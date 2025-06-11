#!/bin/bash

# Test script for Ansible deployment system
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[TEST]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Test 1: Check prerequisites
log "Testing prerequisites..."

if ! command -v ansible &> /dev/null; then
    error "Ansible not installed. Install with: pip install ansible"
    exit 1
fi

if ! command -v python3.11 &> /dev/null; then
    warn "Python 3.11 not found. You may need to install it."
fi

log "✅ Prerequisites check passed"

# Test 2: Local setup script
log "Testing local setup script..."
if [ -x "ansible/scripts/local_setup.sh" ]; then
    log "✅ Local setup script is executable"
else
    error "Local setup script not executable"
    exit 1
fi

# Test 3: Ansible configuration
log "Testing Ansible configuration..."
cd ansible

if ansible-playbook deploy.yml --syntax-check &> /dev/null; then
    log "✅ deploy.yml syntax is valid"
else
    error "deploy.yml has syntax errors"
    exit 1
fi

if ansible-playbook update.yml --syntax-check &> /dev/null; then
    log "✅ update.yml syntax is valid"
else
    error "update.yml has syntax errors"
    exit 1
fi

# Test 4: Check required files
log "Checking required files..."

required_files=(
    "group_vars/all/main.yml"
    "inventory/hosts.yml"
    "scripts/deploy.sh"
    "scripts/local_setup.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log "✅ $file exists"
    else
        error "$file is missing"
        exit 1
    fi
done

# Test 5: Check vault file
if [ -f "group_vars/all/vault.yml" ]; then
    log "✅ Vault file exists"
    if ansible-vault view group_vars/all/vault.yml --ask-vault-pass &> /dev/null; then
        log "✅ Vault file is properly encrypted"
    else
        warn "Could not decrypt vault file (password may be wrong)"
    fi
else
    warn "Vault file doesn't exist. Create it with: ansible-vault create group_vars/all/vault.yml"
fi

# Test 6: Inventory validation
log "Testing inventory..."
if ansible-inventory --list &> /dev/null; then
    log "✅ Inventory is valid"
else
    error "Inventory has errors"
    exit 1
fi

log "🎉 All tests passed! Your Ansible deployment system is ready."
log ""
log "Next steps:"
log "1. Create vault file if missing: ansible-vault create group_vars/all/vault.yml"
log "2. Update inventory/hosts.yml with your server details"
log "3. Test connection: ansible all -m ping --ask-vault-pass"
log "4. Dry run: ./scripts/deploy.sh -c -e development"
log "5. Deploy: ./scripts/deploy.sh -e development" 