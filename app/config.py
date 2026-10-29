"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_JWT_SECRET_LENGTH = 32
_JWT_SECRET_PLACEHOLDER_FRAGMENTS = (
    "change-me",
    "replace-with",
    "your-own-long-random",
    "not-a-secret",
)
# Rejected only in production so .env.example can keep a local-dev secret.
_JWT_SECRET_PRODUCTION_FORBIDDEN_FRAGMENTS = (
    "do-not-use",
    "local-dev",
)


class Settings(BaseSettings):
    """Runtime configuration. All values come from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://conduct:conduct@localhost:5432/conduct"
    redis_url: str = "redis://localhost:6379/0"
    invite_expiry_hours: int = 72
    max_page_size: int = 100
    default_page_size: int = 20
    jwt_secret: str
    jwt_expiry_minutes: int = 30
    stuck_after_days: int = 7
    summary_cache_ttl_seconds: int = 60

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> Self:
        """Require a long secret; reject placeholders outside the test environment."""
        secret = self.jwt_secret
        if len(secret) < _MIN_JWT_SECRET_LENGTH:
            message = f"jwt_secret must be at least {_MIN_JWT_SECRET_LENGTH} characters"
            raise ValueError(message)
        lowered = secret.lower()
        if self.app_env != "test" and any(
            fragment in lowered for fragment in _JWT_SECRET_PLACEHOLDER_FRAGMENTS
        ):
            raise ValueError("jwt_secret looks like a placeholder; set a real secret")
        if self.app_env == "production" and any(
            fragment in lowered
            for fragment in _JWT_SECRET_PRODUCTION_FORBIDDEN_FRAGMENTS
        ):
            raise ValueError(
                "jwt_secret must not use a local-dev or example value in production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    # jwt_secret is required and supplied via env / .env by pydantic-settings.
    return Settings()  # type: ignore[call-arg]
