from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models.db import RiskSettingsHistory
from app.schemas.api import RiskSettingsRead, RiskSettingsUpdate
from app.services.logging import log_event
from app.services.trading.demo import get_or_create_risk_settings
from app.utils.security import require_admin


router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_admin)])


@router.get("/risk", response_model=RiskSettingsRead)
def read_risk_settings(session: Session = Depends(get_session)):
    return get_or_create_risk_settings(session)


@router.put("/risk", response_model=RiskSettingsRead)
def update_risk_settings(payload: RiskSettingsUpdate, session: Session = Depends(get_session)):
    settings = get_or_create_risk_settings(session)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    session.add(settings)
    session.add(RiskSettingsHistory(settings_snapshot=payload.model_dump()))
    session.commit()
    session.refresh(settings)
    log_event(session, "settings.risk.updated", "Risk settings updated", context=payload.model_dump())
    return settings
