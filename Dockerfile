# Python base image
FROM python:3.10-slim@sha256:f9fd9a142c9e3bc54d906053b756eb7e7e386ee1cf784d82c251cf640c502512

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files first (needed for Poetry to install the project)
COPY . .

# Configure Poetry to not create virtualenvs (install to system Python)
ENV POETRY_VIRTUALENVS_CREATE=false

# Install Poetry and project dependencies

RUN python -m pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir poetry==1.8.3 && \
    POETRY_CACHE_DIR=/tmp/poetry-cache poetry install --only main --no-interaction --no-ansi && \
    rm -rf /tmp/poetry-cache /root/.cache/pip

# Create necessary directories for static files
RUN mkdir -p /app/static /app/staticfiles

# Create and configure environment variables
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

# Echo message during build
RUN echo "Your Project is now live on http://localhost:8000"

# Expose port
EXPOSE 8000

# Start the server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
