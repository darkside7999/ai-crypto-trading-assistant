from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import LogEntry
from app.schemas.api import LogRead
from app.utils.security import require_admin


router = APIRouter(prefix="/logs", tags=["logs"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[LogRead])
def logs(session: Session = Depends(get_session)):
    return session.exec(select(LogEntry).order_by(LogEntry.created_at.desc()).limit(300)).all()
