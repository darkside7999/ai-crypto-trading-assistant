from dataclasses import dataclass, field
from datetime import datetime, time, timezone

from sqlmodel import Session, select

from app.models.db import BotState, RiskSettings, Trade, TradeStatus, TradingMode


@dataclass
class TradeProposal:
    action: str
    symbol: str
    amount_eur: float
    entry_price: float
    target_price: float
    expected_net_profit: float
    estimated_fee_eur: float
    estimated_spread_eur: float
    spread_pct: float
    quote_volume: float
    reason: str


@dataclass
class RiskResult:
    accepted: bool
    reasons: list[str] = field(default_factory=list)


class RiskEngine:
    def validate_buy(self, session: Session, state: BotState, settings: RiskSettings, proposal: TradeProposal) -> RiskResult:
        reasons: list[str] = []

        if state.trading_mode != TradingMode.DEMO:
            reasons.append("Phase 1 only allows DEMO mode")
        if proposal.symbol in settings.blocked_symbols:
            reasons.append("Symbol is blocked")
        if proposal.symbol not in settings.allowed_symbols:
            reasons.append("Symbol is not in the allowed list")
        if proposal.amount_eur > settings.max_capital_per_trade_eur:
            reasons.append("Capital per trade limit exceeded")
        if proposal.expected_net_profit < settings.target_profit_eur:
            reasons.append("Expected net profit is below configured target")
        if proposal.spread_pct > settings.max_spread_pct:
            reasons.append("Spread is above configured maximum")
        if proposal.quote_volume < settings.min_volume_quote:
            reasons.append("Volume is below configured minimum")

        open_count = len(session.exec(select(Trade).where(Trade.status == TradeStatus.OPEN)).all())
        if open_count >= settings.max_open_trades:
            reasons.append("Maximum open trades reached")

        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        spent_today = sum(
            trade.amount_eur
            for trade in session.exec(
                select(Trade).where(Trade.status.in_([TradeStatus.OPEN, TradeStatus.CLOSED]), Trade.created_at >= today_start)
            ).all()
        )
        if spent_today + proposal.amount_eur > settings.max_daily_capital_eur:
            reasons.append("Daily capital limit exceeded")

        daily_pnl = sum(
            trade.net_pnl_eur
            for trade in session.exec(select(Trade).where(Trade.status == TradeStatus.CLOSED, Trade.created_at >= today_start)).all()
        )
        if daily_pnl <= -abs(settings.max_daily_loss_eur):
            reasons.append("Daily loss limit reached")

        return RiskResult(accepted=not reasons, reasons=reasons)
