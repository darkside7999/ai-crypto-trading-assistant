from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import BotState, ControlMode, ModeChange, Trade, TradeStatus, TradingMode
from app.schemas.api import BotStatusResponse, MessageResponse, StrongConfirmationRequest
from app.services.logging import log_event
from app.services.telegram.service import TelegramService
from app.services.trading.demo import DemoTradingService, get_or_create_state
from app.utils.security import require_admin


router = APIRouter(prefix="/bot", tags=["bot"], dependencies=[Depends(require_admin)])


def _status(session: Session, state: BotState) -> BotStatusResponse:
    open_count = len(session.exec(select(Trade).where(Trade.status == TradeStatus.OPEN)).all())
    return BotStatusResponse(
        enabled=state.enabled,
        trading_mode=state.trading_mode,
        control_mode=state.control_mode,
        updated_at=state.updated_at,
        open_trades=open_count,
    )


@router.get("/status", response_model=BotStatusResponse)
def bot_status(session: Session = Depends(get_session)) -> BotStatusResponse:
    return _status(session, get_or_create_state(session))


@router.post("/start", response_model=MessageResponse)
async def start_bot(session: Session = Depends(get_session)) -> MessageResponse:
    state = get_or_create_state(session)
    state.enabled = True
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()
    log_event(session, "bot.started", "Bot enabled", context={"mode": state.trading_mode.value})
    await TelegramService().send(session, f"Bot encendido en modo {state.trading_mode.value}/{state.control_mode.value}", "bot_started")
    return MessageResponse(message="Bot started")


@router.post("/stop", response_model=MessageResponse)
async def stop_bot(session: Session = Depends(get_session)) -> MessageResponse:
    state = get_or_create_state(session)
    state.enabled = False
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()
    log_event(session, "bot.stopped", "Bot disabled")
    await TelegramService().send(session, "Bot apagado", "bot_stopped")
    return MessageResponse(message="Bot stopped")


@router.post("/mode/demo", response_model=MessageResponse)
async def set_demo(session: Session = Depends(get_session)) -> MessageResponse:
    state = get_or_create_state(session)
    previous = state.trading_mode.value
    state.trading_mode = TradingMode.DEMO
    state.real_mode_confirmed_at = None
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.add(ModeChange(previous_value=previous, new_value="DEMO", change_type="trading_mode", reason="Dashboard/API switch"))
    session.commit()
    log_event(session, "mode.demo", "Trading mode set to DEMO")
    await TelegramService().send(session, "Modo cambiado a DEMO. No se usara dinero real.", "mode_demo")
    return MessageResponse(message="Demo mode enabled")


@router.post("/mode/real", response_model=MessageResponse)
async def set_real(payload: StrongConfirmationRequest, session: Session = Depends(get_session)) -> MessageResponse:
    if payload.confirmation != "ENABLE_REAL_MODE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strong confirmation is required")
    log_event(session, "mode.real.blocked", "Real mode requested but blocked in Phase 1", level="WARNING")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Real mode is intentionally disabled in Phase 1")


@router.post("/mode/manual", response_model=MessageResponse)
async def set_manual(session: Session = Depends(get_session)) -> MessageResponse:
    state = get_or_create_state(session)
    previous = state.control_mode.value
    state.control_mode = ControlMode.MANUAL
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.add(ModeChange(previous_value=previous, new_value="MANUAL", change_type="control_mode", reason="Dashboard/API switch"))
    session.commit()
    log_event(session, "mode.manual", "Control mode set to MANUAL")
    await TelegramService().send(session, "Modo cambiado a MANUAL. Las operaciones requieren confirmacion.", "mode_manual")
    return MessageResponse(message="Manual mode enabled")


@router.post("/mode/autonomous", response_model=MessageResponse)
async def set_autonomous(session: Session = Depends(get_session)) -> MessageResponse:
    state = get_or_create_state(session)
    previous = state.control_mode.value
    state.control_mode = ControlMode.AUTONOMOUS
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.add(ModeChange(previous_value=previous, new_value="AUTONOMOUS", change_type="control_mode", reason="Dashboard/API switch"))
    session.commit()
    log_event(session, "mode.autonomous", "Control mode set to AUTONOMOUS in DEMO-only phase")
    await TelegramService().send(session, "Modo AUTONOMO activado solo para DEMO.", "mode_autonomous")
    return MessageResponse(message="Autonomous demo mode enabled")


@router.post("/tick", response_model=MessageResponse)
def run_tick(session: Session = Depends(get_session)) -> MessageResponse:
    result = DemoTradingService().run_cycle(session)
    DemoTradingService().mark_to_market(session)
    return MessageResponse(message=f"Cycle result: {result}")
