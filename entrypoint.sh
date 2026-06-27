#!/bin/sh
set -e

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "Waiting for database..."
while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 0.5
done
echo "Database ready."

echo "Waiting for Redis..."
while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
  sleep 0.5
done
echo "Redis ready."

python manage.py migrate --noinput
exec "$@"
