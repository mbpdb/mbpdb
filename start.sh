#!/bin/bash

# Start Redis server
service redis-server start

# Start Gunicorn
gunicorn -b 0.0.0.0:8000 --timeout=300 peptide.wsgi:application &

# Start Celery worker
celery -A peptide worker --loglevel=info
