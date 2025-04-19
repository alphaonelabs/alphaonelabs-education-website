#!/bin/bash

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load variables from .env.db file
ENV_FILE="$PROJECT_ROOT/.env.db"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

ssh-keygen -R "$PRIMARY_VPS_DB_HOST_IP" &> /dev/null

echo "Reformatting server $PRIMARY_VPS_DB_HOST_IP"
# Initiate reformatting via API
response=$(curl -s -X POST -H "Authorization: Bearer $VULTR_API_KEY" -H "Content-Type: application/json" \
     -d "{\"hostname\":\"$PRIMARY_HOSTNAME\"}" "https://api.vultr.com/v2/instances/$PRIMARY_SERVER_ID/reinstall")
echo "Server reformatting initiated for $PRIMARY_VPS_DB_HOST_IP. Check Vultr dashboard for status."

# Extract default password from the response
echo "Processing Vultr API response..."
default_password=$(echo "$response" | grep -o '"default_password":"[^"]*"' | cut -d'"' -f4)

if [ -n "$default_password" ]; then
    echo "New password received from Vultr API"
    echo "Password: $default_password"

    # Update the PRIMARY_VPS_DB_HOST_PASSWORD in .env.db
    if [ -f "$ENV_FILE" ]; then
        # Create a backup of the original file
        cp "$ENV_FILE" "${ENV_FILE}.bak"

        # More robust approach to update the password
        # First grep to see if the variable exists
        if grep -q "^PRIMARY_VPS_DB_HOST_PASSWORD=" "$ENV_FILE"; then
            # Update existing variable
            echo "Updating existing PRIMARY_VPS_DB_HOST_PASSWORD in $ENV_FILE"
            # Use a different delimiter for sed to avoid issues with password special characters
            sed -i "s|^PRIMARY_VPS_DB_HOST_PASSWORD=.*|PRIMARY_VPS_DB_HOST_PASSWORD=\"$default_password\"|" "$ENV_FILE"

            # Verify the update with a more robust check
            echo "Verifying password update..."
            updated_password=$(grep "^PRIMARY_VPS_DB_HOST_PASSWORD=" "$ENV_FILE" | cut -d'"' -f2)
            if [ "$updated_password" = "$default_password" ]; then
                echo "✅ Password updated successfully in $ENV_FILE"
            else
                echo "⚠️ Password update verification failed. Please check $ENV_FILE manually."
                echo "Expected: $default_password"
                echo "Found: $updated_password"
                # Restore backup if verification fails
                mv "${ENV_FILE}.bak" "$ENV_FILE"
                exit 1
            fi
        else
            # Add new variable if it doesn't exist
            echo "Adding PRIMARY_VPS_DB_HOST_PASSWORD to $ENV_FILE"
            echo "PRIMARY_VPS_DB_HOST_PASSWORD=\"$default_password\"" >> "$ENV_FILE"
        fi
    else
        echo "Error: Could not find .env.db file"
        exit 1
    fi
else
    echo "Warning: Could not extract default_password from Vultr API response"
    echo "Raw API response: $response"
    exit 1
fi

# Loop until server is back online, checking SSH port
echo "Waiting for server to come back online..."
MAX_ATTEMPTS=120  # 10 minutes with 5-second intervals
ATTEMPT=0
SERVER_ONLINE=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Use nc (netcat) to check if SSH port is open
    if command -v nc &> /dev/null; then
        if nc -z -w5 "$PRIMARY_VPS_DB_HOST_IP" 22 &> /dev/null; then
            echo -e "\nSSH port is open. Server is back online!"
            SERVER_ONLINE=true
            break
        fi
    # Fallback to timeout and bash's /dev/tcp if netcat is not available
    elif timeout 5 bash -c "echo > /dev/tcp/$PRIMARY_VPS_DB_HOST_IP/22" &> /dev/null; then
        echo -e "\nSSH port is open. Server is back online!"
        SERVER_ONLINE=true
        break
    fi

    echo -n "."
    ATTEMPT=$((ATTEMPT+1))
    sleep 5
done

if [ "$SERVER_ONLINE" = false ]; then
    echo -e "\nWarning: Could not detect the server coming back online within the timeout period."
    echo "Please check server status manually."
    exit 1
fi

echo "Successfully detected the database server is online."
echo "The updated PRIMARY_VPS_DB_HOST_PASSWORD is ready to be used for deployment."
echo "New password: $default_password"
