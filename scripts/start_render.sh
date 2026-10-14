#!/usr/bin/env bash
# Container entrypoint on Render: Temporal dev server, worker, then the web app on $PORT.
set -euo pipefail
mkdir -p /var/data
temporal server start-dev --db-filename /var/data/temporal.db --ui-port 8233 --log-level warn &
until nc -z localhost 7233 2>/dev/null; do sleep 0.5; done
python -m shelfmitra.worker &
exec python -m uvicorn shelfmitra.app:app --host 0.0.0.0 --port "${PORT:-10000}"
