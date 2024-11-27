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

# Setup trap for cleanup
trap cleanup SIGTERM SIGINT

# Start Redis server
echo "Starting Redis server..."
service redis-server start || echo "Redis server failed to start"

# Start Nginx server
echo "Starting Nginx..."
service nginx start || echo "Nginx failed to start"

# Reload Nginx configuration
echo "Reloading Nginx configuration..."
nginx -s reload || echo "Failed to reload Nginx configuration"

# Change to Django app directory
echo "Changing to Django application directory..."
cd /app/include/peptide

# Start Gunicorn in background
echo "Starting Gunicorn..."
gunicorn -b 127.0.0.1:8000 --timeout=600 peptide.wsgi:application &
GUNICORN_PID=$!

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A peptide worker --loglevel=info &
CELERY_PID=$!

# Change to notebooks directory
echo "Changing to Voilà notebooks directory..."
cd /app/include/peptide/peptide/notebooks

# Start Voilà in background
echo "Starting Voilà..."
voila \
    --no-browser \
    --port=8866 \
    --Voila.ip=127.0.0.1 \
    --template=lab \
    --enable_nbextensions=True \
    --debug \
    Heatmap_Visualization_widget_volia.ipynb &

# Keep the script running to handle signals
wait
