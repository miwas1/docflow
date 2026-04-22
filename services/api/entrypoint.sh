#!/bin/sh
# Entrypoint for the API service.
# Runs database migrations then starts the uvicorn server.
set -e

cd /app/services/api

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn api_service.main:app --host 0.0.0.0 --port 8000
