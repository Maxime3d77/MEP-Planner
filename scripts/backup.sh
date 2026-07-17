#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-./backup/mep-planner-$STAMP.tar.gz}"
mkdir -p "$(dirname "$OUT")"
CONTAINER="mep-planner-backend"
if ! sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Le conteneur $CONTAINER n'est pas démarré." >&2
  exit 1
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
sudo docker cp "$CONTAINER:/app/data" "$TMP/data"
tar -C "$TMP" -czf "$OUT" data
printf 'Sauvegarde créée : %s\n' "$OUT"
