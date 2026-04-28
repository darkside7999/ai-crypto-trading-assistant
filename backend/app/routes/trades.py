from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import ExchangeOrder, Trade, TradeStatus
from app.schemas.api import MessageResponse, TradeRead
from app.services.logging import log_event
from app.services.telegram.service import TelegramService
from app.utils.security import require_admin


router = APIRouter(prefix="/trades", tags=["trades"], dependencies=[Depends(require_admin)])


@router.get("/open", response_model=list[TradeRead])
def open_trades(session: Session = Depends(get_session)):
    return session.exec(select(Trade).where(Trade.status.in_([TradeStatus.OPEN, TradeStatus.PROPOSED, TradeStatus.RISK]))).all()


@router.get("/history", response_model=list[TradeRead])
def trade_history(session: Session = Depends(get_session)):
    return session.exec(select(Trade).order_by(Trade.created_at.desc()).limit(200)).all()


@router.post("/{trade_id}/confirm-buy", response_model=MessageResponse)
async def confirm_buy(trade_id: int, session: Session = Depends(get_session)) -> MessageResponse:
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    if trade.status != TradeStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only proposed trades can be confirmed")
    trade.status = TradeStatus.OPEN
    trade.opened_at = datetime.now(timezone.utc)
    trade.updated_at = datetime.now(timezone.utc)
    session.add(trade)
    session.add(
        ExchangeOrder(
            trade_id=trade.id,
            symbol=trade.symbol,
            side="BUY",
            request_payload={"paper": True, "confirmed_by": "admin"},
            response_payload={"status": "filled", "entry_price": trade.entry_price},
        )
    )
    session.commit()
    log_event(session, "trade.confirmed_buy", "Paper buy confirmed", context={"trade_id": trade.id})
    await TelegramService().send(session, f"Operacion DEMO abierta: {trade.symbol} por {trade.amount_eur:.2f} EUR", "trade_opened")
    return MessageResponse(message="Paper buy confirmed")


@router.post("/{trade_id}/confirm-sell", response_model=MessageResponse)
async def confirm_sell(trade_id: int, session: Session = Depends(get_session)) -> MessageResponse:
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    if trade.status not in {TradeStatus.OPEN, TradeStatus.RISK}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only open/risk trades can be sold")
    trade.status = TradeStatus.CLOSED
    trade.exit_reason = "Manual sell confirmation"
    trade.closed_at = datetime.now(timezone.utc)
    trade.updated_at = datetime.now(timezone.utc)
    session.add(trade)
    session.add(
        ExchangeOrder(
            trade_id=trade.id,
            symbol=trade.symbol,
            side="SELL",
            request_payload={"paper": True, "confirmed_by": "admin"},
            response_payload={"status": "filled", "exit_price": trade.current_price},
        )
    )
    session.commit()
    log_event(session, "trade.confirmed_sell", "Paper sell confirmed", context={"trade_id": trade.id})
    await TelegramService().send(session, f"Operacion DEMO cerrada: {trade.symbol}. PnL neto: {trade.net_pnl_eur:.2f} EUR", "trade_closed")
    return MessageResponse(message="Paper sell confirmed")


@router.post("/{trade_id}/convert-long-term", response_model=MessageResponse)
def convert_long_term(trade_id: int, session: Session = Depends(get_session)) -> MessageResponse:
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    trade.status = TradeStatus.LONG_TERM_HOLD
    trade.exit_reason = "Converted to long-term hold"
    trade.updated_at = datetime.now(timezone.utc)
    session.add(trade)
    session.commit()
    log_event(session, "trade.long_term", "Trade converted to long-term hold", context={"trade_id": trade.id})
    return MessageResponse(message="Trade converted to long-term hold")
