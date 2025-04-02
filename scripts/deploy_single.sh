#!/bin/bash
set -e
VERSION="1.0.0"
# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# We'll directly use environment variables from .env.production
source "$PROJECT_ROOT/.env.production"


echo "Starting deployment to $PRIMARY_HOSTNAME ($PRIMARY_VPS_IP)"

# Create a password file for ssh connections
PASS_FILE=$(mktemp)
echo "$PRIMARY_VPS_PASSWORD" > "$PASS_FILE"
chmod 600 "$PASS_FILE"

# Clear known hosts
ssh-keygen -R "$PRIMARY_VPS_IP" &> /dev/null

# Test SSH connection
echo "Testing SSH connection..."
if ! sshpass -f "$PASS_FILE" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP" "echo 'Connection successful'"; then
    echo "SSH connection failed."
    rm -f "$PASS_FILE"
    exit 1
fi
echo "✅ SSH connection successful"

# Helper function to run commands on the remote server
run_remote() {
    sshpass -f "$PASS_FILE" ssh -o StrictHostKeyChecking=no "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP" "$1"
}

# Helper function for diagnostics
run_diagnostics() {
    echo "🔍 Running comprehensive diagnostics..."

    echo "📂 Checking directory structure and permissions:"
    run_remote "ls -la /home/$PRIMARY_VPS_USER/$PROJECT_NAME/ | head -n 20"
    run_remote "ls -la /home/$PRIMARY_VPS_USER/$PROJECT_NAME/static/ 2>/dev/null || echo 'Static directory not found or empty'"

    echo "🔍 Checking Nginx default site:"
    run_remote "ls -la /etc/nginx/sites-enabled/"

    echo "🗄️ Checking database connection:"
    run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
        source venv/bin/activate && \
        python -c \"
import sys, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('✅ Database connection successful')
except Exception as e:
    print('❌ Database connection failed:', e)
    sys.exit(1)
\""

    echo "🔒 Checking PostgreSQL roles and permissions:"
    run_remote "sudo -u postgres psql -c '\\du' | grep $PRIMARY_DB_USER"
    run_remote "sudo -u postgres psql -c '\\l' | grep $PRIMARY_DB_NAME"

    echo "🌐 Checking web server and application status:"
    run_remote "sudo systemctl status nginx --no-pager"
    run_remote "sudo systemctl status uvicorn_$PROJECT_NAME --no-pager"
    run_remote "sudo netstat -tulpn | grep -E '$APP_PORT|80'"

    echo "📜 Checking recent logs:"
    run_remote "sudo journalctl -u uvicorn_$PROJECT_NAME -n 30 --no-pager"
    run_remote "sudo tail -n 20 /var/log/nginx/error.log"

    echo "⚙️ Checking Django settings:"
    run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
        source venv/bin/activate && \
        python -c \"
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
django.setup()
from django.conf import settings
print('ALLOWED_HOSTS =', settings.ALLOWED_HOSTS)
print('DEBUG =', settings.DEBUG)
print('STATIC_ROOT =', settings.STATIC_ROOT)
print('STATIC_URL =', settings.STATIC_URL)
print('DATABASES =', settings.DATABASES)
print('CSRF_COOKIE_SECURE =', getattr(settings, 'CSRF_COOKIE_SECURE', False))
print('CSRF_TRUSTED_ORIGINS =', getattr(settings, 'CSRF_TRUSTED_ORIGINS', []))
print('MIDDLEWARE =', settings.MIDDLEWARE)
\""

    echo "🚦 Testing HTTP request to server:"
    run_remote "curl -v -H 'Host: $PRIMARY_DOMAIN_NAME' http://localhost"

    echo "📡 Testing direct request to app server:"
    run_remote "curl -v http://localhost:$APP_PORT"

    echo "🔍 Checking Nginx configuration:"
    run_remote "sudo nginx -T | grep -A 20 '$PRIMARY_DOMAIN_NAME'"

    echo "🔍 Checking for Welcome to nginx! page:"
    run_remote "curl -s http://localhost | grep -i 'welcome to nginx'"
}

# Copy required files to server
echo "Copying files to server..."
sshpass -f "$PASS_FILE" scp -o StrictHostKeyChecking=no "$PROJECT_ROOT/.env.production" "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP:/tmp/.env"
sshpass -f "$PASS_FILE" scp -o StrictHostKeyChecking=no "$PROJECT_ROOT/requirements.txt" "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP:/tmp/requirements.txt"
echo "✅ Files copied to server"

# Create project directory and copy .env file
echo "Setting up project directory..."
run_remote "mkdir -p /home/$PRIMARY_VPS_USER/$PROJECT_NAME"
run_remote "cp /tmp/.env /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env"
run_remote "chmod 600 /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env"
echo "✅ Project directory set up"

# Install required packages
echo "Installing system packages..."
run_remote "
# Wait for any apt/dpkg locks to be released
wait_apt() {
    echo \"Waiting for apt/dpkg locks to be released...\"
    while sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1 || sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        echo \"Waiting for package manager lock...\"
        sleep 5
    done
}

wait_apt
apt-get update -y && apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git ufw openssl curl"
echo "✅ System packages installed"

# Configure firewall
echo "Configuring firewall..."
run_remote "ufw allow 'Nginx Full' && ufw allow ssh && ufw --force enable"
echo "✅ Firewall configured"

# Set up repository
echo "Setting up repository..."
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
if [ -d \".git\" ]; then \
    git fetch origin && \
    git reset --hard origin/main || git reset --hard origin/master; \
    echo \"✅ Repository updated\"; \
else \
    if [ \"\$(ls -A)\" ]; then \
        echo \"Directory not empty. Attempting to initialize git repository...\"; \
        if git init && git remote add origin $REPO_URL; then \
            git fetch && \
            git checkout -f -t origin/main || git checkout -f -t origin/master; \
            echo \"✅ Repository initialized and updated\"; \
        else \
            echo \"Cannot initialize git. Cleaning directory and cloning...\"; \
            cp .env /tmp/.env.backup && \
            rm -rf * .[^.]* && \
            cp /tmp/.env.backup .env && \
            git clone $REPO_URL .; \
            echo \"✅ Repository cloned after cleaning directory\"; \
        fi; \
    else \
        git clone $REPO_URL .; \
        echo \"✅ Repository cloned\"; \
    fi; \
fi"
echo "✅ Repository setup complete"

# Set up Python environment
echo "Setting up Python environment..."
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r /tmp/requirements.txt && \
pip install uvicorn psycopg2-binary"
echo "✅ Python environment ready"

# Configure PostgreSQL
echo "Configuring database..."
run_remote "sudo -u postgres psql -c \"CREATE DATABASE $PRIMARY_DB_NAME;\" || echo \"Database exists\" && \
sudo -u postgres psql -c \"CREATE USER $PRIMARY_DB_USER WITH PASSWORD '$PRIMARY_DB_PASSWORD';\" || echo \"User exists\" && \
sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $PRIMARY_DB_NAME TO $PRIMARY_DB_USER;\" || echo \"Grant done\" && \
sudo -u postgres psql -c \"ALTER USER $PRIMARY_DB_USER CREATEDB;\" || echo \"CREATEDB granted\" && \
sudo -u postgres psql -c \"ALTER ROLE $PRIMARY_DB_USER WITH LOGIN;\" || echo \"LOGIN granted\" && \
sudo -u postgres psql -d $PRIMARY_DB_NAME -c \"GRANT ALL ON SCHEMA public TO $PRIMARY_DB_USER;\" || echo \"SCHEMA permissions granted\" && \
sudo -u postgres psql -d $PRIMARY_DB_NAME -c \"ALTER USER $PRIMARY_DB_USER WITH SUPERUSER;\" || echo \"SUPERUSER granted\" && \
\
# Update PostgreSQL authentication configuration if needed
if ! grep -q \"$PRIMARY_DB_USER\" /etc/postgresql/*/main/pg_hba.conf; then
  echo \"Updating PostgreSQL authentication configuration...\" && \
  sudo bash -c \"echo 'local   $PRIMARY_DB_NAME    $PRIMARY_DB_USER    md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo bash -c \"echo 'host    $PRIMARY_DB_NAME    $PRIMARY_DB_USER    127.0.0.1/32    md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo bash -c \"echo 'host    $PRIMARY_DB_NAME    $PRIMARY_DB_USER    ::1/128         md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo systemctl restart postgresql
fi"
echo "✅ Database configured"

# Django migrations and static files
echo "Running Django migrations and collecting static files..."
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
source venv/bin/activate && \
export POSTGRES_DB=$PRIMARY_DB_NAME && \
export POSTGRES_USER=$PRIMARY_DB_USER && \
export POSTGRES_PASSWORD=$PRIMARY_DB_PASSWORD && \
export POSTGRES_HOST=localhost && \
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE && \
export ALLOWED_HOSTS=\"$PRIMARY_DOMAIN_NAME $PRIMARY_VPS_IP localhost 127.0.0.1\" && \
export DEBUG=False && \
export DATABASE_URL=\"postgres://$PRIMARY_DB_USER:$PRIMARY_DB_PASSWORD@localhost:5432/$PRIMARY_DB_NAME\" && \

# Create a local_settings.py file to override settings
cat > /home/$PRIMARY_VPS_USER/$PROJECT_NAME/web/local_settings.py << 'SETTINGS_EOF'
import os

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', ''),
        'USER': os.environ.get('POSTGRES_USER', ''),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': '5432',
    }
}

CSRF_TRUSTED_ORIGINS = ['http://' + host for host in ALLOWED_HOSTS] + ['https://' + host for host in ALLOWED_HOSTS]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SETTINGS_EOF

# Ensure settings.py imports local_settings.py
if ! grep -q 'local_settings' /home/$PRIMARY_VPS_USER/$PROJECT_NAME/web/settings.py; then
    echo 'Adding import for local_settings.py to settings.py...'
    cat >> /home/$PRIMARY_VPS_USER/$PROJECT_NAME/web/settings.py << 'IMPORT_EOF'

# Import local settings (must be at the end of the file)
try:
    from .local_settings import *
except ImportError:
    pass
IMPORT_EOF
fi

echo 'Running migrations with database settings:' && \
echo \"Database: $PRIMARY_DB_NAME, User: $PRIMARY_DB_USER\" && \
echo \"ALLOWED_HOSTS: $PRIMARY_DOMAIN_NAME $PRIMARY_VPS_IP localhost 127.0.0.1\" && \
{ python manage.py migrate --noinput; MIGRATE_STATUS=\$?; if [ \$MIGRATE_STATUS -ne 0 ]; then echo \"Migration failed with status \$MIGRATE_STATUS\"; python manage.py migrate --noinput -v 3; exit \$MIGRATE_STATUS; fi; } && \
python manage.py collectstatic --noinput"
echo "✅ Django setup complete"

# Create Nginx configuration
echo "Configuring web server..."
run_remote "
cat > /tmp/nginx_config << 'EOF'
server {
    listen 80;
    server_name SERVER_NAME_PLACEHOLDER LOCALHOST_PLACEHOLDER;

    # Detailed error logging
    error_log /var/log/nginx/error.log debug;
    access_log /var/log/nginx/access.log;

    # Increase buffer size to handle larger headers
    client_max_body_size 20M;
    client_body_buffer_size 128k;
    client_header_buffer_size 2k;
    large_client_header_buffers 4 4k;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root PROJECT_ROOT_PLACEHOLDER;
        expires 30d;
        add_header Cache-Control \"public, max-age=2592000\";
    }

    location /media/ {
        root PROJECT_ROOT_PLACEHOLDER;
        expires 30d;
        add_header Cache-Control \"public, max-age=2592000\";
    }

    location / {
        proxy_pass http://127.0.0.1:APP_PORT_PLACEHOLDER;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;

        # Extended timeout settings
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        send_timeout 300s;

        # Handling larger headers
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
}
EOF

# Replace placeholders with actual values
sed -i \"s|SERVER_NAME_PLACEHOLDER|${PRIMARY_DOMAIN_NAME} ${PRIMARY_VPS_IP}|g\" /tmp/nginx_config
sed -i \"s|LOCALHOST_PLACEHOLDER|localhost|g\" /tmp/nginx_config
sed -i \"s|PROJECT_ROOT_PLACEHOLDER|/home/${PRIMARY_VPS_USER}/${PROJECT_NAME}|g\" /tmp/nginx_config
sed -i \"s|APP_PORT_PLACEHOLDER|${APP_PORT}|g\" /tmp/nginx_config

sudo mv /tmp/nginx_config /etc/nginx/sites-available/${PROJECT_NAME} && \
sudo ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/ && \
sudo rm -f /etc/nginx/sites-enabled/default && \
sudo nginx -t || echo \"WARNING: Nginx configuration test failed\""
echo "✅ Web server configured"

# Create systemd service
echo "Creating application service..."
run_remote "
cat > /tmp/systemd_service << 'EOF'
[Unit]
Description=uvicorn daemon for PROJECT_NAME_PLACEHOLDER
After=network.target postgresql.service

[Service]
User=root
Group=www-data
WorkingDirectory=PROJECT_ROOT_PLACEHOLDER
ExecStart=PROJECT_ROOT_PLACEHOLDER/venv/bin/uvicorn --host 0.0.0.0 --port APP_PORT_PLACEHOLDER --workers 2 --timeout-keep-alive 300 web.asgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=\"DJANGO_SETTINGS_MODULE=DJANGO_SETTINGS_MODULE_PLACEHOLDER\"
Environment=\"ALLOWED_HOSTS=SERVER_NAME_PLACEHOLDER localhost 127.0.0.1\"
Environment=\"DEBUG=False\"
Environment=\"DATABASE_URL=postgres://DB_USER_PLACEHOLDER:DB_PASSWORD_PLACEHOLDER@localhost:5432/DB_NAME_PLACEHOLDER\"
Environment=\"POSTGRES_DB=DB_NAME_PLACEHOLDER\"
Environment=\"POSTGRES_USER=DB_USER_PLACEHOLDER\"
Environment=\"POSTGRES_PASSWORD=DB_PASSWORD_PLACEHOLDER\"
Environment=\"POSTGRES_HOST=localhost\"

[Install]
WantedBy=multi-user.target
EOF

# Replace placeholders with actual values
sed -i \"s|PROJECT_NAME_PLACEHOLDER|${PROJECT_NAME}|g\" /tmp/systemd_service
sed -i \"s|PROJECT_ROOT_PLACEHOLDER|/home/${PRIMARY_VPS_USER}/${PROJECT_NAME}|g\" /tmp/systemd_service
sed -i \"s|APP_PORT_PLACEHOLDER|${APP_PORT}|g\" /tmp/systemd_service
sed -i \"s|DJANGO_SETTINGS_MODULE_PLACEHOLDER|${DJANGO_SETTINGS_MODULE}|g\" /tmp/systemd_service
sed -i \"s|SERVER_NAME_PLACEHOLDER|${PRIMARY_DOMAIN_NAME} ${PRIMARY_VPS_IP}|g\" /tmp/systemd_service
sed -i \"s|DB_USER_PLACEHOLDER|${PRIMARY_DB_USER}|g\" /tmp/systemd_service
sed -i \"s|DB_PASSWORD_PLACEHOLDER|${PRIMARY_DB_PASSWORD}|g\" /tmp/systemd_service
sed -i \"s|DB_NAME_PLACEHOLDER|${PRIMARY_DB_NAME}|g\" /tmp/systemd_service

sudo mv /tmp/systemd_service /etc/systemd/system/uvicorn_${PROJECT_NAME}.service && \
sudo mkdir -p /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/media && \
sudo mkdir -p /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/static && \
sudo chown -R root:www-data /home/${PRIMARY_VPS_USER}/${PROJECT_NAME} && \
sudo chmod -R g+w /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/media && \
sudo chmod -R g+w /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/static && \
sudo chmod -R 755 /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/venv"
echo "✅ Application service created"

# Start services
echo "Starting services..."
run_remote "sudo systemctl daemon-reload && \
sudo systemctl restart postgresql && \
sudo systemctl enable postgresql && \
sudo systemctl start uvicorn_$PROJECT_NAME && \
sudo systemctl enable uvicorn_$PROJECT_NAME && \
sudo systemctl restart nginx && \
sudo systemctl enable nginx"
echo "✅ Services started"


# Cleanup
rm -f "$PASS_FILE"

echo "Deployment completed"
