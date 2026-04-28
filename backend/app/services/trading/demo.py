from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.db import AiDecision, BotState, ExchangeOrder, RiskSettings, Trade, TradeStatus
from app.services.exchange.binance import BinanceMarketData, MarketTicker
from app.services.logging import log_event
from app.services.risk.engine import RiskEngine, TradeProposal


FEE_RATE = 0.001


def get_or_create_state(session: Session) -> BotState:
    state = session.exec(select(BotState).limit(1)).first()
    if state:
        return state
    state = BotState()
    session.add(state)
    session.commit()
    session.refresh(state)
    return state


def get_or_create_risk_settings(session: Session) -> RiskSettings:
    settings = session.exec(select(RiskSettings).limit(1)).first()
    if settings:
        return settings
    settings = RiskSettings()
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


class DemoTradingService:
    def __init__(self) -> None:
        self.risk = RiskEngine()

    def run_cycle(self, session: Session) -> dict[str, str]:
        state = get_or_create_state(session)
        settings = get_or_create_risk_settings(session)

        if not state.enabled:
            return {"status": "skipped", "reason": "bot_disabled"}

        tickers = BinanceMarketData().fetch_tickers(settings.allowed_symbols)
        candidate = self._select_candidate(tickers, settings)
        if candidate is None:
            decision = AiDecision(action="WAIT", reason="Not enough reliable data", raw_response={"source": "rules_v1"})
            session.add(decision)
            session.commit()
            log_event(session, "decision.wait", "No market candidate passed the initial filters")
            return {"status": "wait", "reason": "no_candidate"}

        ai_decision = None
        try:
            from app.services.ai.openrouter import OpenRouterAiService, ai_setting_enabled

            if ai_setting_enabled(session):
                ai_decision, ai_usage = OpenRouterAiService().analyze(session)
                if ai_decision.action != "BUY":
                    log_event(
                        session,
                        "ai.no_trade",
                        "AI did not recommend a demo buy",
                        context={"action": ai_decision.action, "reason": ai_decision.reason, "usage": ai_usage},
                    )
                    return {"status": "wait", "reason": ai_decision.reason}
                ticker_by_symbol = {ticker.symbol: ticker for ticker in tickers}
                if ai_decision.symbol not in ticker_by_symbol:
                    log_event(
                        session,
                        "ai.symbol_rejected",
                        "AI recommended a symbol outside collected market data",
                        context={"symbol": ai_decision.symbol},
                    )
                    return {"status": "rejected", "reason": "ai_symbol_not_available"}
                candidate = ticker_by_symbol[ai_decision.symbol]
        except Exception as exc:
            log_event(session, "ai.cycle_error", "AI analysis failed during demo cycle", level="ERROR", context={"error": str(exc)})
            return {"status": "wait", "reason": "ai_cycle_error"}

        proposal = self._build_proposal(candidate, settings)
        if ai_decision:
            decision = ai_decision
            proposal.reason = f"AI demo: {ai_decision.reason}"
            proposal.expected_net_profit = min(proposal.expected_net_profit, ai_decision.expected_net_profit or proposal.expected_net_profit)
        else:
            decision = AiDecision(
                provider="rules_v1",
                action="BUY",
                symbol=proposal.symbol,
                confidence=0.55,
                reason=proposal.reason,
                risk_level="MEDIUM",
                expected_net_profit=proposal.expected_net_profit,
                max_acceptable_loss=settings.max_loss_per_trade_eur,
                requires_user_confirmation=state.control_mode == "MANUAL",
                raw_response={
                    "action": "BUY",
                    "symbol": proposal.symbol,
                    "confidence": 0.55,
                    "reason": proposal.reason,
                    "risk_level": "MEDIUM",
                    "expected_net_profit": proposal.expected_net_profit,
                    "max_acceptable_loss": settings.max_loss_per_trade_eur,
                    "time_horizon": "scalp",
                    "requires_user_confirmation": state.control_mode == "MANUAL",
                },
            )
            session.add(decision)
            session.commit()
            session.refresh(decision)

        risk_result = self.risk.validate_buy(session, state, settings, proposal)
        if not risk_result.accepted:
            trade = Trade(
                symbol=proposal.symbol,
                status=TradeStatus.REJECTED,
                mode=state.trading_mode,
                control_mode=state.control_mode,
                amount_eur=proposal.amount_eur,
                entry_price=proposal.entry_price,
                current_price=proposal.entry_price,
                target_price=proposal.target_price,
                estimated_fee_eur=proposal.estimated_fee_eur,
                estimated_spread_eur=proposal.estimated_spread_eur,
                ai_decision_id=decision.id,
                entry_reason=proposal.reason,
                risk_reason="; ".join(risk_result.reasons),
            )
            session.add(trade)
            session.commit()
            log_event(session, "trade.rejected", "Risk engine rejected paper trade", context={"reasons": risk_result.reasons})
            return {"status": "rejected", "reason": trade.risk_reason or "risk_rejected"}

        status = TradeStatus.PROPOSED if state.control_mode == "MANUAL" else TradeStatus.OPEN
        opened_at = None if status == TradeStatus.PROPOSED else datetime.now(timezone.utc)
        trade = Trade(
            symbol=proposal.symbol,
            status=status,
            mode=state.trading_mode,
            control_mode=state.control_mode,
            amount_eur=proposal.amount_eur,
            entry_price=proposal.entry_price,
            current_price=proposal.entry_price,
            target_price=proposal.target_price,
            estimated_fee_eur=proposal.estimated_fee_eur,
            estimated_spread_eur=proposal.estimated_spread_eur,
            ai_decision_id=decision.id,
            entry_reason=proposal.reason,
            opened_at=opened_at,
        )
        session.add(trade)
        session.commit()
        session.refresh(trade)

        if status == TradeStatus.OPEN:
            session.add(
                ExchangeOrder(
                    trade_id=trade.id,
                    symbol=trade.symbol,
                    side="BUY",
                    request_payload={"paper": True, "amount_eur": trade.amount_eur},
                    response_payload={"status": "filled", "entry_price": trade.entry_price},
                )
            )
            session.commit()
            log_event(session, "trade.opened", "Paper trade opened", context={"trade_id": trade.id, "symbol": trade.symbol})
        else:
            log_event(session, "trade.proposed", "Manual confirmation required for paper trade", context={"trade_id": trade.id})

        return {"status": status.value.lower(), "trade_id": str(trade.id)}

    def mark_to_market(self, session: Session) -> None:
        settings = get_or_create_risk_settings(session)
        open_trades = session.exec(select(Trade).where(Trade.status == TradeStatus.OPEN)).all()
        if not open_trades:
            return
        tickers = {ticker.symbol: ticker for ticker in BinanceMarketData().fetch_tickers([trade.symbol for trade in open_trades])}
        for trade in open_trades:
            ticker = tickers.get(trade.symbol)
            if not ticker or not trade.entry_price:
                continue
            trade.current_price = ticker.last
            units = trade.amount_eur / trade.entry_price
            trade.gross_pnl_eur = (ticker.last - trade.entry_price) * units
            trade.net_pnl_eur = trade.gross_pnl_eur - trade.estimated_fee_eur - trade.estimated_spread_eur
            if trade.net_pnl_eur <= -abs(settings.max_loss_per_trade_eur):
                trade.status = TradeStatus.RISK
                trade.risk_reason = "Maximum loss per trade reached"
            elif trade.net_pnl_eur >= settings.target_profit_eur:
                trade.status = TradeStatus.CLOSED
                trade.exit_reason = "Target net profit reached"
                trade.closed_at = datetime.now(timezone.utc)
                session.add(
                    ExchangeOrder(
                        trade_id=trade.id,
                        symbol=trade.symbol,
                        side="SELL",
                        request_payload={"paper": True, "reason": trade.exit_reason},
                        response_payload={"status": "filled", "exit_price": ticker.last},
                    )
                )
            trade.updated_at = datetime.now(timezone.utc)
            session.add(trade)
        session.commit()

    def _select_candidate(self, tickers: list[MarketTicker], settings: RiskSettings) -> MarketTicker | None:
        filtered = [
            ticker
            for ticker in tickers
            if ticker.last > 0
            and ticker.quote_volume >= settings.min_volume_quote
            and ticker.spread_pct <= settings.max_spread_pct
            and ticker.percentage >= 0
        ]
        return sorted(filtered, key=lambda ticker: (ticker.percentage, ticker.quote_volume), reverse=True)[0] if filtered else None

    def _build_proposal(self, ticker: MarketTicker, settings: RiskSettings) -> TradeProposal:
        amount = min(settings.max_capital_per_trade_eur, settings.max_daily_capital_eur)
        fee = round(amount * FEE_RATE * 2, 4)
        spread = round(amount * (ticker.spread_pct / 100), 4)
        target_profit = settings.target_profit_eur
        target_price = ticker.ask * (1 + ((target_profit + fee + spread) / amount))
        expected_net = round((target_price - ticker.ask) * (amount / ticker.ask) - fee - spread, 4)
        return TradeProposal(
            action="BUY",
            symbol=ticker.symbol,
            amount_eur=amount,
            entry_price=ticker.ask,
            target_price=target_price,
            expected_net_profit=expected_net,
            estimated_fee_eur=fee,
            estimated_spread_eur=spread,
            spread_pct=ticker.spread_pct,
            quote_volume=ticker.quote_volume,
            reason=f"Rules v1: positive 24h change ({ticker.percentage:.2f}%), volume OK, spread {ticker.spread_pct:.3f}%.",
        )
