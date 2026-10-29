"""CLI entrypoint: `make seed` / `uv run python scripts/seed.py`."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow `python scripts/seed.py` without installing the package editable path quirks.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.config import get_settings
from app.db import get_session_factory, reset_db_caches
from app.logging import setup_logging
from app.services.seed import run_seed


def main() -> int:
    """Run idempotent seed against DATABASE_URL and exit 0."""
    settings = get_settings()
    setup_logging(settings)
    reset_db_caches()
    session = get_session_factory()()
    try:
        report = run_seed(session)
    finally:
        session.close()
    logging.getLogger(__name__).info(
        "seed_cli_finished created_playbooks=%s created_tenants=%s "
        "created_users=%s created_assignments=%s",
        report.playbooks_created,
        report.tenants_created,
        report.users_created,
        report.assignments_created,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
