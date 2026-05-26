#!/bin/sh

# Start the Celery worker in the background
echo "🚀 Starting Celery worker in background..."
celery -A app.celery_app worker -Q opentra --loglevel=info &

# Start the FastAPI server in the foreground
echo "🚀 Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
