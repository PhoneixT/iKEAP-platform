#!/bin/sh
set -eu
python -m alembic upgrade head
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python -m app.infrastructure.seed --demo
else
  python -m app.infrastructure.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
