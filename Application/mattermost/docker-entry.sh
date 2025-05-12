#!/bin/sh
set -e

# Ensure volumes are writeable
chown -R 2000:2000 /mattermost-config 2>/dev/null || true

#-------------------------------------------------------------
# 1) Launch Mattermost (as uid 2000) in the background
#-------------------------------------------------------------
gosu mattermost /mattermost/bin/mattermost &
MM_PID=$!

echo "Waiting for Mattermost to accept connections…"
# Try for up to 60 seconds
for i in $(seq 1 60); do
    if curl -s http://localhost:8065/api/v4/system/ping >/dev/null 2>&1; then
        echo "Mattermost is up."
        break
    fi
    sleep 1
done

#-------------------------------------------------------------
# 2) Run your bootstrap script exactly once
#-------------------------------------------------------------
gosu mattermost /opt/mattermost/mattermost-setup.sh || true

#-------------------------------------------------------------
# 3) Bring the server process back to foreground
#-------------------------------------------------------------
wait "$MM_PID"
