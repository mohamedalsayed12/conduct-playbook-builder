#!/bin/sh
# Start the API. Free Render plans cannot run preDeployCommand, so migrate
# and seed here before binding $PORT (defaults to 8000 for local Docker).
set -eu
/app/scripts/render_predeploy.sh
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
