#!/bin/bash
ser -e

echo "Running migrations..."
python manage.py migrate --noinput

exec "$@"