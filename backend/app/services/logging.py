from typing import Any

from sqlmodel import Session

from app.models.db import LogEntry
from app.utils.security import redact


def log_event(session: Session, event: str, message: str, level: str = "INFO", context: dict[str, Any] | None = None) -> LogEntry:
    entry = LogEntry(level=level, event=event, message=message, context=redact(context or {}))
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
