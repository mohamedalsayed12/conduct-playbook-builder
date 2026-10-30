#!/bin/sh
# Run before each Render deploy: schema first, then idempotent demo seed.
set -eu
alembic upgrade head
python scripts/seed.py
