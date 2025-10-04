# Production Deployment Guide

This guide explains how to use the automated GitHub Actions workflow for deploying to production.

## Overview

The production deployment workflow automates the entire deployment process, including:

1. **Release Management**: Automatically creates and tags releases using semantic versioning
2. **Code Deployment**: SSH to server, pull latest code from Git
3. **Dependency Management**: Install/update dependencies using Poetry
4. **Database Migrations**: Run Django migrations
5. **Static Files**: Collect static files for serving
6. **Service Restart**: Restart web server (Gunicorn/Uvicorn) and Nginx

## Prerequisites

### 1. GitHub Secrets Configuration

Configure the following secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Example |
|------------|-------------|---------|
| `PRODUCTION_SERVER_IP` | IP address of your production server | `203.0.113.10` |
| `PRODUCTION_SERVER_USER` | SSH username (typically `django` or `root`) | `django` |
| `PRODUCTION_SERVER_PASSWORD` | SSH password for the user | `your-secure-password` |

### 2. Server Requirements

Your production server must have:
- Git installed
- Python 3.10+ with virtualenv
- Poetry 2.0.1 (will be installed/upgraded by the workflow)
- Project cloned at `/home/django/education-website` (or update the path in the workflow)
- Systemd service named `education-website`
- Nginx installed and configured
- SSH access enabled

### 3. Server User Permissions

The deployment user must have:
- Read/write access to the project directory
- Permission to run `sudo systemctl restart education-website`
- Permission to run `sudo systemctl restart nginx`

You can configure this by adding to `/etc/sudoers.d/django`:
```bash
django ALL=(ALL) NOPASSWD: /bin/systemctl restart education-website
django ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx
django ALL=(ALL) NOPASSWD: /bin/systemctl status education-website
django ALL=(ALL) NOPASSWD: /bin/systemctl status nginx
```

## How to Deploy

### Step 1: Navigate to Actions Tab

1. Go to your GitHub repository
2. Click on the **Actions** tab at the top

### Step 2: Select Deployment Workflow

1. In the left sidebar, find and click **Deploy to Production**
2. Click the **Run workflow** button on the right

### Step 3: Choose Version Bump

Select the appropriate version bump type:

- **patch** (default): Bug fixes and minor changes
  - Example: `v1.0.0` → `v1.0.1`
  
- **minor**: New features that don't break compatibility
  - Example: `v1.0.0` → `v1.1.0`
  
- **major**: Breaking changes or major releases
  - Example: `v1.0.0` → `v2.0.0`

### Step 4: Run the Workflow

1. Click the green **Run workflow** button
2. Monitor the progress in real-time

## Workflow Steps

The deployment workflow performs the following steps:

### 1. Create Release Tag
- Fetches the latest Git tag
- Calculates the new version based on your selection
- Creates and pushes a new Git tag

### 2. Create GitHub Release
- Creates a GitHub release with the new version
- Includes release notes and changelog

### 3. Deploy to Server
The workflow SSHs to your production server and executes:

```bash
cd /home/django/education-website
git fetch --all --prune
git reset --hard origin/main
source venv/bin/activate
pip install --upgrade pip wheel
pip install --upgrade poetry==2.0.1
poetry config virtualenvs.create false --local || true
poetry install --only main --no-interaction --no-ansi
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart education-website
sudo systemctl restart nginx
```

### 4. Verify Deployment
- Checks the status of the `education-website` service
- Checks the status of the `nginx` service

## Customization

### Changing the Project Path

If your project is not at `/home/django/education-website`, update line 119 in the workflow file:

```yaml
cd /home/django/education-website
```

### Changing Poetry Version

To use a different Poetry version, update line 130:

```yaml
pip install --upgrade poetry==2.0.1
```

### Adding Additional Deployment Steps

You can add custom steps before or after the restart commands. For example, to clear cache:

```yaml
# Clear application cache
python manage.py clear_cache

# Restart the web server (systemd service)
sudo systemctl restart education-website
```

## Troubleshooting

### SSH Connection Fails

**Error**: `Permission denied (publickey,password)`

**Solution**: 
- Verify `PRODUCTION_SERVER_PASSWORD` secret is correct
- Ensure SSH password authentication is enabled on the server
- Check `/etc/ssh/sshd_config` has `PasswordAuthentication yes`

### Git Pull Fails

**Error**: `error: Your local changes to the following files would be overwritten`

**Solution**: 
The workflow uses `git reset --hard origin/main` which should override local changes. If this persists, SSH to the server and manually resolve conflicts.

### Migration Fails

**Error**: Migration errors during `python manage.py migrate`

**Solution**:
1. SSH to the server manually
2. Check database connectivity
3. Review migration files
4. Run migrations manually to identify the issue

### Permission Denied on Restart

**Error**: `sudo: no tty present and no askpass program specified`

**Solution**: 
Configure passwordless sudo for the deployment user (see Server User Permissions section above)

### Service Not Found

**Error**: `Failed to restart education-website.service: Unit education-website.service not found`

**Solution**:
- Verify the systemd service is installed: `systemctl status education-website`
- Check the service file exists: `/etc/systemd/system/education-website.service`
- Run `sudo systemctl daemon-reload` if you just created the service

## Security Best Practices

1. **Use SSH Keys Instead of Passwords** (Recommended)
   - Generate SSH key pair
   - Add public key to server's `~/.ssh/authorized_keys`
   - Store private key as GitHub secret
   - Modify workflow to use key-based authentication

2. **Limit User Permissions**
   - Use a dedicated deployment user (not root)
   - Only grant necessary sudo permissions
   - Use sudoers.d configuration as shown above

3. **Rotate Credentials Regularly**
   - Change SSH passwords periodically
   - Update GitHub secrets when credentials change

4. **Monitor Deployments**
   - Review deployment logs after each run
   - Set up notifications for failed deployments
   - Monitor server logs: `/var/log/syslog`, application logs

## Manual Deployment

If you need to deploy manually without the GitHub Action:

```bash
# SSH to server
ssh django@your-server-ip

# Navigate to project
cd /home/django/education-website

# Pull latest code
git pull origin main

# Activate virtualenv
source venv/bin/activate

# Install dependencies
poetry install --only main --no-interaction --no-ansi

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart education-website
sudo systemctl restart nginx
```

## Related Documentation

- [Ansible Deployment](../ansible/README.md) - For full server provisioning
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)

## Support

If you encounter issues:
1. Check the GitHub Actions logs for detailed error messages
2. SSH to the server and check service logs
3. Review this troubleshooting guide
4. Contact the development team
