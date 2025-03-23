#!/bin/sh

# Apply database migrations
python manage.py migrate

# Create test data (if needed)
python manage.py create_test_data

# Create superuser (only if it doesn't exist)
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='admin').exists() or \
User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword')" \
| python manage.py shell

# Start the server
exec python manage.py runserver 0.0.0.0:8000
