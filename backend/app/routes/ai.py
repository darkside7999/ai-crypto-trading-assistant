from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import AiDecision
from app.schemas.api import AiAnalyzeRequest, AiAnalyzeResponse, AiCostsResponse, AiDecisionRead, AiSettingsRead, AiSettingsUpdate
from app.services.ai.openrouter import OpenRouterAiService, set_ai_enabled
from app.services.logging import log_event
from app.utils.security import require_admin


router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(require_admin)])


@router.get("/decisions", response_model=list[AiDecisionRead])
def decisions(session: Session = Depends(get_session)):
    return session.exec(select(AiDecision).order_by(AiDecision.created_at.desc()).limit(200)).all()


@router.get("/settings", response_model=AiSettingsRead)
def ai_settings(session: Session = Depends(get_session)):
    return OpenRouterAiService().settings(session)


@router.put("/settings", response_model=AiSettingsRead)
def update_ai_settings(payload: AiSettingsUpdate, session: Session = Depends(get_session)):
    set_ai_enabled(session, payload.enabled)
    log_event(session, "ai.settings.updated", "AI demo setting updated", context={"enabled": payload.enabled})
    return OpenRouterAiService().settings(session)


@router.get("/costs", response_model=AiCostsResponse)
def ai_costs(session: Session = Depends(get_session)):
    return OpenRouterAiService().costs(session)


@router.post("/analyze", response_model=AiAnalyzeResponse)
def ai_analyze(payload: AiAnalyzeRequest, session: Session = Depends(get_session)):
    decision, usage = OpenRouterAiService().analyze(session, symbol=payload.symbol, use_fallback=payload.use_fallback)
    return AiAnalyzeResponse(decision=decision, usage=usage)
