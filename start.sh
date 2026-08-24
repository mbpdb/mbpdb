#!/bin/bash
set -e

# Function to cleanup background processes
cleanup() {
    echo "Cleaning up processes..."
    kill $GUNICORN_PID 2>/dev/null || true
    kill $CELERY_PID 2>/dev/null || true
    service nginx stop || echo "Failed to stop Nginx"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start Redis server
echo "Starting Redis server..."
service redis-server start || echo "Redis server failed to start"

# Start Nginx server
echo "Starting Nginx..."
nginx -t && service nginx start || { echo "Nginx failed to start: $(nginx -t 2>&1)"; exit 1; }

# Change to Django app directory
cd /app/include/peptide

# Migrate + clearsessions + superuser check in one process (one interpreter
# start, one django.setup()) instead of three separate manage.py invocations.
echo "Running startup bootstrap (migrate, clearsessions, superuser check)..."
python manage.py bootstrap || echo "WARNING: bootstrap step failed"

# Start Gunicorn in background
echo "Starting Gunicorn..."
gunicorn -b 127.0.0.1:8001 --timeout=600 peptide.wsgi:application &
GUNICORN_PID=$!

# celery_user and the ownership/permissions of uploads/ and db.sqlite3 are
# already set up at image build time (see Dockerfile) -- redoing them here
# on every cold start was pure wasted I/O on the boot critical path.

# Start Celery worker in background with non-root user
echo "Starting Celery worker..."
gosu celery_user celery -A peptide worker --loglevel=info &
CELERY_PID=$!

# Wait for all background processes
wait