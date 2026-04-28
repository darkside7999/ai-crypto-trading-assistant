from typing import Any

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.models.db import TelegramMessage
from app.utils.security import redact


class TelegramService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send(self, session: Session, text: str, message_type: str = "general") -> bool:
        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id
        if not token or not chat_id:
            record = TelegramMessage(message_type=message_type, text=text, success=False, response_payload={"reason": "not_configured"})
            session.add(record)
            session.commit()
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
            ok = response.is_success
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text}
        except Exception as exc:
            ok = False
            body = {"error": str(exc)}

        record = TelegramMessage(message_type=message_type, text=text, success=ok, response_payload=redact(body))
        session.add(record)
        session.commit()
        return ok
