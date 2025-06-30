#!/bin/bash
set -e

# Function to cleanup background processes
cleanup() {
    echo "Cleaning up processes..."
    kill $GUNICORN_PID 2>/dev/null || true
    kill $CELERY_PID 2>/dev/null || true
    kill $VOILA_HEATMAP_PID 2>/dev/null || true
    kill $VOILA_DATA_PID 2>/dev/null || true
    kill $VOILA_DATA_VISUALIZATION_PID 2>/dev/null || true
    service nginx stop || echo "Failed to stop Nginx"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start Redis server
echo "Starting Redis server..."
service redis-server start || echo "Redis server failed to start"

# Start Nginx server
echo "Starting Nginx..."
nginx -t && service nginx start || echo "Nginx failed to start: $(nginx -t 2>&1)"

# Change to Django app directory
cd /app/include/peptide

# Run Django migrations
echo "Running Django migrations..."
python3 manage.py migrate --noinput

# Start Gunicorn in background
echo "Starting Gunicorn..."
gunicorn -b 127.0.0.1:8001 --timeout=600 peptide.wsgi:application &
GUNICORN_PID=$!

# Create a non-root user for Celery if it doesn't exist
if ! id -u celery_user > /dev/null 2>&1; then
    adduser --system --no-create-home --group celery_user
fi

# Ensure proper permissions for working directories
chown -R celery_user:celery_user /app/include/peptide/uploads
chmod 755 /app/include/peptide/uploads

# Ensure database has proper permissions
chown celery_user:celery_user /app/include/peptide/db.sqlite3
chmod 664 /app/include/peptide/db.sqlite3

# Start Celery worker in background with non-root user
echo "Starting Celery worker..."
gosu celery_user celery -A peptide worker --loglevel=info &
CELERY_PID=$!

# Change to notebooks directory
cd /app/include/peptide/peptide/notebooks

# Start Voilà instance for Heatmap
echo "Starting Voilà for Heatmap..."
voila \
    --no-browser \
    --port=8866 \
    --Voila.ip=127.0.0.1 \
    --template=lab \
    --Voila.base_url='/voila/' \
    --ServerApp.allow_origin='http://127.0.0.1:8000' \
    --ServerApp.allow_websocket_origin='127.0.0.1:8000' \
    --ServerApp.token="${VOILA_TOKEN}" \
    --ServerApp.allow_credentials=True \
    --Voila.tornado_settings allow_origin=* \
    --debug \
    Heatmap_Visualization_widget_volia.ipynb &
VOILA_HEATMAP_PID=$!

# Start Voilà instance for Data Transformation
echo "Starting Voilà for Data Transformation..."
voila \
    --no-browser \
    --port=8867 \
    --Voila.ip=127.0.0.1 \
    --template=lab \
    --Voila.base_url='/data/' \
    --ServerApp.allow_origin='http://127.0.0.1:8000' \
    --ServerApp.allow_websocket_origin='127.0.0.1:8000' \
    --ServerApp.token="${VOILA_TOKEN}" \
    --ServerApp.allow_credentials=True \
    --Voila.tornado_settings allow_origin=* \
    --debug \
    Data_Transformation_widget.ipynb &
VOILA_DATA_PID=$!

echo "Starting Voilà for Data Visualization..."
voila \
    --no-browser \
    --port=8868 \
    --Voila.ip=127.0.0.1 \
    --template=lab \
    --Voila.base_url='/data_visualization/' \
    --ServerApp.allow_origin='http://127.0.0.1:8000' \
    --ServerApp.allow_websocket_origin='127.0.0.1:8000' \
    --ServerApp.token="${VOILA_TOKEN}" \
    --ServerApp.allow_credentials=True \
    --Voila.tornado_settings allow_origin=* \
    --debug \
    Data_Vizualization.ipynb &
VOILA_DATA_VISUALIZATION_PID=$!

# Wait for all background processes
wait