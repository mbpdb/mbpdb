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

# Start Gunicorn in background.
#
# Concurrency note: this used to run gunicorn's default of a single sync
# worker, i.e. exactly one request in flight at a time with everything else
# queued in nginx. That contradicted the Container App scale rule, which is
# concurrentRequests=10 -- KEDA waited for 10 requests to pile up on a replica
# that could only ever serve one, so load turned into queueing latency instead
# of a second replica.
#
# Threads rather than extra worker processes, for two reasons:
#   - Memory. Peak WorkingSetBytes is ~1.67Gi against this container's 2Gi
#     limit (~78%), largely because the celery worker forks 4 prefork children.
#     Another gunicorn process would carry its own Django heap; threads share
#     one.
#   - SQLite. Each additional process means another connection contending for
#     the same write lock; threads don't reduce that to zero but don't multiply
#     the process count either.
# Work that is actually CPU-heavy goes to celery, so the GIL is not the binding
# constraint here -- these threads are waiting on SQLite reads and I/O.
#
# 8 threads also keeps /health/ answerable while a slow view is in flight,
# which the readiness probe (httpGet /health/, 5s timeout x3) depends on.
echo "Starting Gunicorn..."
# -c gunicorn.conf.py: enables per-request access logging to stdout (real
# client IP, path, status, user agent, referer) so Container App wake-ups can
# be attributed to real traffic vs crawlers. /health/ probe hits are filtered
# out there to keep the log readable.
gunicorn -c gunicorn.conf.py -b 127.0.0.1:8001 --timeout=600 \
    --worker-class gthread --workers 1 --threads 8 \
    peptide.wsgi:application &
GUNICORN_PID=$!

# celery_user and the ownership/permissions of uploads/ and db.sqlite3 are
# already set up at image build time (see Dockerfile) -- redoing them here
# on every cold start was pure wasted I/O on the boot critical path.

# Start Celery worker in background with non-root user
echo "Starting Celery worker..."
# --concurrency: celery defaults to the number of CPUs it can see, and it reads
# the *host's* count rather than the container's cgroup limit -- on this 1-CPU
# container it was forking 4 prefork children, each with its own Django heap.
# That was the main driver of the ~1.67Gi peak against a 2Gi limit. 2 children
# lets one task overlap another's I/O without oversubscribing a single core.
#
# --max-tasks-per-child: recycle children periodically so pandas/numpy
# allocations in the search tasks can't accumulate across a long-lived replica.
# Safe for celery (unlike gunicorn) since a child is only recycled between
# tasks, never mid-request.
gosu celery_user celery -A peptide worker --loglevel=info \
    --concurrency 2 --max-tasks-per-child 20 &
CELERY_PID=$!

# Wait for all background processes
wait