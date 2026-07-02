import functools
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq AI
    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"

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

    def validate_api_keys(self) -> None:
        """Validate that required API keys are set before making calls."""
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required. Get one free at console.groq.com")


@functools.lru_cache
def get_settings() -> Settings:
    """Lazy-load settings to avoid crash-on-import when env vars are missing."""
    return Settings()
