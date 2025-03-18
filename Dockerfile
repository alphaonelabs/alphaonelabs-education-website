# Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# Copy project files
COPY . .

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
