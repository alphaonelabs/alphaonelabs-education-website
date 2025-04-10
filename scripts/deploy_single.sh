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

# Copy environment file to server
sshpass -f "$PASS_FILE" scp -o StrictHostKeyChecking=no "$PROJECT_ROOT/.env.production" "$PRIMARY_VPS_USER@$PRIMARY_VPS_IP:/tmp/.env"

# Install required packages
run_remote "apt-get update -y && apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git ufw openssl curl nginx-extras"

# Configure firewall
run_remote "ufw allow 'Nginx Full' && ufw allow ssh && ufw --force enable"

# Create an empty project directory and clone the repository
run_remote "rm -rf /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
mkdir -p /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
git clone $REPO_URL . && \
cp /tmp/.env /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env && \
chmod 600 /home/$PRIMARY_VPS_USER/$PROJECT_NAME/.env"

# Set up Python environment
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
pip install psycopg2-binary"

# Configure PostgreSQL
run_remote "
# Create database and user
sudo -u postgres psql -c \"CREATE DATABASE $PRIMARY_DB_NAME;\" 2>/dev/null || true
sudo -u postgres psql -c \"CREATE USER $PRIMARY_DB_USER WITH PASSWORD '$PRIMARY_DB_PASSWORD';\" 2>/dev/null || true
sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $PRIMARY_DB_NAME TO $PRIMARY_DB_USER;\" 2>/dev/null || true
sudo -u postgres psql -c \"ALTER USER $PRIMARY_DB_USER CREATEDB;\" 2>/dev/null || true
sudo -u postgres psql -c \"ALTER USER $PRIMARY_DB_USER WITH LOGIN SUPERUSER;\" 2>/dev/null || true
sudo -u postgres psql -d $PRIMARY_DB_NAME -c \"GRANT ALL ON SCHEMA public TO $PRIMARY_DB_USER;\" 2>/dev/null || true"

# Django migrations and static files
run_remote "cd /home/$PRIMARY_VPS_USER/$PROJECT_NAME && \
source venv/bin/activate && \
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE && \
export DATABASE_URL=\"postgres://$PRIMARY_DB_USER:$PRIMARY_DB_PASSWORD@localhost:5432/$PRIMARY_DB_NAME\" && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput"

# Create Nginx configuration with direct variable interpolation
PROJECT_PATH="/home/$PRIMARY_VPS_USER/$PROJECT_NAME"
run_remote "cat > /tmp/nginx_config << EOF
server {
    listen 80;
    server_name $PRIMARY_DOMAIN_NAME $PRIMARY_VPS_IP localhost;

    more_clear_headers Server;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias $PROJECT_PATH/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
EOF

sudo mv /tmp/nginx_config /etc/nginx/sites-available/$PROJECT_NAME && \
sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/ && \
sudo rm -f /etc/nginx/sites-enabled/default"

# Create systemd service with direct variable interpolation
run_remote "cat > /tmp/systemd_service << EOF
[Unit]
Description=uvicorn
After=network.target postgresql.service

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_PATH
ExecStart=$PROJECT_PATH/venv/bin/uvicorn --host 0.0.0.0 --port $APP_PORT --workers 2 web.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/systemd_service /etc/systemd/system/uvicorn.service && \
sudo mkdir -p $PROJECT_PATH/static && \
sudo chown -R root:www-data $PROJECT_PATH && \
sudo chmod -R g+w $PROJECT_PATH/static && \
sudo chmod -R 755 $PROJECT_PATH/venv"

# Start services
run_remote "sudo systemctl daemon-reload && \
sudo systemctl restart postgresql && \
sudo systemctl enable postgresql && \
sudo systemctl start uvicorn && \
sudo systemctl enable uvicorn && \
sudo systemctl restart nginx && \
sudo systemctl enable nginx"

# Cleanup
rm -f "$PASS_FILE"
