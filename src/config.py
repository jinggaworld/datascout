import functools
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI Backend: "groq" or "proxy" (ds2api)
    ai_backend: str = "groq"

    # Groq AI (used when ai_backend="groq")
    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"

    # DS2API Proxy (used when ai_backend="proxy")
    proxy_base_url: str = "http://127.0.0.1:5001"
    proxy_api_key: str = ""
    proxy_model_primary: str = "deepseek-v4-flash"
    proxy_model_fallback: str = "deepseek-v4-flash-nothinking"

    # CAP Protocol
    cap_api_url: str = "https://api.croo.network"
    cap_ws_url: str = "wss://api.croo.network/ws"
    cap_agent_id: str = ""
    cap_agent_wallet: str = ""

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
