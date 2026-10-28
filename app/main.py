"""Application factory and ASGI entrypoint."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import Settings, get_settings
from app.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    resolved = settings if settings is not None else get_settings()
    setup_logging(resolved)

    application = FastAPI(
        title="Conduct Playbook Builder",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.include_router(health_router)
    return application


app = create_app()
