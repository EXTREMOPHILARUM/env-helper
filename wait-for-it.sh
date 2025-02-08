#!/bin/sh
# wait-for-it.sh

HOST="$1"
PORT="$2"

# Try with hostname first
while ! nc -z "$HOST" "$PORT" 2>/dev/null; do
  # If hostname fails, try to resolve using Docker DNS
  if getent hosts "$HOST" >/dev/null 2>&1; then
    IP=$(getent hosts "$HOST" | awk '{ print $1 }')
    if nc -z "$IP" "$PORT" 2>/dev/null; then
      break
    fi
  fi
  echo "Waiting for $HOST:$PORT..."
  sleep 1
done

echo "$HOST:$PORT is up - executing command"
shift 2
exec "$@"
