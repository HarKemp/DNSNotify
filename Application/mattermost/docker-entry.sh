#!/bin/sh
set -e

chown -R 2000:2000 /mattermost-config 2>/dev/null || true

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

gosu mattermost /opt/mattermost/mattermost-setup.sh || true

wait "$MM_PID"
