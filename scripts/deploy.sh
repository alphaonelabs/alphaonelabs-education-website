#!/bin/bash
set -e

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${GREEN}$1${NC}"
}

error() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${RED}ERROR: $1${NC}" >&2
}

warn() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING: $1${NC}"
}

info() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${BLUE}INFO: $1${NC}"
}

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
    log "Loaded environment variables from .env file"
fi

# Default values with environment variable support
PROJECT_NAME="${PROJECT_NAME:-"education-website"}"
PYTHON_VERSION="${PYTHON_VERSION:-"3.10"}"
APP_PORT="${APP_PORT:-8000}"
DEBUG="${DEBUG:-False}"

# Server 1 (Primary) configuration
PRIMARY_VPS_IP="${PRIMARY_VPS_IP:-""}"
PRIMARY_VPS_USER="${PRIMARY_VPS_USER:-""}"
PRIMARY_VPS_PASSWORD="${PRIMARY_VPS_PASSWORD:-""}"
PRIMARY_DOMAIN_NAME="${PRIMARY_DOMAIN_NAME:-""}"
PRIMARY_DB_NAME="${PRIMARY_DB_NAME:-"${PROJECT_NAME//-/_}_primary"}"
PRIMARY_DB_USER="${PRIMARY_DB_USER:-${PRIMARY_VPS_USER}}"
PRIMARY_DB_PASSWORD="${PRIMARY_DB_PASSWORD:-"$(openssl rand -base64 12)"}"

# Server 2 (Secondary) configuration
SECONDARY_VPS_IP="${SECONDARY_VPS_IP:-""}"
SECONDARY_VPS_USER="${SECONDARY_VPS_USER:-""}"
SECONDARY_VPS_PASSWORD="${SECONDARY_VPS_PASSWORD:-""}"
SECONDARY_DOMAIN_NAME="${SECONDARY_DOMAIN_NAME:-""}"
SECONDARY_DB_NAME="${SECONDARY_DB_NAME:-"${PROJECT_NAME//-/_}_secondary"}"
SECONDARY_DB_USER="${SECONDARY_DB_USER:-${SECONDARY_VPS_USER}}"
SECONDARY_DB_PASSWORD="${SECONDARY_DB_PASSWORD:-"$(openssl rand -base64 12)"}"

# Common configuration
SECRET_KEY="${SECRET_KEY:-"$(openssl rand -base64 32)"}"
STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-""}"
STRIPE_PUBLISHABLE_KEY="${STRIPE_PUBLISHABLE_KEY:-""}"
STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-""}"
SENDGRID_PASSWORD="${SENDGRID_PASSWORD:-""}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-""}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to ensure sshpass is installed
ensure_sshpass() {
    if ! command_exists sshpass; then
        log "sshpass is not installed. Installing it now..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y sshpass
        elif command_exists yum; then
            sudo yum install -y sshpass
        elif command_exists brew; then
            brew install hudochenkov/sshpass/sshpass
        else
            error "Could not install sshpass. Please install it manually."
            exit 1
        fi
    fi
}

# Interactive input function
get_input() {
    local prompt="$1"
    local var_name="$2"
    local default_value="${!var_name}"
    local result=""

    if [ -n "$default_value" ]; then
        read -p "$prompt [$default_value]: " result
        result="${result:-$default_value}"
    else
        read -p "$prompt: " result
        while [ -z "$result" ]; do
            read -p "$prompt (cannot be empty): " result
        done
    fi

    eval "$var_name=\"$result\""
}

# Function to get password input (hidden)
get_password() {
    local prompt="$1"
    local var_name="$2"
    local default_value="${!var_name}"
    local result=""

    if [ -n "$default_value" ]; then
        read -s -p "$prompt [$default_value - press enter to keep or type new password]: " result
        echo
        result="${result:-$default_value}"
    else
        read -s -p "$prompt: " result
        echo
        while [ -z "$result" ]; do
            read -s -p "$prompt (cannot be empty): " result
            echo
        done
    fi

    eval "$var_name=\"$result\""
}

# Function to prompt for server information if not provided
prompt_for_server_info() {
    log "Please provide information for the primary server:"
    get_input "Primary server IP address" PRIMARY_VPS_IP
    get_input "Primary server username" PRIMARY_VPS_USER
    get_password "Primary server password" PRIMARY_VPS_PASSWORD
    get_input "Primary server domain name (optional)" PRIMARY_DOMAIN_NAME
    get_input "Primary database name" PRIMARY_DB_NAME
    get_input "Primary database user" PRIMARY_DB_USER
    get_password "Primary database password" PRIMARY_DB_PASSWORD

    echo
    log "Please provide information for the secondary server:"
    get_input "Secondary server IP address" SECONDARY_VPS_IP
    get_input "Secondary server username" SECONDARY_VPS_USER
    get_password "Secondary server password" SECONDARY_VPS_PASSWORD
    get_input "Secondary server domain name (optional)" SECONDARY_DOMAIN_NAME
    get_input "Secondary database name" SECONDARY_DB_NAME
    get_input "Secondary database user" SECONDARY_DB_USER
    get_password "Secondary database password" SECONDARY_DB_PASSWORD
}

# Function to check if required variables are set
check_required_vars() {
    local missing_vars=()

    [ -z "$PRIMARY_VPS_IP" ] && missing_vars+=("PRIMARY_VPS_IP")
    [ -z "$PRIMARY_VPS_USER" ] && missing_vars+=("PRIMARY_VPS_USER")
    [ -z "$PRIMARY_VPS_PASSWORD" ] && missing_vars+=("PRIMARY_VPS_PASSWORD")

    [ -z "$SECONDARY_VPS_IP" ] && missing_vars+=("SECONDARY_VPS_IP")
    [ -z "$SECONDARY_VPS_USER" ] && missing_vars+=("SECONDARY_VPS_USER")
    [ -z "$SECONDARY_VPS_PASSWORD" ] && missing_vars+=("SECONDARY_VPS_PASSWORD")

    if [ ${#missing_vars[@]} -gt 0 ]; then
        warn "The following environment variables are not set:"
        for var in "${missing_vars[@]}"; do
            echo "- $var"
        done

        read -p "Do you want to enter these values now? (y/n): " prompt
        if [[ "$prompt" =~ ^[Yy]$ ]]; then
            prompt_for_server_info
        else
            error "Required variables are not set. Exiting."
            exit 1
        fi
    fi
}

# Function to run a command on a server
run_command_on_server() {
    local ip="$1"
    local user="$2"
    local password="$3"
    local command="$4"

    log "Running command on server $ip: $command"
    sshpass -p "$password" ssh -o StrictHostKeyChecking=no $user@$ip "$command"
}

# Function to copy a file to a server
copy_file_to_server() {
    local ip="$1"
    local user="$2"
    local password="$3"
    local src="$4"
    local dest="$5"

    log "Copying file to server $ip: $src -> $dest"
    sshpass -p "$password" scp -o StrictHostKeyChecking=no "$src" $user@$ip:"$dest"
}

# Function to create a temporary setup script for a server
create_server_setup_script() {
    local server_type="$1"  # "PRIMARY" or "SECONDARY"
    local vps_ip="${server_type}_VPS_IP"
    local vps_user="${server_type}_VPS_USER"
    local vps_password="${server_type}_VPS_PASSWORD"
    local domain_name="${server_type}_DOMAIN_NAME"
    local db_name="${server_type}_DB_NAME"
    local db_user="${server_type}_DB_USER"
    local db_password="${server_type}_DB_PASSWORD"

    # Use indirect variable references
    vps_ip="${!vps_ip}"
    vps_user="${!vps_user}"
    vps_password="${!vps_password}"
    domain_name="${!domain_name}"
    db_name="${!db_name}"
    db_user="${!db_user}"
    db_password="${!db_password}"

    # Create a temporary script
    local tmp_script=$(mktemp)

    # Add environment variables to the script
    cat << EOF > "$tmp_script"
#!/bin/bash
set -e

# Environment variables
export SERVER_TYPE="$server_type"
export PROJECT_NAME="$PROJECT_NAME"
export DOMAIN_NAME="$domain_name"
export APP_PORT="$APP_PORT"
export DB_NAME="$db_name"
export DB_USER="$db_user"
export DB_PASSWORD="$db_password"
export VPS_USER="$vps_user"
export SECRET_KEY="$SECRET_KEY"
export DEBUG="$DEBUG"
export PRIMARY_VPS_IP="$PRIMARY_VPS_IP"
export SECONDARY_VPS_IP="$SECONDARY_VPS_IP"
export PRIMARY_DB_NAME="$PRIMARY_DB_NAME"
export PRIMARY_DB_USER="$PRIMARY_DB_USER"
export PRIMARY_DB_PASSWORD="$PRIMARY_DB_PASSWORD"
export SECONDARY_DB_NAME="$SECONDARY_DB_NAME"
export SECONDARY_DB_USER="$SECONDARY_DB_USER"
export SECONDARY_DB_PASSWORD="$SECONDARY_DB_PASSWORD"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] \$1"
}

# Function to install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3-pip python3-full nginx git certbot python3-certbot-nginx ufw fail2ban \
        postgresql postgresql-contrib python3-dev libpq-dev build-essential
}

# Function to setup PostgreSQL
setup_postgresql() {
    log "Setting up PostgreSQL..."
    sudo -u postgres psql -c "CREATE USER \$DB_USER WITH PASSWORD '\$DB_PASSWORD';" || true
    sudo -u postgres psql -c "CREATE DATABASE \$DB_NAME WITH OWNER \$DB_USER;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \$DB_NAME TO \$DB_USER;" || true

    # Allow remote connections to PostgreSQL for the other server
    if [ "\$SERVER_TYPE" = "PRIMARY" ]; then
        log "Configuring PostgreSQL to accept connections from Secondary server..."
        PEER_IP="$SECONDARY_VPS_IP"
    else
        log "Configuring PostgreSQL to accept connections from Primary server..."
        PEER_IP="$PRIMARY_VPS_IP"
    fi

    # Update pg_hba.conf to allow connections from the other server
    sudo bash -c "echo 'host    \$DB_NAME    \$DB_USER    \$PEER_IP/32    md5' >> /etc/postgresql/*/main/pg_hba.conf"

    # Update postgresql.conf to listen on all interfaces
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf

    # Restart PostgreSQL to apply changes
    sudo systemctl restart postgresql
}

# Function to setup firewall
setup_firewall() {
    log "Setting up firewall..."
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80
    sudo ufw allow 443

    # Allow PostgreSQL connections from the other server
    if [ "\$SERVER_TYPE" = "PRIMARY" ]; then
        sudo ufw allow from $SECONDARY_VPS_IP to any port 5432
    else
        sudo ufw allow from $PRIMARY_VPS_IP to any port 5432
    fi

    sudo ufw --force enable
}

# Function to setup fail2ban
setup_fail2ban() {
    log "Setting up fail2ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
}

# Function to setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install uvicorn gunicorn psycopg2-binary
}

# Function to create database router
create_database_router() {
    log "Creating database router..."

    mkdir -p /home/\${VPS_USER}/\${PROJECT_NAME}/web/routers

    cat > /home/\${VPS_USER}/\${PROJECT_NAME}/web/routers/__init__.py << 'EOL'
# Database routers package
EOL

    cat > /home/\${VPS_USER}/\${PROJECT_NAME}/web/routers/db_router.py << 'EOL'
class DatabaseRouter:
    """
    A router to control all database operations on models for dual-database setup.
    """
    def db_for_read(self, model, **hints):
        """
        Reads go to the primary database by default.
        """
        if hasattr(model, 'use_secondary_db') and model.use_secondary_db:
            return 'secondary'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Writes go to the primary database by default.
        """
        if hasattr(model, 'use_secondary_db') and model.use_secondary_db:
            return 'secondary'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations are allowed if both objects are in the same database.
        """
        # Allow relations between models in the same database
        db1 = 'secondary' if hasattr(obj1.__class__, 'use_secondary_db') and obj1.__class__.use_secondary_db else 'default'
        db2 = 'secondary' if hasattr(obj2.__class__, 'use_secondary_db') and obj2.__class__.use_secondary_db else 'default'

        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which models get migrated to which database.
        """
        # Check if the model is meant for the secondary database
        model = hints.get('model')
        if model and hasattr(model, 'use_secondary_db') and model.use_secondary_db:
            return db == 'secondary'

        # By default, allow migrations on the primary database
        return db == 'default'
EOL
}

# Function to update Django settings for dual databases
update_django_settings() {
    log "Updating Django settings for dual database configuration..."

    # Backup original settings
    cp /home/\${VPS_USER}/\${PROJECT_NAME}/web/settings.py /home/\${VPS_USER}/\${PROJECT_NAME}/web/settings.py.bak

    # Update the settings file with the dual database configuration
    sed -i "/^DATABASES = /,/^}/ c\\
DATABASES = {\\
    'default': {\\
        'ENGINE': 'django.db.backends.postgresql',\\
        'NAME': '$PRIMARY_DB_NAME',\\
        'USER': '$PRIMARY_DB_USER',\\
        'PASSWORD': '$PRIMARY_DB_PASSWORD',\\
        'HOST': '$PRIMARY_VPS_IP',\\
        'PORT': '5432',\\
    },\\
    'secondary': {\\
        'ENGINE': 'django.db.backends.postgresql',\\
        'NAME': '$SECONDARY_DB_NAME',\\
        'USER': '$SECONDARY_DB_USER',\\
        'PASSWORD': '$SECONDARY_DB_PASSWORD',\\
        'HOST': '$SECONDARY_VPS_IP',\\
        'PORT': '5432',\\
    }\\
}\\
\\
# Add database router\\
DATABASE_ROUTERS = ['web.routers.db_router.DatabaseRouter']\\
" /home/\${VPS_USER}/\${PROJECT_NAME}/web/settings.py

    # Add base model for secondary database models
    cat >> /home/\${VPS_USER}/\${PROJECT_NAME}/web/models.py << 'EOL'

# Base model for secondary database
class SecondaryDatabaseModel(models.Model):
    """
    Abstract base model for all models that should use the secondary database.
    """
    use_secondary_db = True

    class Meta:
        abstract = True
EOL
}

# Function to setup Nginx
setup_nginx() {
    log "Setting up Nginx..."
    sudo rm -f /etc/nginx/sites-enabled/default

    sudo tee /etc/nginx/sites-available/\$PROJECT_NAME << EEOF
server {
    listen 80;
    server_name \${DOMAIN_NAME};

    location /static/ {
        alias /home/\${VPS_USER}/\${PROJECT_NAME}/staticfiles/;
    }

    location /media/ {
        alias /home/\${VPS_USER}/\${PROJECT_NAME}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:\${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EEOF

    sudo ln -sf /etc/nginx/sites-available/\$PROJECT_NAME /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
}

# Function to setup SSL
setup_ssl() {
    if [ ! -z "\$DOMAIN_NAME" ]; then
        log "Setting up SSL for \$DOMAIN_NAME..."
        sudo certbot --nginx -d \$DOMAIN_NAME --non-interactive --agree-tos --email admin@\${DOMAIN_NAME}
    fi
}

# Function to setup systemd service
setup_systemd_service() {
    log "Setting up systemd service..."
    sudo tee /etc/systemd/system/\$PROJECT_NAME.service << EEOF
[Unit]
Description=\$PROJECT_NAME website
After=network.target

[Service]
User=\${VPS_USER}
Group=\${VPS_USER}
WorkingDirectory=/home/\${VPS_USER}/\${PROJECT_NAME}
Environment="PATH=/home/\${VPS_USER}/\${PROJECT_NAME}/venv/bin"
ExecStart=/home/\${VPS_USER}/\${PROJECT_NAME}/venv/bin/uvicorn web.asgi:application --host 0.0.0.0 --port \${APP_PORT}
Restart=always

[Install]
WantedBy=multi-user.target
EEOF

    sudo systemctl daemon-reload
    sudo systemctl enable \$PROJECT_NAME
    sudo systemctl start \$PROJECT_NAME
}

# Function to create sample secondary model
create_sample_secondary_model() {
    log "Creating a sample model that uses the secondary database..."

    # Create a new file in the models directory
    cat >> /home/\${VPS_USER}/\${PROJECT_NAME}/web/models.py << 'EOL'

# Sample model that uses the secondary database
class SecondaryData(SecondaryDatabaseModel):
    """
    A sample model that will be stored in the secondary database.
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
EOL
}

# Main execution
log "Starting server setup for \$SERVER_TYPE server..."
install_system_dependencies
setup_firewall
setup_fail2ban

# Clone repository if it doesn't exist
if [ ! -d "/home/\${VPS_USER}/\${PROJECT_NAME}" ]; then
    log "Cloning repository..."
    git clone https://github.com/AlphaOneLabs/education-website.git /home/\${VPS_USER}/\${PROJECT_NAME}
fi

cd /home/\${VPS_USER}/\${PROJECT_NAME}
setup_postgresql
setup_python_env

# Create database router only on primary server
if [ "\$SERVER_TYPE" = "PRIMARY" ]; then
    create_database_router
    update_django_settings
    create_sample_secondary_model

    # Apply migrations to both databases
    log "Applying migrations to both databases..."
    source venv/bin/activate
    python manage.py makemigrations
    python manage.py migrate
    python manage.py migrate --database=secondary
    python manage.py collectstatic --noinput
else
    # Secondary server only needs to run the application
    log "Secondary server setup..."
    source venv/bin/activate
    python manage.py collectstatic --noinput
fi

setup_nginx
setup_ssl
setup_systemd_service

log "\$SERVER_TYPE server setup completed!"
EOF

    # Make the script executable
    chmod +x "$tmp_script"

    echo "$tmp_script"
}

# Function to setup a server
setup_server() {
    local server_type="$1"  # "PRIMARY" or "SECONDARY"
    local vps_ip="${server_type}_VPS_IP"
    local vps_user="${server_type}_VPS_USER"
    local vps_password="${server_type}_VPS_PASSWORD"

    # Use indirect variable references
    vps_ip="${!vps_ip}"
    vps_user="${!vps_user}"
    vps_password="${!vps_password}"

    log "Setting up $server_type server at $vps_ip..."

    # Create the setup script
    local script_path=$(create_server_setup_script "$server_type")

    # Copy the script to the server
    copy_file_to_server "$vps_ip" "$vps_user" "$vps_password" "$script_path" "/tmp/setup.sh"

    # Copy requirements.txt to the server
    copy_file_to_server "$vps_ip" "$vps_user" "$vps_password" "requirements.txt" "/tmp/requirements.txt"

    # Run the setup script on the server
    run_command_on_server "$vps_ip" "$vps_user" "$vps_password" "cd /tmp && bash setup.sh"

    # Clean up
    rm "$script_path"

    log "$server_type server setup completed!"
}

# Main function
main() {
    log "Starting dual-server deployment for $PROJECT_NAME"

    # Check if required variables are set or prompt for them
    check_required_vars

    # Ensure sshpass is installed
    ensure_sshpass

    # Setup primary server first
    setup_server "PRIMARY"

    # Setup secondary server
    setup_server "SECONDARY"

    log "Dual-server deployment completed successfully!"

    # Display connection information
    info "Primary server: $PRIMARY_VPS_IP (DB: $PRIMARY_DB_NAME)"
    if [ -n "$PRIMARY_DOMAIN_NAME" ]; then
        info "Primary domain: $PRIMARY_DOMAIN_NAME"
    fi

    info "Secondary server: $SECONDARY_VPS_IP (DB: $SECONDARY_DB_NAME)"
    if [ -n "$SECONDARY_DOMAIN_NAME" ]; then
        info "Secondary domain: $SECONDARY_DOMAIN_NAME"
    fi

    log "To use a model with the secondary database, extend SecondaryDatabaseModel"
    log "Example: class YourModel(SecondaryDatabaseModel): ..."
}

# Run the main function
main
