#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
REPOSITORY="${GITHUB_REPOSITORY:-Maxime3d77/MEP-Planner}"
TARGET_VERSION="${1:-latest}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$ROOT_DIR/backups/pre-update-$STAMP"
TMP_DIR="$(mktemp -d)"
CURRENT_ARCHIVE="$BACKUP_DIR/application.tar.gz"

cleanup(){ rm -rf "$TMP_DIR"; }
trap cleanup EXIT
mkdir -p "$BACKUP_DIR" "$ROOT_DIR/data" "$ROOT_DIR/logs" "$ROOT_DIR/backups"

printf '1/7 Sauvegarde de la configuration persistante…\n'
for item in .env docker-compose.override.yml; do
  [[ -f "$item" ]] && cp -a "$item" "$BACKUP_DIR/"
done
[[ -d data ]] && cp -a data "$BACKUP_DIR/data"
[[ -d branding ]] && cp -a branding "$BACKUP_DIR/branding-defaults"
tar --exclude='./data' --exclude='./logs' --exclude='./backups' --exclude='./.env' -czf "$CURRENT_ARCHIVE" .

printf '2/7 Résolution de la version…\n'
if [[ "$TARGET_VERSION" == "latest" ]]; then
  TARGET_VERSION="$(curl -fsSL "https://api.github.com/repos/$REPOSITORY/releases/latest" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi
[[ -n "$TARGET_VERSION" ]] || { echo 'Impossible de déterminer la version cible.' >&2; exit 1; }
URL="https://github.com/$REPOSITORY/archive/refs/tags/$TARGET_VERSION.tar.gz"

printf '3/7 Téléchargement de %s…\n' "$TARGET_VERSION"
curl -fL --retry 3 "$URL" -o "$TMP_DIR/release.tar.gz"
tar -xzf "$TMP_DIR/release.tar.gz" -C "$TMP_DIR"
NEW_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -1)"
[[ -d "$NEW_ROOT" ]] || { echo 'Archive invalide.' >&2; exit 1; }

printf '4/7 Installation du code sans écraser les données…\n'
rsync -a --delete \
  --exclude='.env' --exclude='data/' --exclude='logs/' --exclude='backups/' \
  --exclude='docker-compose.override.yml' \
  "$NEW_ROOT/" "$ROOT_DIR/"
mkdir -p data logs backups

printf '5/7 Reconstruction des conteneurs…\n'
docker compose build --pull
docker compose up -d --remove-orphans

printf '6/7 Contrôle de santé…\n'
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8080/api/health}"
for _ in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    printf '7/7 Mise à jour réussie vers %s.\n' "$TARGET_VERSION"
    exit 0
  fi
  sleep 2
done

echo 'Le contrôle de santé a échoué. Restauration du code précédent…' >&2
tar -xzf "$CURRENT_ARCHIVE" -C "$ROOT_DIR"
[[ -f "$BACKUP_DIR/.env" ]] && cp -a "$BACKUP_DIR/.env" "$ROOT_DIR/.env"
docker compose build
docker compose up -d --remove-orphans
exit 1
