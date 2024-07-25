# Use an official Python runtime as a parent image
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED 1

# Update apt-get and install system dependencies
RUN apt-get update && apt-get install -y \
    dos2unix \
    nano \
    recode \
    sqlite3 \
    ncbi-blast+ \
    git \
    redis-server
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed Python packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the include folder into the container
COPY include /app/include

# Create temp directory
RUN mkdir -p /app/include/peptide/uploads/temp
RUN chmod 700 /app/include/peptide/uploads/temp


# Explicitly copy start.sh
COPY start.sh /app/start.sh

# Make the start script executable
RUN chmod +x /app/start.sh



# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set Django settings module and PYTHONPATH
ENV DJANGO_SETTINGS_MODULE=peptide.settings

ENV PYTHONPATH include/peptide/:$PYTHONPATH

# Run your application
# CMD gunicorn -b 0.0.0.0:8000 --timeout=300 peptide.wsgi:application

# Run Redis, Django, and Celery
#CMD service redis-server start && \
#    gunicorn -b 0.0.0.0:8000 --timeout=300 peptide.wsgi:application & \
#    celery -A peptide worker --loglevel=info

# Use the script as the CMD
CMD ["/app/start.sh"]