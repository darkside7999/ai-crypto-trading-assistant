from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradingMode(str, Enum):
    DEMO = "DEMO"
    REAL = "REAL"


class ControlMode(str, Enum):
    MANUAL = "MANUAL"
    AUTONOMOUS = "AUTONOMOUS"


class TradeStatus(str, Enum):
    PROPOSED = "PROPOSED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAUSED = "PAUSED"
    RISK = "RISK"
    LONG_TERM_HOLD = "LONG_TERM_HOLD"
    REJECTED = "REJECTED"


class BotState(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = False
    trading_mode: TradingMode = TradingMode.DEMO
    control_mode: ControlMode = ControlMode.MANUAL
    real_mode_confirmed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class RiskSettings(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    max_daily_capital_eur: float = 5.0
    max_daily_loss_eur: float = 10.0
    target_profit_eur: float = 0.30
    max_open_trades: int = 2
    max_capital_per_trade_eur: float = 2.50
    max_loss_per_trade_eur: float = 1.0
    min_volume_quote: float = 1000000.0
    max_spread_pct: float = 0.25
    max_trade_minutes: int = 240
    allow_sell_small_loss: bool = False
    trailing_take_profit_pct: float = 0.15
    allowed_symbols: list[str] = Field(default_factory=lambda: ["BTC/USDT", "ETH/USDT", "SOL/USDT"], sa_column=Column(JSON))
    blocked_symbols: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utc_now)


class RiskSettingsHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    settings_snapshot: dict[str, Any] = Field(sa_column=Column(JSON))
    changed_by: str = "admin"
    created_at: datetime = Field(default_factory=utc_now)


class Trade(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    symbol: str
    status: TradeStatus = TradeStatus.PROPOSED
    mode: TradingMode = TradingMode.DEMO
    control_mode: ControlMode = ControlMode.MANUAL
    amount_eur: float
    entry_price: float | None = None
    current_price: float | None = None
    target_price: float | None = None
    estimated_fee_eur: float = 0.0
    estimated_spread_eur: float = 0.0
    gross_pnl_eur: float = 0.0
    net_pnl_eur: float = 0.0
    ai_decision_id: int | None = None
    entry_reason: str | None = None
    exit_reason: str | None = None
    risk_reason: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ExchangeOrder(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trade_id: int | None = Field(default=None, foreign_key="trade.id")
    exchange: str = "binance"
    symbol: str
    side: str
    order_type: str = "paper"
    mode: TradingMode = TradingMode.DEMO
    request_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    response_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class AiDecision(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    provider: str = "rules_v1"
    action: str
    symbol: str | None = None
    confidence: float = 0.0
    reason: str
    risk_level: str = "MEDIUM"
    expected_net_profit: float = 0.0
    max_acceptable_loss: float = 0.0
    time_horizon: str = "scalp"
    requires_user_confirmation: bool = True
    raw_response: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class BalanceSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mode: TradingMode = TradingMode.DEMO
    asset: str = "EUR"
    free: float = 0.0
    used: float = 0.0
    total: float = 0.0
    raw_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class ModeChange(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    previous_value: str
    new_value: str
    change_type: str
    reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TelegramMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    message_type: str
    text: str
    success: bool
    response_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class LogEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    level: str = "INFO"
    event: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utc_now)


class AiUsage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    provider: str = "openrouter"
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    success: bool = False
    reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class AiSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    summary: str = ""
    active: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AiMemory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int | None = Field(default=None, foreign_key="aisession.id")
    content: str
    source: str = "system"
    confidence: float = 0.5
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
