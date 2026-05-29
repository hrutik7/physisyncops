#!/bin/sh
set -eu

cleanup() {
  if [ -n "${WORKER_PID:-}" ]; then
    kill "$WORKER_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

echo "Starting Celery worker for upload processing..."
.venv/bin/python -m celery -A app.celery_app worker -Q opentra --loglevel=info --concurrency=1 &
WORKER_PID=$!

echo "Starting FastAPI server on port 8000..."
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
