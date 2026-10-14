#!/usr/bin/env bash
# Runs ShelfMitra locally: Temporal dev server, the worker and the web app.
# Usage: scripts/run_local.sh   (then open http://localhost:8000, Temporal UI at http://localhost:8233)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . ./.env; set +a
export SSL_CERT_FILE="$(.venv/bin/python -c 'import certifi;print(certifi.where())')"
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-localhost:7233}"
mkdir -p data logs
temporal server start-dev --db-filename data/temporal.db --ui-port 8233 --log-level warn > logs/temporal.log 2>&1 &
TPID=$!
trap 'kill $TPID $WPID 2>/dev/null' EXIT
until nc -z localhost 7233 2>/dev/null; do sleep 0.5; done
.venv/bin/python -m shelfmitra.worker > logs/worker.log 2>&1 &
WPID=$!
.venv/bin/python -m uvicorn shelfmitra.app:app --host 0.0.0.0 --port "${PORT:-8000}"
