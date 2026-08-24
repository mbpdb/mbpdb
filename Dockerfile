# Dockerfile
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=peptide.settings
ENV PYTHONPATH=/app/include/peptide
ENV PIP_ROOT_USER_ACTION=ignore

# System dependencies + gosu (privilege dropping) + celery_user, in one
# update/install/cleanup instead of two (was two separate `apt-get update`
# round-trips and layers for no reason).
#
# Removed vs. the previous list: python3-dev/pip/setuptools/wheel/cffi and
# libcairo2/libpango-1.0-0/libpangocairo-1.0-0/libgdk-pixbuf-2.0-0/libffi-dev/
# shared-mime-info. Nothing in requirements.txt or the app code touches
# system cairo/pango/cffi (no weasyprint/cairosvg/cairocffi; kaleido bundles
# its own headless Chromium), and the app's pip installs always run against
# the base image's own /usr/local Python, not the system python3 that
# python3-pip/setuptools/wheel would provide. build-essential is kept as a
# fallback in case a requirements.txt package ever needs to compile from
# source instead of using a prebuilt wheel.
RUN apt-get update && apt-get install -y \
    gosu \
    nginx \
    dos2unix \
    nano \
    recode \
    sqlite3 \
    ncbi-blast+ \
    git \
    redis-server \
    build-essential \
    curl \
    && useradd -r -s /sbin/nologin celery_user \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY include /app/include

# Ownership + baseline permissions first, then the tighter/looser
# exceptions on top -- the previous order set uploads/temp to 750 and then
# immediately overwrote it back to 755 with the recursive chmod below, so
# that restriction never actually took effect.
RUN chown -R celery_user:celery_user /app/include/peptide && \
    chmod -R 755 /app/include/peptide && \
    touch /app/include/peptide/db.sqlite3 && \
    chown celery_user:celery_user /app/include/peptide/db.sqlite3 && \
    chmod 664 /app/include/peptide/db.sqlite3 && \
    mkdir -p /app/include/peptide/uploads/temp && \
    chown celery_user:celery_user /app/include/peptide/uploads/temp && \
    chmod 750 /app/include/peptide/uploads/temp

# Copy and setup start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

WORKDIR /app/include/peptide

# Collect static files (BUILDING=true allows this without SECRET_KEY)
# --verbosity 1 reduces "Found another file" duplicate messages
RUN BUILDING=true python manage.py collectstatic --noinput --verbosity 1 && \
    chmod -R 755 /app/include/peptide/static_files

# Expose port for Django
EXPOSE 8000

# Use the start script as the entry point
CMD ["/app/start.sh"]
