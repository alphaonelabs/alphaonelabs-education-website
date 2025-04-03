#!/bin/bash

# Simple script to reformat a single Vultr server
# Usage: ./vultr_reformat_single.sh

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ssh-keygen -R "$PRIMARY_VPS_IP" &> /dev/null

# Load variables from .env.production
ENV_FILE="$PROJECT_ROOT/.env.production"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

echo "Reformatting server $PRIMARY_VPS_IP"
# Initiate reformatting via API
response=$(curl -s -X POST -H "Authorization: Bearer $VULTR_API_KEY" -H "Content-Type: application/json" \
     -d "{\"hostname\":\"$PRIMARY_HOSTNAME\"}" "https://api.vultr.com/v2/instances/$PRIMARY_SERVER_ID/reinstall")
echo "Server reformatting initiated for $PRIMARY_VPS_IP. Check Vultr dashboard for status."

# Extract default password from the response
echo "Processing Vultr API response..."
default_password=$(echo "$response" | grep -o '"default_password":"[^"]*"' | cut -d'"' -f4)

if [ -n "$default_password" ]; then
    echo "New password received from Vultr API"

    # Update the PRIMARY_VPS_PASSWORD in .env.production
    if [ -f "$ENV_FILE" ]; then
        # Create a backup of the original file
        cp "$ENV_FILE" "${ENV_FILE}.bak"

        # Update the password in the environment file
        sed -i "s/PRIMARY_VPS_PASSWORD=\"[^\"]*\"/PRIMARY_VPS_PASSWORD=\"$default_password\"/" "$ENV_FILE"
        echo "Updated PRIMARY_VPS_PASSWORD in $ENV_FILE"
    else
        echo "Error: Could not find .env.production file"
    fi
else
    echo "Warning: Could not extract default_password from Vultr API response"
    echo "Raw API response: $response"
fi

# Loop until server is back online using ping
echo "Waiting for server to come back online..."
while ! ping -c 1 -W 2 "$PRIMARY_VPS_IP" > /dev/null 2>&1; do
    echo -n "."
    sleep 5
done

echo -e "\nServer is back online!"
echo "The updated PRIMARY_VPS_PASSWORD is ready to be used for deployment"
