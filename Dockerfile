# Use a minimal Python base image
FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends && \
    python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/static /app/staticfiles

# Copy environment variables
COPY .env.sample .env

# Collects static files (migrations should not be run here)
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Using an entrypoint script instead of running commands in Dockerfile
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
