#!/usr/bin/env bash
set -euo pipefail
ARCHIVE="${1:-}"
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || { echo "Usage: $0 backup.tar.gz" >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$ARCHIVE" -C "$TMP"
sudo docker compose stop backend
sudo docker compose run --rm --no-deps -v "$TMP/data:/restore:ro" backend sh -c 'rm -rf /app/data/* && cp -a /restore/. /app/data/'
sudo docker compose up -d backend
printf 'Restauration terminée.\n'
