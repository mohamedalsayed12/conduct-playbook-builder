"""Application factory and ASGI entrypoint."""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.errors import register_exception_handlers
from app.api.health import router as health_router
from app.api.invites import router as invites_router
from app.api.playbooks import router as playbooks_router
from app.api.summary import router as summary_router
from app.api.tenants import router as tenants_router
from app.api.users import router as users_router
from app.config import Settings, get_settings
from app.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    resolved = settings if settings is not None else get_settings()
    setup_logging(resolved)

    application = FastAPI(
        title="Conduct Playbook Builder",
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(tenants_router)
    application.include_router(invites_router)
    application.include_router(users_router)
    application.include_router(summary_router)
    application.include_router(playbooks_router)
    return application


app = create_app()
