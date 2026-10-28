"""Map domain exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    DefaultPlaybookMissingError,
    ForbiddenError,
    InviteTokenInvalidError,
    NotFoundError,
    ValidationAppError,
)


def register_exception_handlers(application: FastAPI) -> None:
    """Attach the single domain-exception handler set to the app."""

    @application.exception_handler(NotFoundError)
    async def not_found_handler(
        _request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @application.exception_handler(ConflictError)
    async def conflict_handler(
        _request: Request,
        exc: ConflictError,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @application.exception_handler(AuthenticationError)
    async def authentication_handler(
        _request: Request,
        exc: AuthenticationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @application.exception_handler(ForbiddenError)
    async def forbidden_handler(
        _request: Request,
        exc: ForbiddenError,
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @application.exception_handler(InviteTokenInvalidError)
    async def invite_invalid_handler(
        _request: Request,
        exc: InviteTokenInvalidError,
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @application.exception_handler(DefaultPlaybookMissingError)
    async def default_playbook_handler(
        _request: Request,
        exc: DefaultPlaybookMissingError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @application.exception_handler(ValidationAppError)
    async def validation_handler(
        _request: Request,
        exc: ValidationAppError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @application.exception_handler(AppError)
    async def app_error_handler(
        _request: Request,
        exc: AppError,
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})
