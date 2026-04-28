from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.db import AiDecision, AiMemory, AiSession
from app.schemas.api import (
    AiAnalyzeRequest,
    AiAnalyzeResponse,
    AiCostsResponse,
    AiDecisionRead,
    AiMemoryCreate,
    AiMemoryRead,
    AiModelOption,
    AiSessionCreate,
    AiSessionRead,
    AiSettingsRead,
    AiSettingsUpdate,
)
from app.services.ai.openrouter import OpenRouterAiService, activate_ai_session, create_ai_session
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
    updated = OpenRouterAiService().update_settings(session, payload.model_dump())
    log_event(session, "ai.settings.updated", "AI settings updated", context=payload.model_dump(exclude_none=True))
    return updated


@router.get("/models", response_model=list[AiModelOption])
def ai_models():
    return OpenRouterAiService().model_catalog()


@router.get("/costs", response_model=AiCostsResponse)
def ai_costs(session: Session = Depends(get_session)):
    return OpenRouterAiService().costs(session)


@router.post("/analyze", response_model=AiAnalyzeResponse)
def ai_analyze(payload: AiAnalyzeRequest, session: Session = Depends(get_session)):
    decision, usage = OpenRouterAiService().analyze(session, symbol=payload.symbol, use_fallback=payload.use_fallback)
    return AiAnalyzeResponse(decision=decision, usage=usage)


@router.get("/sessions", response_model=list[AiSessionRead])
def ai_sessions(session: Session = Depends(get_session)):
    return session.exec(select(AiSession).order_by(AiSession.updated_at.desc())).all()


@router.post("/sessions", response_model=AiSessionRead)
def create_session(payload: AiSessionCreate, session: Session = Depends(get_session)):
    created = create_ai_session(session, payload.title)
    log_event(session, "ai.session.created", "AI session created", context={"session_id": created.id, "title": created.title})
    return created


@router.post("/sessions/{session_id}/activate", response_model=AiSessionRead)
def activate_session(session_id: int, session: Session = Depends(get_session)):
    activated = activate_ai_session(session, session_id)
    log_event(session, "ai.session.activated", "AI session activated", context={"session_id": activated.id})
    return activated


@router.get("/memory", response_model=list[AiMemoryRead])
def ai_memory(session: Session = Depends(get_session)):
    return session.exec(select(AiMemory).where(AiMemory.active == True).order_by(AiMemory.created_at.desc()).limit(100)).all()  # noqa: E712


@router.post("/memory", response_model=AiMemoryRead)
def create_memory(payload: AiMemoryCreate, session: Session = Depends(get_session)):
    memory = AiMemory(
        session_id=payload.session_id,
        content=payload.content,
        source=payload.source,
        confidence=payload.confidence,
    )
    session.add(memory)
    session.commit()
    session.refresh(memory)
    log_event(session, "ai.memory.created", "AI memory created", context={"memory_id": memory.id, "source": memory.source})
    return memory
