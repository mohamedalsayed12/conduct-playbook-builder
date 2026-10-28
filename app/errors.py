"""Domain exceptions mapped to HTTP responses in one place."""


class AppError(Exception):
    """Base class for expected domain failures."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Requested entity does not exist (or is out of scope)."""


class ConflictError(AppError):
    """Request conflicts with current state."""


class InvalidStageTransitionError(ConflictError):
    """User cannot move to the requested onboarding stage."""


class InviteTokenInvalidError(AppError):
    """Invite token is unknown, expired, or already used (generic to clients)."""


class DefaultPlaybookMissingError(AppError):
    """No global default playbook exists to copy for a new tenant."""


class ValidationAppError(AppError):
    """Domain-level validation failure distinct from FastAPI request validation."""


class AuthenticationError(AppError):
    """Caller is missing or has invalid credentials."""


class ForbiddenError(AppError):
    """Caller is authenticated but not allowed to perform this action."""
