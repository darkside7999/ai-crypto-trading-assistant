from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Crypto Trading Assistant"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./trading.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str | None = (
        r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$"
    )

    admin_username: str = "admin"
    admin_password: str = "change-this-password"
    auth_secret_key: str = "change-this-long-random-secret"

    default_mode: Literal["DEMO", "REAL"] = "DEMO"
    default_control_mode: Literal["MANUAL", "AUTONOMOUS"] = "MANUAL"
    bot_interval_seconds: int = 60
    auto_start_scheduler: bool = False

    binance_testnet_api_key: str | None = None
    binance_testnet_secret: str | None = None
    binance_real_api_key: str | None = None
    binance_real_secret: str | None = None

    openrouter_api_key: str | None = None
    nvidia_api_key: str | None = None
    ai_provider: str = "disabled"
    ai_enabled: bool = False
    ai_model: str = "google/gemini-2.5-flash-lite"
    ai_fallback_model: str = "deepseek/deepseek-chat-v3.1"
    ai_max_calls_per_day: int = 200
    ai_max_input_tokens: int = 6000
    ai_max_output_tokens: int = 800
    ai_temperature: float = 0.1

    market_intel_enable_coingecko: bool = True
    market_intel_rss_urls: str = ""
    market_data_provider: str = "kraken_public"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("default_mode")
    @classmethod
    def force_demo_default(cls, value: str) -> str:
        return "DEMO" if value != "DEMO" else value

    @field_validator("cors_origin_regex")
    @classmethod
    def empty_regex_to_none(cls, value: str | None) -> str | None:
        return value or None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def market_intel_rss_url_list(self) -> list[str]:
        return [url.strip() for url in self.market_intel_rss_urls.split(",") if url.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
