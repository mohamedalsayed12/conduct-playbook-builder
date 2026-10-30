"""Unit tests for settings helpers."""

from app.config import Settings, normalize_database_url

_TEST_JWT_SECRET = "unit-test-jwt-secret-value-at-least-32-chars"


def test_normalize_database_url_rewrites_render_schemes() -> None:
    assert (
        normalize_database_url("postgres://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    assert (
        normalize_database_url("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )


def test_normalize_database_url_keeps_psycopg_urls() -> None:
    url = "postgresql+psycopg://conduct:conduct@localhost:5432/conduct"
    assert normalize_database_url(url) == url


def test_settings_normalizes_database_url_from_env_style_value() -> None:
    settings = Settings(
        app_env="test",
        jwt_secret=_TEST_JWT_SECRET,
        database_url="postgres://u:p@db:5432/app",
    )
    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/app"
