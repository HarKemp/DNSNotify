#!/usr/bin/env bash

set -e
stack=dnsnotify

echo "Removing stack $stack ..."
docker stack rm "$stack"

echo -n "Waiting for removal to finish ..."
while docker stack ls | grep -q "$stack"; do
  echo -n "."
  sleep 2
done
echo
echo "Stack removed."