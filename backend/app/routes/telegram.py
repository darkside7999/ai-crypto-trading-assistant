from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas.api import MessageResponse
from app.services.telegram.service import TelegramService
from app.utils.security import require_admin


router = APIRouter(prefix="/telegram", tags=["telegram"], dependencies=[Depends(require_admin)])


@router.post("/test", response_model=MessageResponse)
async def test_telegram(session: Session = Depends(get_session)) -> MessageResponse:
    ok = await TelegramService().send(session, "Prueba de Telegram desde AI Crypto Trading Assistant", "test")
    return MessageResponse(message="Telegram message sent" if ok else "Telegram is not configured or failed")
