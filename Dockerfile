# Dockerfile
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=peptide.settings
ENV BASE_PYTHONPATH=/app/include/peptide
ENV PIP_ROOT_USER_ACTION=ignore

# Add gosu for privilege dropping
RUN apt-get update && apt-get install -y gosu && \
    useradd -r -s /sbin/nologin celery_user && \
    rm -rf /var/lib/apt/lists/*

# Update apt-get and install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    dos2unix \
    nano \
    recode \
    sqlite3 \
    ncbi-blast+ \
    git \
    redis-server \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY include /app/include

# Create required directories and set permissions
RUN mkdir -p /app/include/peptide/uploads/temp && \
    chmod 750 /app/include/peptide/uploads/temp

RUN chown -R celery_user:celery_user /app/include/peptide && \
    chmod -R 755 /app/include/peptide && \
    touch /app/include/peptide/db.sqlite3 && \
    chown celery_user:celery_user /app/include/peptide/db.sqlite3 && \
    chmod 664 /app/include/peptide/db.sqlite3

# Copy and setup start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf


# Set PYTHONPATH properly
ENV PYTHONPATH=/app/include/peptide:${BASE_PYTHONPATH}

# Add these new commands for static files handling
WORKDIR /app/include/peptide

# Collect static files (BUILDING=true allows this without SECRET_KEY)
RUN BUILDING=true python manage.py collectstatic --noinput

# Make sure static files are accessible
RUN chmod -R 755 /app/include/peptide/static_files

# Create required directories and set permissions
RUN mkdir -p /app/include/peptide/static_files && \
    chmod -R 755 /app/include/peptide/static_files

# Expose port for Django
EXPOSE 8000

# Use the start script as the entry point
CMD ["/app/start.sh"]
