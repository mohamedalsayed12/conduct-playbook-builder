"""Domain enumerations persisted as PostgreSQL ENUM types."""

from enum import StrEnum

from sqlalchemy import Enum


class UserRole(StrEnum):
    """Access role for a user account."""

    STRATEGIST = "strategist"
    CUSTOMER_ADMIN = "customer_admin"
    END_USER = "end_user"


class SapRole(StrEnum):
    """SAP job function for customer end users."""

    DEVELOPER = "developer"
    ANALYST = "analyst"
    PROCESS_OWNER = "process_owner"
    ARCHITECT = "architect"


class UserStage(StrEnum):
    """Onboarding stage for a user within a tenant."""

    INVITED = "invited"
    ACTIVATED = "activated"
    FIRST_USE = "first_use"
    ACTIVE = "active"


def pg_enum[T: StrEnum](enum_cls: type[T], name: str) -> Enum:
    """Build a native PostgreSQL ENUM column type from a StrEnum."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda members: [member.value for member in members],
    )


# Single shared instances so Alembic creates each PG enum type once.
USER_ROLE_ENUM = pg_enum(UserRole, "user_role")
SAP_ROLE_ENUM = pg_enum(SapRole, "sap_role")
USER_STAGE_ENUM = pg_enum(UserStage, "user_stage")
