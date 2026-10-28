"""Prove the core schema migration upgrades and downgrades cleanly."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db import get_engine, reset_db_caches


def test_migration_upgrade_and_downgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = get_engine()
    inspector = inspect(engine)
    assert "tenants" in inspector.get_table_names()
    assert "users" in inspector.get_table_names()
    assert "invites" in inspector.get_table_names()
    assert "stage_events" in inspector.get_table_names()
    assert "strategist_assignments" in inspector.get_table_names()
    assert "playbooks" in inspector.get_table_names()
    assert "playbook_steps" in inspector.get_table_names()

    command.downgrade(alembic_config, "base")
    reset_db_caches()
    engine = get_engine()
    inspector = inspect(engine)
    remaining_tables = set(inspector.get_table_names())
    assert "tenants" not in remaining_tables
    assert remaining_tables <= {"alembic_version"}

    with engine.connect() as connection:
        enums = (
            connection.execute(
                text("SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname")
            )
            .scalars()
            .all()
        )
    assert enums == []

    command.upgrade(alembic_config, "head")
    reset_db_caches()
    inspector = inspect(get_engine())
    assert "tenants" in inspector.get_table_names()
