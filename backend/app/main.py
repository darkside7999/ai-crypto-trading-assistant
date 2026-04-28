from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import ai, auth, bot, logs, market, settings as settings_router, telegram, trades
from app.workers.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bot.router)
app.include_router(settings_router.router)
app.include_router(trades.router)
app.include_router(ai.router)
app.include_router(logs.router)
app.include_router(telegram.router)
app.include_router(market.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "phase_1_demo_only"}
