# Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel FIRST
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies with PEP 517 disabled (for old setup.py packages)
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --no-use-pep517 -r requirements.txt
RUN python -m pip install --no-cache-dir mysqlclient

# Copy the rest of the app
COPY . .

# Create necessary directories
RUN mkdir -p /app/static /app/staticfiles

# Setup env variables
COPY .env.sample .env

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations and create test data
RUN python manage.py migrate && \
    python manage.py create_test_data

# Create superuser
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@example.com
ENV DJANGO_SUPERUSER_PASSWORD=adminpassword
RUN python manage.py createsuperuser --noinput

# Expose port
EXPOSE 8000

# Start the server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
