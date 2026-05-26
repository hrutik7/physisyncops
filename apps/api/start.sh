#!/bin/sh

# Start the Celery worker in the background with limited concurrency (1 worker process)
# to prevent exceeding Render's 512MB free tier RAM limit (OOM crash)
echo "🚀 Starting Celery worker in background with concurrency=1..."
celery -A app.celery_app worker -Q opentra --loglevel=info --concurrency=1 &

# Start the FastAPI server in the foreground
echo "🚀 Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
