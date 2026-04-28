import json
import threading
from datetime import datetime, time, timezone
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import get_settings
from app.models.db import AiDecision, AiMemory, AiSession, AiUsage, AppSetting
from app.services.ai.prompt import SYSTEM_PROMPT
from app.services.logging import log_event
from app.services.market_intel import MarketIntelService
from app.services.trading.demo import get_or_create_risk_settings
from app.utils.security import redact


AI_ANALYSIS_LOCK = threading.Lock()

MODEL_CATALOG = [
    {
        "id": "qwen/qwen3-235b-a22b:free",
        "provider": "openrouter",
        "label": "Qwen3 235B A22B Free",
        "cost_tier": "free",
        "input_price_per_million": 0.0,
        "output_price_per_million": 0.0,
        "strength_for_trading": "Muy alta para razonamiento estructurado y JSON; gratis pero con limites/rate limits.",
        "notes": "Recomendado como primer modelo gratis potente. Puede saturarse al ser free.",
    },
    {
        "id": "deepseek/deepseek-r1-0528:free",
        "provider": "openrouter",
        "label": "DeepSeek R1 0528 Free",
        "cost_tier": "free",
        "input_price_per_million": 0.0,
        "output_price_per_million": 0.0,
        "strength_for_trading": "Alta para razonamiento; puede ser mas lento y a veces verboso.",
        "notes": "Buen fallback gratis para segunda opinion, sujeto a limites de OpenRouter.",
    },
    {
        "id": "google/gemini-2.5-flash-lite",
        "provider": "openrouter",
        "label": "Gemini 2.5 Flash-Lite",
        "cost_tier": "very_low",
        "input_price_per_million": 0.10,
        "output_price_per_million": 0.40,
        "strength_for_trading": "Muy buena relacion coste/latencia para decisiones frecuentes.",
        "notes": "Recomendado si los free models se saturan.",
    },
    {
        "id": "deepseek/deepseek-chat-v3.1",
        "provider": "openrouter",
        "label": "DeepSeek V3.1",
        "cost_tier": "low",
        "input_price_per_million": 0.15,
        "output_price_per_million": 0.75,
        "strength_for_trading": "Fuerte para analisis general y explicaciones de riesgo.",
        "notes": "Fallback economico de pago.",
    },
    {
        "id": "ollama:qwen3:8b",
        "provider": "ollama",
        "label": "Ollama Qwen3 8B local",
        "cost_tier": "local",
        "input_price_per_million": 0.0,
        "output_price_per_million": 0.0,
        "strength_for_trading": "Gratis en tu maquina; calidad depende del modelo y hardware.",
        "notes": "Usa OLLAMA_BASE_URL y OLLAMA_MODEL. Internet sigue controlado por backend.",
    },
]


def catalog_by_id() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in MODEL_CATALOG}


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


def get_ai_config(session: Session) -> dict[str, Any]:
    settings = get_settings()
    stored = session.get(AppSetting, "ai")
    value = stored.value if stored else {}
    default_model = settings.ai_model
    return {
        "enabled": bool(value.get("enabled", settings.ai_enabled)),
        "provider": value.get("provider", settings.ai_provider),
        "model": value.get("model", default_model),
        "fallback_model": value.get("fallback_model", settings.ai_fallback_model),
        "active_session_id": value.get("active_session_id"),
    }


def save_ai_config(session: Session, updates: dict[str, Any]) -> AppSetting:
    stored = session.get(AppSetting, "ai")
    if not stored:
        stored = AppSetting(key="ai", value={})
    clean_updates = {key: value for key, value in updates.items() if value is not None}
    stored.value = {**stored.value, **clean_updates}
    stored.updated_at = datetime.now(timezone.utc)
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored


def ai_setting_enabled(session: Session) -> bool:
    return bool(get_ai_config(session)["enabled"])


def set_ai_enabled(session: Session, enabled: bool) -> AppSetting:
    return save_ai_config(session, {"enabled": enabled})


def get_or_create_active_session(session: Session) -> AiSession:
    config = get_ai_config(session)
    if config.get("active_session_id"):
        existing = session.get(AiSession, int(config["active_session_id"]))
        if existing:
            return existing
    active = session.exec(select(AiSession).where(AiSession.active == True).limit(1)).first()  # noqa: E712
    if active:
        save_ai_config(session, {"active_session_id": active.id})
        return active
    created = AiSession(title="Sesion demo inicial", active=True)
    session.add(created)
    session.commit()
    session.refresh(created)
    save_ai_config(session, {"active_session_id": created.id})
    return created


def create_ai_session(session: Session, title: str) -> AiSession:
    for existing in session.exec(select(AiSession).where(AiSession.active == True)).all():  # noqa: E712
        existing.active = False
        session.add(existing)
    created = AiSession(title=title.strip() or "Nueva sesion", active=True)
    session.add(created)
    session.commit()
    session.refresh(created)
    save_ai_config(session, {"active_session_id": created.id})
    return created


def activate_ai_session(session: Session, session_id: int) -> AiSession:
    target = session.get(AiSession, session_id)
    if not target:
        raise ValueError("AI session not found")
    for existing in session.exec(select(AiSession)).all():
        existing.active = existing.id == session_id
        session.add(existing)
    session.commit()
    session.refresh(target)
    save_ai_config(session, {"active_session_id": target.id})
    return target


class OpenRouterAiService:
    def model_catalog(self) -> list[dict[str, Any]]:
        return MODEL_CATALOG

    def settings(self, session: Session) -> dict[str, Any]:
        settings = get_settings()
        config = get_ai_config(session)
        provider = self._provider_for_model(config["model"], config["provider"])
        return {
            "enabled": config["enabled"],
            "provider": provider,
            "configured": self._is_configured(provider),
            "model": config["model"],
            "fallback_model": config["fallback_model"],
            "active_session_id": config.get("active_session_id"),
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "max_calls_per_day": settings.ai_max_calls_per_day,
            "max_input_tokens": settings.ai_max_input_tokens,
            "max_output_tokens": settings.ai_max_output_tokens,
            "temperature": settings.ai_temperature,
        }

    def update_settings(self, session: Session, updates: dict[str, Any]) -> dict[str, Any]:
        allowed = {key: value for key, value in updates.items() if key in {"enabled", "provider", "model", "fallback_model", "active_session_id"}}
        if allowed.get("model"):
            allowed["provider"] = self._provider_for_model(allowed["model"], allowed.get("provider"))
        save_ai_config(session, allowed)
        return self.settings(session)

    def costs(self, session: Session) -> dict[str, Any]:
        settings = get_settings()
        config = get_ai_config(session)
        rows = session.exec(select(AiUsage).where(AiUsage.created_at >= today_start())).all()
        api_call_rows = [row for row in rows if row.success]
        prices = self._prices(config["model"])
        return {
            "enabled": config["enabled"],
            "configured": self._is_configured(self._provider_for_model(config["model"], config["provider"])),
            "model": config["model"],
            "fallback_model": config["fallback_model"],
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
        acquired = AI_ANALYSIS_LOCK.acquire(timeout=settings.ai_queue_wait_seconds)
        if not acquired:
            return self._wait(session, get_ai_config(session)["model"], "AI queue wait timeout", "queue_timeout")
        try:
            return self._analyze_locked(session, symbol=symbol, use_fallback=use_fallback)
        finally:
            AI_ANALYSIS_LOCK.release()

    def _analyze_locked(self, session: Session, symbol: str | None = None, use_fallback: bool = False) -> tuple[AiDecision, dict[str, Any]]:
        settings = get_settings()
        risk_settings = get_or_create_risk_settings(session)
        config = get_ai_config(session)
        model = config["fallback_model"] if use_fallback else config["model"]
        provider = self._provider_for_model(model, config["provider"])
        model_for_provider = self._model_for_provider(model)

        if not config["enabled"]:
            return self._wait(session, model, "AI demo is disabled", "disabled")
        if not self._is_configured(provider):
            return self._wait(session, model, f"{provider} is not configured", "provider_not_configured")

        calls_today = len(session.exec(select(AiUsage).where(AiUsage.created_at >= today_start(), AiUsage.success == True)).all())  # noqa: E712
        if provider == "openrouter" and calls_today >= settings.ai_max_calls_per_day:
            return self._wait(session, model, "Daily AI call limit reached", "daily_limit")

        ai_session = get_or_create_active_session(session)
        memories = session.exec(select(AiMemory).where(AiMemory.active == True).order_by(AiMemory.created_at.desc()).limit(12)).all()  # noqa: E712
        symbols = [symbol] if symbol else risk_settings.allowed_symbols
        intel = MarketIntelService().collect(symbols)
        prompt_payload = {
            "ai_session": {"id": ai_session.id, "title": ai_session.title, "summary": ai_session.summary},
            "memories": [{"content": memory.content, "source": memory.source, "confidence": memory.confidence} for memory in memories],
            "risk_settings": risk_settings.model_dump(),
            "market_intel": intel,
            "constraints": {
                "demo_only": True,
                "must_return_json_only": True,
                "must_wait_if_data_insufficient": True,
                "internet_is_backend_controlled": True,
            },
        }
        user_prompt = json.dumps(prompt_payload, ensure_ascii=False, default=str)
        input_tokens = estimate_tokens(SYSTEM_PROMPT + user_prompt)
        if input_tokens > settings.ai_max_input_tokens:
            return self._wait(session, model, "AI input token estimate exceeds configured limit", "input_token_limit", input_tokens=input_tokens)

        try:
            raw = self._call_model(provider, model_for_provider, user_prompt)
            text = self._extract_text(provider, raw)
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
                provider=f"{provider}:{model_for_provider}",
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
                    provider=provider,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_cost_usd=cost,
                    success=True,
                    reason=parsed.reason,
                )
            )
            self._learn_from_decision(session, ai_session, decision)
            session.commit()
            session.refresh(decision)
            log_event(session, "ai.analyze", "AI analysis completed", context={"provider": provider, "model": model, "action": decision.action})
            return decision, {"provider": provider, "model": model, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "estimated_cost_usd": cost}
        except Exception as exc:
            log_event(session, "ai.error", "AI analysis failed", level="ERROR", context={"provider": provider, "model": model, "error": str(exc)})
            return self._wait(session, model, f"AI analysis failed: {exc}", "error")

    def _call_model(self, provider: str, model: str, user_prompt: str) -> dict[str, Any]:
        if provider == "ollama":
            return self._call_ollama(model, user_prompt)
        return self._call_openrouter(model, user_prompt)

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
        with httpx.Client(timeout=45) as client:
            response = client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def _call_ollama(self, model: str, user_prompt: str) -> dict[str, Any]:
        settings = get_settings()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": settings.ai_temperature, "num_predict": settings.ai_max_output_tokens},
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

    def _extract_text(self, provider: str, raw: dict[str, Any]) -> str:
        if provider == "ollama":
            return str((raw.get("message") or {}).get("content") or "")
        return str(raw["choices"][0]["message"]["content"])

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

    def _learn_from_decision(self, session: Session, ai_session: AiSession, decision: AiDecision) -> None:
        short_reason = decision.reason[:260]
        ai_session.summary = (
            f"Ultima decision: {decision.action} {decision.symbol or ''}. "
            f"Riesgo {decision.risk_level}. Razon: {short_reason}"
        )[:1000]
        ai_session.updated_at = datetime.now(timezone.utc)
        session.add(ai_session)
        if decision.action in {"WAIT", "HOLD"}:
            session.add(
                AiMemory(
                    session_id=ai_session.id,
                    content=f"Evitar operar cuando la IA indique {decision.action}: {short_reason}",
                    source="auto",
                    confidence=0.55,
                )
            )

    def _wait(
        self,
        session: Session,
        model: str,
        reason: str,
        code: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> tuple[AiDecision, dict[str, Any]]:
        provider = self._provider_for_model(model, get_ai_config(session)["provider"])
        decision = AiDecision(
            provider=f"{provider}:{self._model_for_provider(model)}",
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
                provider=provider,
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
        return decision, {"provider": provider, "model": model, "prompt_tokens": input_tokens, "completion_tokens": output_tokens, "estimated_cost_usd": 0.0, "code": code}

    def _provider_for_model(self, model: str, fallback_provider: str | None) -> str:
        if model.startswith("ollama:"):
            return "ollama"
        if model in catalog_by_id():
            return catalog_by_id()[model]["provider"]
        return fallback_provider or "openrouter"

    def _model_for_provider(self, model: str) -> str:
        if model.startswith("ollama:"):
            return model.split(":", 1)[1]
        return model

    def _is_configured(self, provider: str) -> bool:
        settings = get_settings()
        if provider == "ollama":
            return bool(settings.ollama_base_url)
        return bool(settings.openrouter_api_key)

    def _prices(self, model: str) -> dict[str, float]:
        catalog = catalog_by_id()
        if model in catalog:
            return {"input": catalog[model]["input_price_per_million"], "output": catalog[model]["output_price_per_million"]}
        return {"input": 0.10, "output": 0.40}

    def _estimated_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        prices = self._prices(model)
        return round((input_tokens / 1_000_000 * prices["input"]) + (output_tokens / 1_000_000 * prices["output"]), 6)
