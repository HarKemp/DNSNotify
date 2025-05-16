#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

set -a
source .env
set +a

docker compose -f prod.yml build \
  ml-model mattermost notification-service test-client

docker stack deploy -c prod.yml dnsnotify