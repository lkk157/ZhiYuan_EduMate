#!/bin/sh
set -eu

echo "Waiting for database migrations..."
attempt=0
while ! alembic upgrade head; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "Database migration failed after ${attempt} attempts." >&2
        exit 1
    fi
    echo "Migration attempt ${attempt} failed; retrying in 2s..."
    sleep 2
done

echo "Starting EduMate API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
