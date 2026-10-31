#!/bin/sh
# Render-only boot. Free plans cannot run preDeployCommand, so migrate and
# seed here. Local Compose does not use this script.
set -eu
/app/scripts/render_predeploy.sh
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
