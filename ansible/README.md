# Education Website Deployment

This Ansible configuration deploys the Education Website to remote servers with a simplified, consolidated structure.

## File Structure

```
ansible/
├── site.yml               # Main deployment playbook (consolidates all roles)
├── inventory.yml          # Server inventory (replaces inventory/ directory)
├── deploy.sh             # Simple deployment script (replaces scripts/ directory)
├── ansible.cfg           # Ansible configuration
├── .vault_pass           # Vault password file
├── group_vars/
│   ├── all.yml           # Global variables (consolidates group_vars/all/)
│   ├── vault.yml         # Encrypted variables
│   └── development.yml   # Environment-specific variables
└── templates/
    ├── django_env.j2     # Django environment file template
    ├── nginx_site.j2     # Nginx site configuration template
    └── systemd_service.j2 # Systemd service template
```

## Quick Start

1. **Configure your server details** in `inventory.yml`
2. **Set your vault password** in `.vault_pass`
3. **Deploy to development**:
   ```bash
   ./deploy.sh -e development
   ```

## Deployment Commands

```bash
# Deploy to development
./deploy.sh -e development

# Deploy to production
./deploy.sh -e production

# Dry run (check mode)
./deploy.sh -e development -c

# Verbose output
./deploy.sh -e development --verbose

# Custom vault password file
./deploy.sh -e development -v /path/to/vault_pass
```

## Configuration

### Server Configuration
Edit `inventory.yml` to configure your servers:
- Update `ansible_host` with your server IP
- Update `ansible_user` with your SSH user
- Update `ansible_ssh_private_key_file` with your SSH key path

### Environment Variables
- **Global variables**: `group_vars/all.yml`
- **Environment-specific**: `group_vars/development.yml` or `group_vars/production.yml`
- **Encrypted secrets**: `group_vars/vault.yml`

### What Gets Deployed

The playbook sets up:
- ✅ Security (UFW firewall, fail2ban)
- ✅ PostgreSQL database
- ✅ Python virtual environment
- ✅ Django application (migrations, static files)
- ✅ Nginx web server
- ✅ Systemd service for the application
- ✅ SSL certificates (optional)

## Maintenance

### Adding New Environments
1. Create `group_vars/{environment}.yml`
2. Add environment section to `inventory.yml`
3. Deploy with `./deploy.sh -e {environment}`

### Updating Variables
Edit the appropriate files in `group_vars/` and redeploy.

### Encrypted Variables
Use `ansible-vault edit group_vars/vault.yml` to modify secrets.

## Simplified Structure Benefits

- **Single playbook** instead of multiple roles
- **One template directory** instead of scattered templates
- **Simple inventory file** instead of complex directory structure
- **Single deployment script** with all options
- **Consolidated variables** in logical groups

This structure is much easier to understand, maintain, and debug compared to the previous multi-role setup.
