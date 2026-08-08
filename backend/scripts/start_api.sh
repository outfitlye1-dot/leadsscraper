#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

# Long-lived workers (scraper jobs, outreach) need a single process unless you
# add Redis/shared job storage. Keep WORKERS=1 on Railway.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers "$WORKERS" \
  --proxy-headers \
  --forwarded-allow-ips='*'
