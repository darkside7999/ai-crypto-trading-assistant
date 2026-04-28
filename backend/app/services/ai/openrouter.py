import json
from datetime import datetime, time, timezone
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import get_settings
from app.models.db import AiDecision, AiUsage, AppSetting
from app.services.ai.prompt import SYSTEM_PROMPT
from app.services.logging import log_event
from app.services.market_intel import MarketIntelService
from app.services.trading.demo import get_or_create_risk_settings
from app.utils.security import redact


MODEL_PRICES = {
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "deepseek/deepseek-chat-v3.1": {"input": 0.15, "output": 0.75},
}


class StructuredAiDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD", "WAIT"]
    symbol: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    expected_net_profit: float = 0.0
    max_acceptable_loss: float = 0.0
    time_horizon: Literal["scalp", "intraday", "long_term"] = "scalp"
    requires_user_confirmation: bool = True


def today_start() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def ai_setting_enabled(session: Session) -> bool:
    stored = session.get(AppSetting, "ai")
    if stored and "enabled" in stored.value:
        return bool(stored.value["enabled"])
    return bool(get_settings().ai_enabled)


def set_ai_enabled(session: Session, enabled: bool) -> AppSetting:
    stored = session.get(AppSetting, "ai")
    if not stored:
        stored = AppSetting(key="ai", value={})
    stored.value = {**stored.value, "enabled": enabled}
    stored.updated_at = datetime.now(timezone.utc)
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored


class OpenRouterAiService:
    def settings(self, session: Session) -> dict[str, Any]:
        settings = get_settings()
        return {
            "enabled": ai_setting_enabled(session),
            "provider": settings.ai_provider,
            "configured": bool(settings.openrouter_api_key),
            "model": settings.ai_model,
            "fallback_model": settings.ai_fallback_model,
            "max_calls_per_day": settings.ai_max_calls_per_day,
            "max_input_tokens": settings.ai_max_input_tokens,
            "max_output_tokens": settings.ai_max_output_tokens,
            "temperature": settings.ai_temperature,
        }

    def costs(self, session: Session) -> dict[str, Any]:
        settings = get_settings()
        rows = session.exec(select(AiUsage).where(AiUsage.created_at >= today_start())).all()
        api_call_rows = [row for row in rows if row.success]
        prices = MODEL_PRICES.get(settings.ai_model, MODEL_PRICES["google/gemini-2.5-flash-lite"])
        return {
            "enabled": ai_setting_enabled(session),
            "configured": bool(settings.openrouter_api_key),
            "model": settings.ai_model,
            "fallback_model": settings.ai_fallback_model,
            "calls_used_today": len(api_call_rows),
            "max_calls_per_day": settings.ai_max_calls_per_day,
            "prompt_tokens_today": sum(row.prompt_tokens for row in rows),
            "completion_tokens_today": sum(row.completion_tokens for row in rows),
            "estimated_cost_today_usd": round(sum(row.estimated_cost_usd for row in rows), 6),
            "input_price_per_million": prices["input"],
            "output_price_per_million": prices["output"],
        }

    def analyze(self, session: Session, symbol: str | None = None, use_fallback: bool = False) -> tuple[AiDecision, dict[str, Any]]:
        settings = get_settings()
        risk_settings = get_or_create_risk_settings(session)
        model = settings.ai_fallback_model if use_fallback else settings.ai_model

        if not ai_setting_enabled(session):
            return self._wait(session, model, "AI demo is disabled", "disabled")
        if settings.ai_provider != "openrouter":
            return self._wait(session, model, "AI provider is not openrouter", "provider_disabled")
        if not settings.openrouter_api_key:
            return self._wait(session, model, "OPENROUTER_API_KEY is not configured", "missing_api_key")

        calls_today = len(session.exec(select(AiUsage).where(AiUsage.created_at >= today_start(), AiUsage.success == True)).all())  # noqa: E712
        if calls_today >= settings.ai_max_calls_per_day:
            return self._wait(session, model, "Daily AI call limit reached", "daily_limit")

        symbols = [symbol] if symbol else risk_settings.allowed_symbols
        intel = MarketIntelService().collect(symbols)
        prompt_payload = {
            "risk_settings": risk_settings.model_dump(),
            "market_intel": intel,
            "constraints": {
                "demo_only": True,
                "must_return_json_only": True,
                "must_wait_if_data_insufficient": True,
            },
        }
        user_prompt = json.dumps(prompt_payload, ensure_ascii=False, default=str)
        input_tokens = estimate_tokens(SYSTEM_PROMPT + user_prompt)
        if input_tokens > settings.ai_max_input_tokens:
            return self._wait(session, model, "AI input token estimate exceeds configured limit", "input_token_limit", input_tokens=input_tokens)

        try:
            raw = self._call_openrouter(model, user_prompt)
            text = raw["choices"][0]["message"]["content"]
            parsed = self._parse_decision(text)
            output_tokens = estimate_tokens(text)
            usage = raw.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or input_tokens)
            completion_tokens = int(usage.get("completion_tokens") or output_tokens)
            if completion_tokens > settings.ai_max_output_tokens:
                return self._wait(
                    session,
                    model,
                    "AI output token count exceeds configured limit",
                    "output_token_limit",
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                )

            decision = AiDecision(
                provider=f"openrouter:{model}",
                action=parsed.action,
                symbol=parsed.symbol,
                confidence=parsed.confidence,
                reason=parsed.reason,
                risk_level=parsed.risk_level,
                expected_net_profit=parsed.expected_net_profit,
                max_acceptable_loss=parsed.max_acceptable_loss,
                time_horizon=parsed.time_horizon,
                requires_user_confirmation=True,
                raw_response=redact(raw),
            )
            session.add(decision)
            cost = self._estimated_cost(model, prompt_tokens, completion_tokens)
            session.add(
                AiUsage(
                    provider="openrouter",
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_cost_usd=cost,
                    success=True,
                    reason=parsed.reason,
                )
            )
            session.commit()
            session.refresh(decision)
            log_event(session, "ai.analyze", "AI analysis completed", context={"model": model, "action": decision.action, "symbol": decision.symbol})
            return decision, {"model": model, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "estimated_cost_usd": cost}
        except Exception as exc:
            log_event(session, "ai.error", "AI analysis failed", level="ERROR", context={"model": model, "error": str(exc)})
            return self._wait(session, model, f"AI analysis failed: {exc}", "error")

    def _call_openrouter(self, model: str, user_prompt: str) -> dict[str, Any]:
        settings = get_settings()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.ai_temperature,
            "max_tokens": settings.ai_max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "AI Crypto Trading Assistant",
        }
        with httpx.Client(timeout=30) as client:
            response = client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def _parse_decision(self, text: str) -> StructuredAiDecision:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise
            data = json.loads(text[start : end + 1])
        parsed = StructuredAiDecision.model_validate(data)
        if parsed.action == "WAIT" and not parsed.reason:
            parsed.reason = "Not enough reliable data"
        if parsed.action != "WAIT" and not parsed.symbol:
            raise ValueError("Non-WAIT actions require a symbol")
        return parsed

    def _wait(
        self,
        session: Session,
        model: str,
        reason: str,
        code: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> tuple[AiDecision, dict[str, Any]]:
        decision = AiDecision(
            provider=f"openrouter:{model}",
            action="WAIT",
            confidence=0.0,
            reason=reason,
            risk_level="MEDIUM",
            expected_net_profit=0.0,
            requires_user_confirmation=True,
            raw_response={"action": "WAIT", "reason": reason, "code": code},
        )
        session.add(decision)
        session.add(
            AiUsage(
                provider="openrouter",
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                estimated_cost_usd=self._estimated_cost(model, input_tokens, output_tokens),
                success=False,
                reason=reason,
            )
        )
        session.commit()
        session.refresh(decision)
        return decision, {"model": model, "prompt_tokens": input_tokens, "completion_tokens": output_tokens, "estimated_cost_usd": 0.0, "code": code}

    def _estimated_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        prices = MODEL_PRICES.get(model, MODEL_PRICES["google/gemini-2.5-flash-lite"])
        return round((input_tokens / 1_000_000 * prices["input"]) + (output_tokens / 1_000_000 * prices["output"]), 6)
