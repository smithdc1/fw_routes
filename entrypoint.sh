#!/bin/bash
set -e

echo "Starting django-tasks database worker..."
uv run --no-sync python manage.py db_worker &

echo "Starting Gunicorn..."
exec uv run --no-sync gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    gpx_routes.wsgi:application
