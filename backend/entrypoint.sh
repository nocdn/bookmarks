#!/bin/sh

set -e

echo "Starting Gunicorn..."

exec gunicorn app:app --bind 0.0.0.0:4871
