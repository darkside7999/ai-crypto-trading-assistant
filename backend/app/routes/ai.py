from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import AiDecision
from app.schemas.api import AiDecisionRead
from app.utils.security import require_admin


router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(require_admin)])


@router.get("/decisions", response_model=list[AiDecisionRead])
def decisions(session: Session = Depends(get_session)):
    return session.exec(select(AiDecision).order_by(AiDecision.created_at.desc()).limit(200)).all()
