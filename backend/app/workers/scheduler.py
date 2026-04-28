from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from app.config import get_settings
from app.database import engine
from app.services.logging import log_event
from app.services.trading.demo import DemoTradingService


scheduler = BackgroundScheduler()


def trading_job() -> None:
    with Session(engine) as session:
        try:
            service = DemoTradingService()
            service.mark_to_market(session)
            result = service.run_cycle(session)
            log_event(session, "bot.tick", "Scheduled paper trading cycle completed", context=result)
        except Exception as exc:
            log_event(session, "bot.tick.error", "Scheduled paper trading cycle failed", level="ERROR", context={"error": str(exc)})


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    scheduler.add_job(trading_job, "interval", seconds=settings.bot_interval_seconds, id="trading_job", replace_existing=True)
    if settings.auto_start_scheduler:
        scheduler.start()
