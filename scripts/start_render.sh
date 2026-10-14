#!/usr/bin/env bash
# Container entrypoint (Render, Hugging Face Spaces): Temporal dev server, worker, then the web app on $PORT.
set -euo pipefail
DATA="${SHELFMITRA_DATA_DIR:-/var/data}"
mkdir -p "$DATA"
temporal server start-dev --db-filename "$DATA/temporal.db" --ui-port 8233 --log-level warn &
until nc -z localhost 7233 2>/dev/null; do sleep 0.5; done
python -m shelfmitra.worker &
exec python -m uvicorn shelfmitra.app:app --host 0.0.0.0 --port "${PORT:-10000}"
