#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.db" ] && source "$SCRIPT_DIR/../.env.db" || { echo "❌ .env.db not found"; exit 1; }

echo "🔍 Checking environment variables:"
echo "Host IP: $PRIMARY_VPS_DB_HOST_IP"
echo "Database: $PRIMARY_DB_NAME"
echo "User: $PRIMARY_DB_USER"
echo "Password: [hidden]"

command -v psql >/dev/null 2>&1 || { echo "❌ psql not found"; exit 1; }

# Check if port is open
timeout 1 bash -c "echo > /dev/tcp/$PRIMARY_VPS_DB_HOST_IP/5432" 2>/dev/null || { echo "❌ Port 5432 not open"; exit 1; }

# Try to connect and check for specific error message
echo "🔌 Attempting to connect to database..."
output=$(PGPASSWORD=$PRIMARY_VPS_DB_DB_PASSWORD psql -h $PRIMARY_VPS_DB_HOST_IP -U $PRIMARY_DB_USER -d $PRIMARY_DB_NAME -c "SELECT 1;" 2>&1)
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Successfully connected to database"
elif echo "$output" | grep -q "no pg_hba.conf entry for host"; then
    echo "✅ Connection successful (firewall passed) but authentication failed (expected)"
else
    echo "❌ Connection failed: $output"
    exit 1
fi
