#!/bin/bash

# Simple deployment script for Education Website
# Usage: ./deploy.sh [environment] [options]

set -e

# Default values
ENVIRONMENT="development"
VAULT_PASS_FILE=".vault_pass"
CHECK_MODE=false
VERBOSE=false
ASK_PASS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--vault-password-file)
            VAULT_PASS_FILE="$2"
            shift 2
            ;;
        -c|--check)
            CHECK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -k|--ask-pass)
            ASK_PASS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -e, --environment ENV         Target environment (default: development)"
            echo "  -v, --vault-password-file     Vault password file (default: .vault_pass)"
            echo "  -c, --check                   Run in check mode (dry run)"
            echo "  --verbose                     Verbose output"
            echo "  -k, --ask-pass                Ask for SSH password"
            echo "  -h, --help                    Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build ansible-playbook command
CMD="ansible-playbook"
CMD="$CMD -i inventory.yml"
CMD="$CMD --limit $ENVIRONMENT"

if [[ -f "$VAULT_PASS_FILE" ]]; then
    CMD="$CMD --vault-password-file $VAULT_PASS_FILE"
fi

if [[ "$CHECK_MODE" == "true" ]]; then
    CMD="$CMD --check"
    echo "Running in CHECK MODE (dry run)"
fi

if [[ "$VERBOSE" == "true" ]]; then
    CMD="$CMD -v"
fi

if [[ "$ASK_PASS" == "true" ]]; then
    CMD="$CMD --ask-pass"
fi

CMD="$CMD site.yml"

# Display command info
echo "========================================="
echo "Deploying Education Website"
echo "Environment: $ENVIRONMENT"
echo "Check Mode: $CHECK_MODE"
echo "========================================="

# Execute the deployment
echo "Executing: $CMD"
$CMD

echo "========================================="
if [[ "$CHECK_MODE" == "true" ]]; then
    echo "Dry run completed successfully!"
else
    echo "Deployment completed successfully!"
    echo "Your application should be accessible at:"
    echo "http://$(ansible-inventory -i inventory.yml --host test-server | grep ansible_host | cut -d'"' -f4)"
fi
echo "========================================="
