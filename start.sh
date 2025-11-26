#!/bin/bash
set -e

# Function to cleanup background processes
cleanup() {
    echo "Cleaning up processes..."
    kill $GUNICORN_PID 2>/dev/null || true
    kill $CELERY_PID 2>/dev/null || true
    kill $VOILA_HEATMAP_PID 2>/dev/null || true
    kill $VOILA_DATA_PID 2>/dev/null || true
    kill $VOILA_DATA_ANALYSIS_PID 2>/dev/null || true
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

# Function to run Voila with auto-restart on crash
run_voila_with_restart() {
    local name=$1
    local port=$2
    local base_url=$3
    local notebook=$4
    
    while true; do
        echo "Starting Voilà for $name on port $port..."
        voila \
            --no-browser \
            --port=$port \
            --Voila.ip=127.0.0.1 \
            --template=lab \
            --Voila.base_url="$base_url" \
            --ServerApp.allow_origin='http://127.0.0.1:8000' \
            --ServerApp.allow_websocket_origin='127.0.0.1:8000' \
            --ServerApp.token="${VOILA_TOKEN}" \
            --ServerApp.allow_credentials=True \
            --Voila.tornado_settings allow_origin=* \
            --Voila.preheat_kernel=True \
            --Voila.cull_idle_timeout=0 \
            --MappingKernelManager.cull_idle_timeout=0 \
            --MappingKernelManager.cull_interval=0 \
            --VoilaExecutor.timeout=600 \
            --debug \
            "$notebook"
        
        exit_code=$?
        echo "Voilà $name exited with code $exit_code. Restarting in 3 seconds..."
        sleep 3
    done
}

# Start Voilà instances with auto-restart in background
run_voila_with_restart "Heatmap" 8866 "/voila/heatmap/" "heatmap_visualization.ipynb" &
VOILA_HEATMAP_PID=$!

sleep 3

run_voila_with_restart "Data Transformation" 8867 "/voila/data_transformation/" "data_transformation.ipynb" &
VOILA_DATA_PID=$!

sleep 3

run_voila_with_restart "Data Analysis" 8868 "/voila/data_analysis/" "data_analysis.ipynb" &
VOILA_DATA_ANALYSIS_PID=$!

# Wait for all background processes
wait