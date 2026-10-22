#!/bin/sh
set -eu
python manage.py migrate --noinput
if [ "${DEMO_MODE:-false}" = true ]; then
    python manage.py seed_demo
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 \
    --no-control-socket \
    --workers 2 --threads 2 --timeout 60 --worker-tmp-dir /tmp \
    --access-logfile - --error-logfile -
