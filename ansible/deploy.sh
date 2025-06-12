#!/bin/bash

# Simple Ansible Deployment Script
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    error "Ansible is not installed. Install with: pip install ansible"
fi

case "${1:-help}" in
    "deploy")
        log "Starting deployment..."
        ansible-playbook -i hosts.yml deploy.yml --ask-vault-pass -v
        log "🚀 Deployment complete! App available at: http://45.76.4.171"
        ;;

    "update")
        log "Quick update (pull latest code and restart)..."
        ansible all -i hosts.yml -m git -a "repo=https://github.com/AlphaOneLabs/education-website.git dest=/home/webapp/education-website force=yes" --ask-vault-pass --become-user=webapp
        ansible all -i hosts.yml -m shell -a "cd /home/webapp/education-website && ./venv/bin/pip install -r requirements.txt" --ask-vault-pass --become-user=webapp
        ansible all -i hosts.yml -m shell -a "cd /home/webapp/education-website && ./venv/bin/python manage.py migrate" --ask-vault-pass --become-user=webapp
        ansible all -i hosts.yml -m shell -a "cd /home/webapp/education-website && ./venv/bin/python manage.py collectstatic --noinput" --ask-vault-pass --become-user=webapp
        ansible all -i hosts.yml -m shell -a "supervisorctl restart education-website-django education-website-channels" --ask-vault-pass --become
        log "✅ Update complete!"
        ;;

    "status")
        log "Checking application status..."
        ansible all -i hosts.yml -m shell -a "supervisorctl status" --ask-vault-pass --become
        ;;

    "logs")
        log "Showing application logs..."
        ansible all -i hosts.yml -m shell -a "tail -n 50 /var/log/supervisor/education-website-django.log" --ask-vault-pass --become
        ;;

    "restart")
        log "Restarting services..."
        ansible all -i hosts.yml -m shell -a "supervisorctl restart education-website-django education-website-channels" --ask-vault-pass --become
        log "✅ Services restarted!"
        ;;

    "encrypt")
        log "Encrypting secrets file..."
        ansible-vault encrypt secrets.yml
        log "✅ Secrets encrypted!"
        ;;

    "decrypt")
        log "Decrypting secrets file..."
        ansible-vault decrypt secrets.yml
        log "✅ Secrets decrypted!"
        ;;

    "edit")
        log "Editing secrets file..."
        ansible-vault edit secrets.yml
        ;;

    *)
        cat << EOF
Simple Ansible Deployment for Education Website

Usage: $0 [command]

Commands:
  deploy    - Full deployment (first time)
  update    - Quick update (code only)
  status    - Check app status
  logs      - Show app logs
  restart   - Restart services

Secrets:
  encrypt   - Encrypt secrets.yml
  decrypt   - Decrypt secrets.yml
  edit      - Edit secrets.yml

Quick Start:
1. Edit secrets.yml with your passwords
2. ./deploy.sh encrypt
3. ./deploy.sh deploy

Files:
- hosts.yml    (server config)
- secrets.yml  (passwords - encrypt this!)
- deploy.yml   (main deployment)
EOF
        ;;
esac