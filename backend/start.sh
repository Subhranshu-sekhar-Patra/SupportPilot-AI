#!/usr/bin/env bash
# SupportPilot AI — Cloud Web Service Startup Script (Render / Koyeb / Docker)
set -e

echo "==> Running Alembic database migrations..."
python -m alembic upgrade head

echo "==> Starting Uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
