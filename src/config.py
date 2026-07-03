import functools
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI Backend: "openrouter" or "groq"
    ai_backend: str = "openrouter"

    # OpenRouter (default backend — Gemini models)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model_primary: str = "google/gemini-2.0-flash-001"
    openrouter_model_fallback: str = "google/gemini-2.5-flash"

    # Groq AI (used when ai_backend="groq")
    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"

    # CAP Protocol — CROO Network
    cap_api_url: str = "https://api.croo.network"
    cap_ws_url: str = "wss://api.croo.network/ws"
    cap_agent_id: str = ""
    cap_agent_wallet: str = ""
    cap_sdk_key: str = ""
    cap_private_key: str = ""
    cap_auto_connect: bool = True

    # Database (Cache)
    db_path: str = "datascout.db"

    # API Keys (optional data sources)
    kaggle_username: Optional[str] = None
    kaggle_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    noaa_api_key: Optional[str] = None
    core_api_key: Optional[str] = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Rate Limits
    max_concurrent_searches: int = 10
    request_timeout: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@functools.lru_cache
def get_settings() -> Settings:
    """Lazy-load settings to avoid crash-on-import when env vars are missing."""
    return Settings()
