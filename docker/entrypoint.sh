#!/usr/bin/env bash
set -euo pipefail

# Wait for database to be ready with retry loop
attempts=0
max_attempts="${DB_MAX_ATTEMPTS:-30}"
sleep_seconds="${DB_RETRY_SLEEP:-2}"
until python manage.py migrate --noinput; do
  attempts=$((attempts+1))
  if [ "$attempts" -ge "$max_attempts" ]; then
    echo "Database not ready after $max_attempts attempts. Exiting."
    exit 1
  fi
  echo "Waiting for database... attempt $attempts/$max_attempts"
  sleep "$sleep_seconds"
done

# Optional: seed test data if desired at runtime
if [[ "${CREATE_TEST_DATA:-0}" == "1" ]]; then
  if python manage.py help | grep -qE '^\s*create_test_data\s'; then
    python manage.py create_test_data
  else
    echo "Skipping test data: management command 'create_test_data' not found."
  fi
fi

if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py shell - <<'PY'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(username=os.environ["DJANGO_SUPERUSER_USERNAME"], defaults={"email": os.environ["DJANGO_SUPERUSER_EMAIL"], "is_staff": True, "is_superuser": True})
u.email = os.environ["DJANGO_SUPERUSER_EMAIL"]
u.set_password(os.environ["DJANGO_SUPERUSER_PASSWORD"])
u.is_staff = True
u.is_superuser = True
u.save()
print(f"Superuser {'created' if created else 'updated'}: {u.username}")
PY
fi

exec "$@"
