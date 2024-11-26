#!/bin/bash
set -e

# Start Redis server
service redis-server start || echo "Redis server failed to start"

# Change to Django app directory
cd /app/include/peptide

# Start Gunicorn in background
gunicorn -b 0.0.0.0:8000 --timeout=600 peptide.wsgi:application &
GUNICORN_PID=$!

# Start Celery worker in background
celery -A peptide worker --loglevel=info &
CELERY_PID=$!

# Change to notebooks directory
cd /app/include/peptide/peptide/notebooks

# Function to cleanup background processes
cleanup() {
    echo "Cleaning up processes..."
    kill $GUNICORN_PID 2>/dev/null || true
    kill $CELERY_PID 2>/dev/null || true
    exit 0
}

# Setup trap for cleanup
trap cleanup SIGTERM SIGINT

# Start Voila in foreground
exec voila \
    --no-browser \
    --port=8866 \
    --Voila.ip=0.0.0.0 \
    --template=lab \
    --enable_nbextensions=True \
    --debug \
    Heatmap_Visualization_widget_volia.ipynb
