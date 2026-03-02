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

# Run database migrations (ensures schema is up to date on every deploy)
echo "Running database migrations..."
python manage.py migrate --run-syncdb --noinput || { echo "WARNING: Migrations failed"; }

# Clear expired sessions (reduces stale/corrupted session warnings)
python manage.py clearsessions 2>/dev/null || true

# Create superuser if credentials are provided and user doesn't exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Checking for superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    print('Creating superuser...')
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '${DJANGO_SUPERUSER_EMAIL:-}', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
" || echo "Warning: Could not create superuser"
fi

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

# Wait for all background processes
wait