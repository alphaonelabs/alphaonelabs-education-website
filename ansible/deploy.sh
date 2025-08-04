#!/bin/bash
set -e
# Change to script directory
cd "$(dirname "$0")"

# ─── Load env file from project root if present ────────────────────────────
PROJECT_ROOT="$(cd .. && pwd)"
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

# ─── VPS connection details ───────────────────────────────────────────────
VPS_IP="${VPS_IP:-}"
VPS_USER="${VPS_USER:-root}"
VPS_PASSWORD="${VPS_PASSWORD:-}"

if [[ -z "$VPS_IP" ]]; then
  echo "❌ VPS_IP not set (export or add to .env)." >&2
  exit 1
fi

# Forward any extra args to ansible-playbook
EXTRA_ARGS=("$@")

ANSIBLE_CMD=(ansible-playbook -i "${VPS_IP}," -u "$VPS_USER" playbook.yml)

if [[ -n "$VPS_PASSWORD" ]]; then
  ANSIBLE_CMD+=(--extra-vars "ansible_password=${VPS_PASSWORD}")
else
  ANSIBLE_CMD+=(--ask-pass)
fi

exec "${ANSIBLE_CMD[@]}" "${EXTRA_ARGS[@]}"
