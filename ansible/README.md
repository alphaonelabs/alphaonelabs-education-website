# Ansible Deployment for Education Website

This directory contains a simplified Ansible deployment setup for the Django Education Website with Django Channels support.

## Files Overview

- `hosts.yml` - Server configuration and variables
- `secrets.yml` - Sensitive configuration (should be encrypted)
- `deploy.yml` - Main deployment playbook
- `deploy.sh` - Convenient deployment script
- `README.md` - This documentation

## Quick Start

### 1. Prerequisites

Install Ansible:
```bash
pip install ansible
```

### 2. Configure Secrets

Edit the secrets file with your actual values:
```bash
./deploy.sh edit
```

Or manually edit `secrets.yml` and then encrypt it:
```bash
# Edit secrets.yml with your values
./deploy.sh encrypt
```

### 3. Deploy

Run the full deployment:
```bash
./deploy.sh deploy
```

## Configuration

### Server Settings (hosts.yml)

- **Server IP**: 45.76.4.171
- **User**: webapp (created during deployment)
- **Project Directory**: /home/webapp/education-website
- **App Port**: 8000

### Required Secrets (secrets.yml)

Update these values in `secrets.yml`:

```yaml
# Django Configuration
django_secret_key: "your-actual-secret-key"

# Database Configuration
database_password: "your-secure-db-password"

# Redis Configuration
redis_password: "your-secure-redis-password"

# Email Configuration
email_from: "your-email@domain.com"
sendgrid_api_key: "your-sendgrid-api-key"
sendgrid_password: "your-sendgrid-password"

# Stripe Configuration (if using payments)
stripe_publishable_key: "your-stripe-publishable-key"
stripe_secret_key: "your-stripe-secret-key"
stripe_webhook_secret: "your-stripe-webhook-secret"

# Other configurations...
```

## Deployment Commands

### Full Deployment
```bash
./deploy.sh deploy
```

### Quick Update (code only)
```bash
./deploy.sh update
```

### Check Status
```bash
./deploy.sh status
```

### View Logs
```bash
./deploy.sh logs
```

### Restart Services
```bash
./deploy.sh restart
```

### Manage Secrets
```bash
./deploy.sh encrypt    # Encrypt secrets.yml
./deploy.sh decrypt    # Decrypt secrets.yml
./deploy.sh edit       # Edit encrypted secrets.yml
```

## What the Deployment Does

1. **System Setup**
   - Updates package cache
   - Installs Python 3.11, PostgreSQL, Redis, Nginx, Supervisor
   - Creates webapp user
   - Configures firewall (UFW)

2. **Database Setup**
   - Configures PostgreSQL
   - Creates database and user
   - Sets up Redis for Django Channels

3. **Application Setup**
   - Clones the GitHub repository
   - Creates Python virtual environment
   - Installs dependencies
   - Creates .env file with production settings
   - Runs migrations and collects static files

4. **Web Server Setup**
   - Configures Nginx as reverse proxy
   - Sets up static file serving
   - Configures WebSocket support for Django Channels

5. **Process Management**
   - Configures Supervisor for process management
   - Sets up Django app with Gunicorn + Uvicorn
   - Sets up Django Channels worker

## Architecture

```
Internet → Nginx (Port 80) → Gunicorn/Uvicorn (Port 8000) → Django App
                          → WebSocket → Django Channels
                          → Static Files (Direct serving)
                          → Media Files (Direct serving)
```

## Services

After deployment, these services will be running:

- **Nginx**: Web server and reverse proxy
- **PostgreSQL**: Database server
- **Redis**: Cache and message broker for Channels
- **Supervisor**: Process manager
  - `education-website-django`: Main Django application
  - `education-website-channels`: Django Channels worker

## Troubleshooting

### Check Service Status
```bash
./deploy.sh status
```

### View Application Logs
```bash
./deploy.sh logs
```

### SSH to Server
```bash
ssh root@45.76.4.171
```

### Manual Service Management
```bash
# On the server
sudo supervisorctl status
sudo supervisorctl restart education-website-django
sudo supervisorctl restart education-website-channels
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### Check Application Health
```bash
curl http://45.76.4.171
```

## Security Notes

1. **Always encrypt secrets.yml** before committing to version control
2. **Change default passwords** in secrets.yml
3. **Use strong passwords** for database and Redis
4. **Consider setting up SSL/HTTPS** for production use
5. **Regularly update system packages** and dependencies

## Environment Variables

The deployment creates a `.env` file with these variables:

- `DEBUG=False`
- `ENVIRONMENT=production`
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `DJANGO_ALLOWED_HOSTS` - Allowed hosts for Django
- `REDIS_URL` - Redis connection string
- Plus all other secrets from secrets.yml

## File Locations on Server

- **Application**: `/home/webapp/education-website/`
- **Virtual Environment**: `/home/webapp/education-website/venv/`
- **Static Files**: `/home/webapp/education-website/staticfiles/`
- **Media Files**: `/home/webapp/education-website/media/`
- **Logs**: `/var/log/supervisor/education-website-*.log`
- **Nginx Config**: `/etc/nginx/sites-available/education-website`
- **Supervisor Config**: `/etc/supervisor/conf.d/education-website.conf`

## Support

If you encounter issues:

1. Check the logs: `./deploy.sh logs`
2. Verify service status: `./deploy.sh status`
3. Try restarting services: `./deploy.sh restart`
4. For code updates: `./deploy.sh update`

For major issues, you may need to run the full deployment again: `./deploy.sh deploy`