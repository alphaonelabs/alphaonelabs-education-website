#!/bin/bash
set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PROJECT_ROOT/.env.production"

# Create a password file for ssh connections
PASS_FILE=$(mktemp)
echo "$PRIMARY_VPS_PASSWORD" > "$PASS_FILE"
chmod 600 "$PASS_FILE"

# Helper function to run commands on the remote server
run_remote() {
    sshpass -f "$PASS_FILE" ssh -o StrictHostKeyChecking=no "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP" "$1"
}

# Copy required files to server
sshpass -f "$PASS_FILE" scp -o StrictHostKeyChecking=no "$PROJECT_ROOT/.env.production" "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP:/tmp/.env"
sshpass -f "$PASS_FILE" scp -o StrictHostKeyChecking=no "$PROJECT_ROOT/requirements.txt" "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP:/tmp/requirements.txt"

# Create project directory and copy .env file
run_remote "mkdir -p /home/$PRIMARY_VPS_USER/$PROJECT_NAME"
run_remote "cp /tmp/.env /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env"
run_remote "chmod 600 /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env"

# Install required packages
run_remote "apt-get update -y && apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git ufw openssl curl"

# Configure firewall
run_remote "ufw allow 'Nginx Full' && ufw allow ssh && ufw --force enable"

# Set up repository - Improved handling of non-empty directories
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
if [ -d \".git\" ]; then \
    # Directory is already a git repository
    git fetch origin && git reset --hard origin/main || git reset --hard origin/master; \
else \
    # Directory exists but not a git repository
    # Save .env file if it exists
    if [ -f \".env\" ]; then \
        cp .env /tmp/.env.backup; \
    fi; \
    # Clear directory but keep hidden files that start with .env
    find . -mindepth 1 -not -name '.env*' -delete; \
    # Clone repository
    git clone $REPO_URL /tmp/repo_temp && \
    cp -a /tmp/repo_temp/. . && \
    rm -rf /tmp/repo_temp; \
    # Restore .env file if we backed it up
    if [ -f \"/tmp/.env.backup\" ]; then \
        cp /tmp/.env.backup .env; \
    fi; \
fi"

# Set up Python environment
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r /tmp/requirements.txt && \
pip install uvicorn psycopg2-binary"

# Configure PostgreSQL
run_remote "sudo -u postgres psql -c \"CREATE DATABASE $PRIMARY_DB_NAME;\" 2>/dev/null || true && \
sudo -u postgres psql -c \"CREATE USER $PRIMARY_DB_USER WITH PASSWORD '$PRIMARY_DB_PASSWORD';\" 2>/dev/null || true && \
sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $PRIMARY_DB_NAME TO $PRIMARY_DB_USER;\" 2>/dev/null || true && \
sudo -u postgres psql -c \"ALTER USER $PRIMARY_DB_USER CREATEDB;\" 2>/dev/null || true && \
sudo -u postgres psql -c \"ALTER ROLE $PRIMARY_DB_USER WITH LOGIN;\" 2>/dev/null || true && \
sudo -u postgres psql -d $PRIMARY_DB_NAME -c \"GRANT ALL ON SCHEMA public TO $PRIMARY_DB_USER;\" 2>/dev/null || true && \
sudo -u postgres psql -d $PRIMARY_DB_NAME -c \"ALTER USER $PRIMARY_DB_USER WITH SUPERUSER;\" 2>/dev/null || true && \
\
if ! grep -q \"$PRIMARY_DB_USER\" /etc/postgresql/*/main/pg_hba.conf; then \
  sudo bash -c \"echo 'local   $PRIMARY_DB_NAME    $PRIMARY_DB_USER    md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo bash -c \"echo 'host    $PRIMARY_DB_NAME    $PRIMARY_DB_USER    127.0.0.1/32    md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo bash -c \"echo 'host    $PRIMARY_DB_NAME    $PRIMARY_DB_USER    ::1/128         md5' >> /etc/postgresql/*/main/pg_hba.conf\" && \
  sudo systemctl restart postgresql; \
fi"

# Django migrations and static files
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
source venv/bin/activate && \
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE && \
export DATABASE_URL=\"postgres://$PRIMARY_DB_USER:$PRIMARY_DB_PASSWORD@localhost:5432/$PRIMARY_DB_NAME\" && \

python manage.py migrate --noinput
python manage.py collectstatic --noinput"

# Create Nginx configuration
run_remote "
cat > /tmp/nginx_config << 'EOF'
server {
    listen 80;
    server_name SERVER_NAME_PLACEHOLDER;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias PROJECT_ROOT_PLACEHOLDER/staticfiles/;
        expires 30d;
    }

    location /media/ {
        root PROJECT_ROOT_PLACEHOLDER;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:APP_PORT_PLACEHOLDER;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Replace placeholders with actual values
sed -i \"s|SERVER_NAME_PLACEHOLDER|${PRIMARY_DOMAIN_NAME} ${PRIMARY_VPS_IP} localhost|g\" /tmp/nginx_config
sed -i \"s|PROJECT_ROOT_PLACEHOLDER|/home/${PRIMARY_VPS_USER}/${PROJECT_NAME}|g\" /tmp/nginx_config
sed -i \"s|APP_PORT_PLACEHOLDER|${APP_PORT}|g\" /tmp/nginx_config

sudo mv /tmp/nginx_config /etc/nginx/sites-available/${PROJECT_NAME} && \
sudo ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/ && \
sudo rm -f /etc/nginx/sites-enabled/default"

# Create systemd service
run_remote "
cat > /tmp/systemd_service << 'EOF'
[Unit]
Description=uvicorn daemon for PROJECT_NAME_PLACEHOLDER
After=network.target postgresql.service

[Service]
User=root
Group=www-data
WorkingDirectory=PROJECT_ROOT_PLACEHOLDER
ExecStart=PROJECT_ROOT_PLACEHOLDER/venv/bin/uvicorn --host 0.0.0.0 --port APP_PORT_PLACEHOLDER --workers 2 web.asgi:application
Restart=always
Environment=\"DJANGO_SETTINGS_MODULE=DJANGO_SETTINGS_MODULE_PLACEHOLDER\"
Environment=\"ALLOWED_HOSTS=SERVER_NAME_PLACEHOLDER localhost 127.0.0.1\"
Environment=\"DEBUG=False\"
Environment=\"DATABASE_URL=postgres://DB_USER_PLACEHOLDER:DB_PASSWORD_PLACEHOLDER@localhost:5432/DB_NAME_PLACEHOLDER\"

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
sudo mkdir -p /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/media /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/static && \
sudo chown -R root:www-data /home/${PRIMARY_VPS_USER}/${PROJECT_NAME} && \
sudo chmod -R g+w /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/media && \
sudo chmod -R g+w /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/static && \
sudo chmod -R 755 /home/${PRIMARY_VPS_USER}/${PROJECT_NAME}/venv"

# Start services
run_remote "sudo systemctl daemon-reload && \
sudo systemctl restart postgresql && \
sudo systemctl enable postgresql && \
sudo systemctl start uvicorn_$PROJECT_NAME && \
sudo systemctl enable uvicorn_$PROJECT_NAME && \
sudo systemctl restart nginx && \
sudo systemctl enable nginx"

# Cleanup
rm -f "$PASS_FILE"
