#!/bin/sh
# Creates / updates every table before the API starts (idempotent: Alembic only applies what is missing).
# Set FV_AUTO_MIGRATE=false to disable and run `alembic upgrade head` yourself (e.g. as a pre-deploy step).
set -e
if [ "${FV_AUTO_MIGRATE:-true}" = "true" ]; then
  echo "[entrypoint] applying database migrations"
  alembic upgrade head
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
