"""create_core_schema

Revision ID: 7bc384335d62
Revises:
Create Date: 2026-10-28 15:22:27.655678
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7bc384335d62"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role_enum = postgresql.ENUM(
    "strategist",
    "customer_admin",
    "end_user",
    name="user_role",
    create_type=False,
)
sap_role_enum = postgresql.ENUM(
    "developer",
    "analyst",
    "process_owner",
    "architect",
    name="sap_role",
    create_type=False,
)
user_stage_enum = postgresql.ENUM(
    "invited",
    "activated",
    "first_use",
    "active",
    name="user_stage",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "strategist",
        "customer_admin",
        "end_user",
        name="user_role",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "developer",
        "analyst",
        "process_owner",
        "architect",
        name="sap_role",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "invited",
        "activated",
        "first_use",
        "active",
        name="user_stage",
    ).create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "playbooks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_playbooks_tenant_id"),
        "playbooks",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("sap_role", sap_role_enum, nullable=True),
        sa.Column("stage", user_stage_enum, nullable=False),
        sa.Column("stage_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(role = 'strategist' AND tenant_id IS NULL) OR "
            "(role <> 'strategist' AND tenant_id IS NOT NULL)",
            name="ck_users_strategist_tenant",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index(
        "ix_users_tenant_stage",
        "users",
        ["tenant_id", "stage"],
        unique=False,
    )
    op.create_index(
        "ix_users_tenant_stage_changed_at",
        "users",
        ["tenant_id", "stage_changed_at"],
        unique=False,
    )
    op.create_table(
        "invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_invites_token_hash"),
    )
    op.create_index(op.f("ix_invites_user_id"), "invites", ["user_id"], unique=False)
    op.create_table(
        "playbook_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("playbook_id", sa.UUID(), nullable=False),
        sa.Column("stage", user_stage_enum, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_within_days", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["playbook_id"], ["playbooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "playbook_id",
            "stage",
            "position",
            name="uq_playbook_steps_playbook_stage_position",
        ),
    )
    op.create_table(
        "stage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("from_stage", user_stage_enum, nullable=True),
        sa.Column("to_stage", user_stage_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stage_events_tenant_user",
        "stage_events",
        ["tenant_id", "user_id"],
        unique=False,
    )
    op.create_table(
        "strategist_assignments",
        sa.Column("strategist_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategist_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("strategist_id", "tenant_id"),
    )


def downgrade() -> None:
    op.drop_table("strategist_assignments")
    op.drop_index("ix_stage_events_tenant_user", table_name="stage_events")
    op.drop_table("stage_events")
    op.drop_table("playbook_steps")
    op.drop_index(op.f("ix_invites_user_id"), table_name="invites")
    op.drop_table("invites")
    op.drop_index("ix_users_tenant_stage_changed_at", table_name="users")
    op.drop_index("ix_users_tenant_stage", table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_playbooks_tenant_id"), table_name="playbooks")
    op.drop_table("playbooks")
    op.drop_table("tenants")

    bind = op.get_bind()
    postgresql.ENUM(name="user_stage").drop(bind, checkfirst=True)
    postgresql.ENUM(name="sap_role").drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_role").drop(bind, checkfirst=True)
