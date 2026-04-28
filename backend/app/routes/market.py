from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.services.trading.demo import get_or_create_risk_settings
from app.services.market_intel import MarketIntelService
from app.utils.security import require_admin


router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(require_admin)])


@router.get("/intel")
def market_intel(session: Session = Depends(get_session)):
    settings = get_or_create_risk_settings(session)
    return MarketIntelService().collect(settings.allowed_symbols)
