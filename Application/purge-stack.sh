#!/usr/bin/env bash

set -e
stack=dnsnotify
prefix="dnsnotify_"
extra="grafana-data clickhouse-data nats-data mattermost-data mattermost-config-exchange postgres-data"

echo "Removing stack $stack ..."
docker stack rm "$stack"
sleep 5

vols=$(docker volume ls --format '{{.Name}}' | \
       awk -v p="$prefix" -v ex="$extra" '
            BEGIN{split(ex,a); for (i in a) exact[a[i]]=1}
            $0 ~ "^"p {print; next}
            exact[$0] {print}
       ')

if [ -n "$vols" ]; then
  echo "Deleting volumes:"
  echo "$vols"
  echo "$vols" | xargs -r docker volume rm
else
  echo "No matching volumes to delete."
fi

echo "Purge complete."