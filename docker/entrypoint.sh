#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate

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
