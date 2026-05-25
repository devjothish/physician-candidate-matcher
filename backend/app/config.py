"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All sensitive values (API keys, database URLs) must be set via env vars
    or a .env file. No defaults for secrets - the app will fail fast on startup
    if they are missing.
    """

    # Secrets - no defaults, must be provided
    anthropic_api_key: str
    supabase_url: str
    supabase_key: str

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # Model configuration
    default_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-4-5-20251001"

    # Rate limiting
    rate_limit_per_minute: int = 20

    # Request limits
    max_candidates_per_request: int = 50

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Call once at startup, reuse everywhere."""
    return Settings()  # type: ignore[call-arg]
