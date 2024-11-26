# Dockerfile
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV JUPYTER_ENABLE_LAB=yes
ENV JUPYTER_PLATFORM_DIRS=1
ENV DJANGO_SETTINGS_MODULE=peptide.settings
ENV BASE_PYTHONPATH=/app/include/peptide

# Update apt-get and install system dependencies
RUN apt-get update && apt-get install -y \
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
    libgdk-pixbuf2.0-0 \
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
RUN python3 -m ipykernel install --user 
#RUN jupyter nbextension enable --py widgetsnbextension


# Copy application files
COPY include /app/include

# Create required directories
RUN mkdir -p /app/include/peptide/uploads/temp && \
    chmod 700 /app/include/peptide/uploads/temp

# Trust notebooks
RUN jupyter trust /app/include/peptide/peptide/notebooks/Heatmap_Visualization_widget_volia.ipynb || echo "Warning: Could not trust notebook"

# Copy and setup start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh


# Set PYTHONPATH properly
ENV PYTHONPATH=/app/include/peptide:${BASE_PYTHONPATH}

# Expose ports for Django and Voila
EXPOSE 8000 8866

# Use the start script as the entry point
CMD ["/app/start.sh"]