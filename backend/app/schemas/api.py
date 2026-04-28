from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.db import ControlMode, TradeStatus, TradingMode


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BotStatusResponse(BaseModel):
    enabled: bool
    trading_mode: TradingMode
    control_mode: ControlMode
    updated_at: datetime
    open_trades: int = 0


class StrongConfirmationRequest(BaseModel):
    confirmation: str = Field(description="Must be exactly ENABLE_REAL_MODE")


class RiskSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_daily_capital_eur: float
    max_daily_loss_eur: float
    target_profit_eur: float
    max_open_trades: int
    max_capital_per_trade_eur: float
    max_loss_per_trade_eur: float
    min_volume_quote: float
    max_spread_pct: float
    max_trade_minutes: int
    allow_sell_small_loss: bool
    trailing_take_profit_pct: float
    allowed_symbols: list[str]
    blocked_symbols: list[str]


class RiskSettingsUpdate(RiskSettingsRead):
    pass


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    status: TradeStatus
    mode: TradingMode
    control_mode: ControlMode
    amount_eur: float
    entry_price: float | None
    current_price: float | None
    target_price: float | None
    estimated_fee_eur: float
    estimated_spread_eur: float
    gross_pnl_eur: float
    net_pnl_eur: float
    entry_reason: str | None
    exit_reason: str | None
    risk_reason: str | None
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class AiDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    action: str
    symbol: str | None
    confidence: float
    reason: str
    risk_level: str
    expected_net_profit: float
    requires_user_confirmation: bool
    raw_response: dict[str, Any]
    created_at: datetime


class LogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    event: str
    message: str
    context: dict[str, Any]
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class AiSettingsRead(BaseModel):
    enabled: bool
    provider: str
    configured: bool
    model: str
    fallback_model: str
    active_session_id: int | None = None
    ollama_base_url: str
    ollama_model: str
    max_calls_per_day: int
    max_input_tokens: int
    max_output_tokens: int
    temperature: float


class AiSettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = None
    model: str | None = None
    fallback_model: str | None = None
    active_session_id: int | None = None


class AiAnalyzeRequest(BaseModel):
    symbol: str | None = None
    use_fallback: bool = False


class AiAnalyzeResponse(BaseModel):
    decision: AiDecisionRead
    usage: dict[str, Any]


class AiCostsResponse(BaseModel):
    enabled: bool
    configured: bool
    model: str
    fallback_model: str
    calls_used_today: int
    max_calls_per_day: int
    prompt_tokens_today: int
    completion_tokens_today: int
    estimated_cost_today_usd: float
    input_price_per_million: float
    output_price_per_million: float


class AiModelOption(BaseModel):
    id: str
    provider: str
    label: str
    cost_tier: str
    input_price_per_million: float
    output_price_per_million: float
    strength_for_trading: str
    notes: str


class AiSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str
    active: bool
    created_at: datetime
    updated_at: datetime


class AiSessionCreate(BaseModel):
    title: str = "Nueva sesion"


class AiMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int | None
    content: str
    source: str
    confidence: float
    active: bool
    created_at: datetime


class AiMemoryCreate(BaseModel):
    content: str
    session_id: int | None = None
    source: str = "manual"
    confidence: float = 0.7
