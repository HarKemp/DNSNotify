#!/bin/sh

CONFIG_OUTPUT_DIR="/mattermost-config" # Define this early for the log file path
SETUP_LOG_FILE="$CONFIG_OUTPUT_DIR/mattermost_setup.log"
# Create the directory if it doesn't exist, then redirect all output
mkdir -p "$CONFIG_OUTPUT_DIR"
exec > "$SETUP_LOG_FILE" 2>&1

set -x

sleep 30

# Use environment variables if set, otherwise use defaults
ADMIN_USERNAME="${SETUP_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${SETUP_ADMIN_PASSWORD:-admin123}"
ADMIN_EMAIL="${SETUP_ADMIN_EMAIL:-admin@admin.com}"

TEAM_NAME="dnsnotify"
TEAM_DISPLAY_NAME="DNS Notifications"

CHANNEL_NAME="dnsnotifications"
CHANNEL_DISPLAY_NAME="Notifications Channel"

BOT_USERNAME="dnsnotifier"
BOT_DISPLAY_NAME="DNS Notifier Bob"
BOT_EMAIL="bot@test.com"
BOT_DESCRIPTION="Bot for sending DNS notifications"

#CONFIG_OUTPUT_DIR="/mattermost-config"
BOT_TOKEN_FILE_PATH="$CONFIG_OUTPUT_DIR/bot_token.txt"

WEBHOOK_DISPLAY_NAME="DNSNotify Webhook"
WEBHOOK_DESCRIPTION="Incoming webhook for DNS notifications"

MMCTL_CMD="/mattermost/bin/mmctl --local"

# 1. Admin User
$MMCTL_CMD user create --system_admin --email "${ADMIN_EMAIL}" --username "${ADMIN_USERNAME}" --password "${ADMIN_PASSWORD}"

# 1.2. Bot user
$MMCTL_CMD user create --system_admin --email "${BOT_EMAIL}" --username "${BOT_USERNAME}" --password "${ADMIN_PASSWORD}"

#sleep 1

# 2. Create team, add user as team admin
$MMCTL_CMD team create --name "${TEAM_NAME}" --display_name "${TEAM_DISPLAY_NAME}" --email "${ADMIN_EMAIL}"
#$MMCTL_CMD team users add "${TEAM_NAME}" "${ADMIN_USERNAME}"

#sleep 1

# TODO - add IF check for existing channels and webhooks

# 3. Channel
#$MMCTL_CMD channel create --team "${TEAM_NAME}" --name "${CHANNEL_NAME}" --display_name "${CHANNEL_DISPLAY_NAME}"
# 3. Channel
TARGET_CHANNEL_ID=""
echo "Checking for existing channel '${CHANNEL_NAME}' in team '${TEAM_NAME}'..."

CHANNELS_LIST_RAW_OUTPUT=$($MMCTL_CMD channel list "${TEAM_NAME}")
MMCTL_CHANNEL_LIST_EXIT_CODE=$?

CHANNEL_EXISTS_IN_LIST=false
if [ $MMCTL_CHANNEL_LIST_EXIT_CODE -eq 0 ]; then
    if echo "$CHANNELS_LIST_RAW_OUTPUT" | grep -qw "$CHANNEL_NAME"; then
        CHANNEL_EXISTS_IN_LIST=true
        echo "Channel '${CHANNEL_NAME}' found in list for team '${TEAM_NAME}'. Attempting to get its ID via 'channel search'..."
        SEARCH_CHANNEL_OUTPUT=$($MMCTL_CMD channel search "${CHANNEL_NAME}" --team "${TEAM_NAME}")
        # Updated awk script to parse "Key :Value, Key :Value, Channel ID :ID" format
        # It specifically looks for "Channel ID :" and extracts the value.
        # It also checks if "Channel Name :" or "Display Name :" matches the desired channel.
        TARGET_CHANNEL_ID=$(echo "$SEARCH_CHANNEL_OUTPUT" | awk -F', *' -v chan_to_find="$CHANNEL_NAME" '
            {
                id=""; name_match=0;
                for (i=1; i<=NF; i++) {
                    if ($i ~ /^[Cc]hannel [Ii][Dd] *:/) {
                        sub(/^[Cc]hannel [Ii][Dd] *:[[:space:]]*/, "", $i);
                        id = $i;
                    }
                    if ($i ~ /^[Cc]hannel [Nn]ame *:/ || $i ~ /^[Dd]isplay [Nn]ame *:/) {
                        temp_name = $i;
                        sub(/^[^:]+:[[:space:]]*/, "", temp_name);
                        if (temp_name == chan_to_find) {
                            name_match=1;
                        }
                    }
                }
                if (id != "" && name_match) {
                    print id;
                    exit;
                }
            }
        ')

        if [ -n "$TARGET_CHANNEL_ID" ]; then
            echo "Found existing channel '${CHANNEL_NAME}' with ID: $TARGET_CHANNEL_ID via 'channel search'."
        else
            echo "Warning: Channel '${CHANNEL_NAME}' was in list, but ID could not be reliably extracted from 'channel search' output or name did not match."
            echo "Debug: 'channel search ${CHANNEL_NAME} --team ${TEAM_NAME}' output was:"
            echo "$SEARCH_CHANNEL_OUTPUT"
            echo "Proceeding to attempt creation as a fallback."
            CHANNEL_EXISTS_IN_LIST=false
        fi
    else
        echo "Channel '${CHANNEL_NAME}' not found in list for team '${TEAM_NAME}'."
    fi
else
    echo "Error: Failed to list channels for team '${TEAM_NAME}'. Exit code: $MMCTL_CHANNEL_LIST_EXIT_CODE"
    echo "List output: $CHANNELS_LIST_RAW_OUTPUT"
fi

if [ "$CHANNEL_EXISTS_IN_LIST" = false ] && [ -z "$TARGET_CHANNEL_ID" ]; then
  echo "Attempting to create channel '${CHANNEL_NAME}' in team '${TEAM_NAME}'..."
  CREATE_CHANNEL_OUTPUT=$($MMCTL_CMD channel create --team "${TEAM_NAME}" --name "${CHANNEL_NAME}" --display_name "${CHANNEL_DISPLAY_NAME}" 2>&1)
  MMCTL_CHANNEL_CREATE_EXIT_CODE=$?

  if [ $MMCTL_CHANNEL_CREATE_EXIT_CODE -eq 0 ]; then
    echo "Channel created, now searching for its ID..."
    # After creating the channel, directly search for it to get the ID
    SEARCH_CHANNEL_OUTPUT=$($MMCTL_CMD channel search "${CHANNEL_NAME}" --team "${TEAM_NAME}" 2>&1)
    TARGET_CHANNEL_ID=$(echo "$SEARCH_CHANNEL_OUTPUT" | grep -i "Channel ID :" | awk -F':' '{print $NF}' | tr -d ' \r\n')

    if [ -n "$TARGET_CHANNEL_ID" ]; then
      echo "Found channel ID: $TARGET_CHANNEL_ID"
    else
      echo "Error: Could not get channel ID after creation. Trying alternative method..."
      CHANNEL_LIST_OUTPUT=$($MMCTL_CMD channel list "${TEAM_NAME}" --json 2>&1)
      TARGET_CHANNEL_ID=$(echo "$CHANNEL_LIST_OUTPUT" | grep -A2 "\"name\": \"${CHANNEL_NAME}\"" | grep -i "\"id\":" | head -1 | awk -F'"' '{print $4}')
      if [ -n "$TARGET_CHANNEL_ID" ]; then
        echo "Found channel ID via JSON: $TARGET_CHANNEL_ID"
      else
        echo "Error: All methods to get channel ID failed. Debug JSON output:"
        echo "$CHANNEL_LIST_OUTPUT" | head -20
      fi
    fi
  else
    echo "Error: Channel creation failed. Exit Code: $MMCTL_CHANNEL_CREATE_EXIT_CODE"
    echo "Create Output: [$CREATE_CHANNEL_OUTPUT]"
  fi
fi

HOOK_ID=""
WEBHOOK_URL_FILE_PATH="$CONFIG_OUTPUT_DIR/webhook_url.txt"

BOT_USER_ID=""
BOT_USER_SEARCH_OUTPUT=$($MMCTL_CMD user search "${BOT_USERNAME}")
if [ $? -eq 0 ]; then
    BOT_USER_ID=$(echo "$BOT_USER_SEARCH_OUTPUT" | grep -i '^id:' | awk '{print $2}' | tr -d '\r')
fi

# Webhook logic: Simplified - relies on file first, then create.
# TARGET_CHANNEL_ID and BOT_USER_ID are needed for webhook *creation* if the file check fails.
if [ -z "$TARGET_CHANNEL_ID" ] || [ -z "$BOT_USER_ID" ]; then
    echo "Error: Could not determine Target Channel ID (found: '$TARGET_CHANNEL_ID') or Bot User ID (found: '$BOT_USER_ID'). Cannot proceed with webhook creation if needed."
    # If we only rely on the file, we might not need to exit here if the file exists and is valid.
    # However, if the file is NOT valid, we cannot create a new one without these IDs.
fi

echo "Expected Webhook Display Name: $WEBHOOK_DISPLAY_NAME"
HOOK_ID="" # Ensure HOOK_ID is reset before checks

if [ -f "$WEBHOOK_URL_FILE_PATH" ]; then
    STORED_HOOK_ID=$(cat "$WEBHOOK_URL_FILE_PATH" | tr -d '\r\n')
    if [ -n "$STORED_HOOK_ID" ]; then
        echo "Found stored webhook ID: $STORED_HOOK_ID. Verifying its existence..."
        # Just check if 'webhook show' succeeds. If so, assume it's the one.
        if $MMCTL_CMD webhook show "$STORED_HOOK_ID" > /dev/null 2>&1; then
            echo "Stored webhook ID $STORED_HOOK_ID exists. Using this webhook."
            HOOK_ID="$STORED_HOOK_ID"
        else
            echo "Stored webhook ID $STORED_HOOK_ID does not exist or 'webhook show' failed. Will attempt to create a new one."
        fi
    else
        echo "Webhook ID file $WEBHOOK_URL_FILE_PATH is empty. Will attempt to create a new one."
    fi
else
    echo "Webhook ID file $WEBHOOK_URL_FILE_PATH does not exist. Will attempt to create a new one."
fi

# If HOOK_ID is still empty (file didn't exist, was empty, or stored ID was invalid), try to create.
if [ -z "$HOOK_ID" ]; then
    if [ -z "$TARGET_CHANNEL_ID" ] || [ -z "$BOT_USER_ID" ]; then
        echo "Error: Cannot create a new webhook because Target Channel ID or Bot User ID is missing."
        # Try to search for the channel again as a last resort
        if [ -z "$TARGET_CHANNEL_ID" ] && [ -n "$TEAM_NAME" ] && [ -n "$CHANNEL_NAME" ]; then
            echo "Trying to search for channel ID one more time..."
            SEARCH_CHANNEL_OUTPUT=$($MMCTL_CMD channel search "${CHANNEL_NAME}" --team "${TEAM_NAME}" 2>&1)
            TARGET_CHANNEL_ID=$(echo "$SEARCH_CHANNEL_OUTPUT" | grep -i "Channel ID :" | awk -F':' '{print $NF}' | tr -d ' \r\n')

            if [ -n "$TARGET_CHANNEL_ID" ]; then
                echo "Finally found channel ID: $TARGET_CHANNEL_ID"
            else
                echo "Still failed to find channel ID. Cannot create webhook."
                exit 1
            fi
        else
            echo "Cannot proceed with webhook creation."
            exit 1
        fi
    fi

    echo "Attempting to create a new webhook..."
    WEBHOOK_CREATED_RAW_OUTPUT=$($MMCTL_CMD webhook create-incoming \
      --channel "${TEAM_NAME}:${CHANNEL_NAME}" \
      --user "${BOT_USERNAME}" \
      --display-name "${WEBHOOK_DISPLAY_NAME}" \
      --description "${WEBHOOK_DESCRIPTION}" 2>&1)
    MMCTL_WEBHOOK_CREATE_EXIT_CODE=$?

    echo "mmctl webhook create command exit code: $MMCTL_WEBHOOK_CREATE_EXIT_CODE"

    if [ $MMCTL_WEBHOOK_CREATE_EXIT_CODE -eq 0 ]; then
        HOOK_ID_FROM_CREATE=$(echo "$WEBHOOK_CREATED_RAW_OUTPUT" | grep -i '^id:' | awk '{print $2}' | tr -d '\r')
        if [ -n "$HOOK_ID_FROM_CREATE" ]; then
            HOOK_ID="$HOOK_ID_FROM_CREATE"
            echo "New webhook created with ID: $HOOK_ID"
        else
            echo "Error: Webhook creation seemed to succeed but could not parse HOOK_ID from output: [$WEBHOOK_CREATED_RAW_OUTPUT]"
        fi
    else
        echo "Error: Webhook creation failed. Exit code: $MMCTL_WEBHOOK_CREATE_EXIT_CODE. Output: [$WEBHOOK_CREATED_RAW_OUTPUT]"
    fi
fi

# Save the determined HOOK_ID to file if it's valid and different from current content
if [ -n "$HOOK_ID" ]; then
    CURRENT_FILE_CONTENT=""
    if [ -f "$WEBHOOK_URL_FILE_PATH" ]; then
        CURRENT_FILE_CONTENT=$(cat "$WEBHOOK_URL_FILE_PATH" | tr -d '\r\n')
    fi

    if [ "$CURRENT_FILE_CONTENT" != "$HOOK_ID" ]; then
        echo "$HOOK_ID" > "$WEBHOOK_URL_FILE_PATH"
        echo "Webhook ID ($HOOK_ID) saved/updated in $WEBHOOK_URL_FILE_PATH"
    else
        echo "Webhook ID ($HOOK_ID) in $WEBHOOK_URL_FILE_PATH is already up-to-date."
    fi
else
    echo "Error: Final HOOK_ID is empty. Cannot save to file $WEBHOOK_URL_FILE_PATH."
fi

echo "Final determined HOOK_ID for use: $HOOK_ID"


#mkdir -p "$CONFIG_OUTPUT_DIR"
#echo "$HOOK_ID" > "$WEBHOOK_URL_FILE_PATH"
#echo "Webhook URL: $WEBHOOK_URL"
#echo "Webhook URL saved to $WEBHOOK_URL_FILE_PATH"