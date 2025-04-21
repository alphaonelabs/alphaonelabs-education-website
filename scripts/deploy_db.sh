#!/bin/bash
set -e

# these scripts are not final versions, they existing to get a working connection and will be refined / secured further

# Source environment variables
if [ ! -f .env.db ]; then
    echo "❌ .env.db file not found"
    exit 1
fi

source .env.db

if [ -z "$PRIMARY_VPS_DB_HOST_PASSWORD" ]; then
    echo "❌ PRIMARY_VPS_DB_HOST_PASSWORD not set in .env.db"
    exit 1
fi

if [ -z "$PRIMARY_DB_USER" ]; then
    echo "❌ PRIMARY_DB_USER not set in .env.db"
    exit 1
fi

if [ -z "$PRIMARY_DB_NAME" ]; then
    echo "❌ PRIMARY_DB_NAME not set in .env.db"
    exit 1
fi

echo "======================================================================"
echo "🐘 PostgreSQL Installation and Configuration"
echo "======================================================================"

# Function to run remote commands
run_remote() {
    local desc=$1
    shift
    local cmd=$1
    local attempt=1
    local max=3
    local delay=5

    echo "🔄 $desc"
    echo "📝 Command: $cmd"

    while ((attempt <= max)); do
        echo "📝 Attempt $attempt/$max"
        if sshpass -p "$PRIMARY_VPS_DB_HOST_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 "root@$PRIMARY_VPS_DB_HOST_IP" "$cmd"; then
            echo "✅ $desc succeeded"
            return 0
        fi
        echo "❌ $desc failed (attempt $attempt/$max)"
        ((attempt++))
        sleep $delay
    done

    echo "❌ $desc: all $max attempts failed"
    exit 1
}

# Install PostgreSQL
echo "📦 Installing PostgreSQL..."
run_remote "Installing PostgreSQL" "sudo apt install -y postgresql"

# Disable UFW
echo "🛡️ Disabling UFW..."
run_remote "Disabling UFW" "sudo ufw disable"

# Restart PostgreSQL service
echo "🔄 Restarting PostgreSQL service..."
run_remote "Restarting PostgreSQL" "sudo systemctl restart postgresql"

# Configure PostgreSQL to allow connections from all hosts
echo "🔧 Configuring PostgreSQL network settings..."

# Update postgresql.conf to listen on all interfaces
run_remote "Updating postgresql.conf" "sudo sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" /etc/postgresql/*/main/postgresql.conf"

# Restart PostgreSQL to apply changes
echo "🔄 Restarting PostgreSQL to apply changes..."
run_remote "Restarting PostgreSQL" "sudo systemctl restart postgresql"

echo "✅ PostgreSQL installation and configuration completed successfully!"
