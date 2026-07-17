#!/usr/bin/env bash
set -Eeuo pipefail

echo "======================================"
echo " Installation complète MEP Planner"
echo "======================================"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Erreur : sudo est nécessaire pour installer Docker."
    echo "Relance en root ou installe sudo."
    exit 1
  fi
  SUDO="sudo"
fi

if [ ! -f /etc/os-release ]; then
  echo "Distribution Linux non reconnue."
  exit 1
fi

. /etc/os-release
DISTRO="${ID:-}"
CODENAME="${VERSION_CODENAME:-}"
DOCKER_DISTRO="$DISTRO"

case "$DISTRO" in
  ubuntu|debian)
    ;;
  linuxmint)
    # Linux Mint standard repose sur Ubuntu.
    DOCKER_DISTRO="ubuntu"
    CODENAME="${UBUNTU_CODENAME:-noble}"
    echo "Linux Mint détecté : utilisation du dépôt Ubuntu ${CODENAME}."
    ;;
  *)
    if [ "${ID_LIKE:-}" = "ubuntu" ] || [[ "${ID_LIKE:-}" == *"ubuntu"* ]]; then
      DOCKER_DISTRO="ubuntu"
      CODENAME="${UBUNTU_CODENAME:-${CODENAME}}"
      echo "Distribution dérivée d'Ubuntu détectée : utilisation du dépôt Ubuntu ${CODENAME}."
    else
      echo "Distribution non prise en charge automatiquement : ${PRETTY_NAME:-$DISTRO}"
      exit 1
    fi
    ;;
esac

install_docker() {
  echo
  echo "[1/5] Installation des prérequis..."
  $SUDO apt-get update
  $SUDO apt-get install -y ca-certificates curl

  echo
  echo "[2/5] Configuration du dépôt officiel Docker..."
  $SUDO install -m 0755 -d /etc/apt/keyrings
  $SUDO curl -fsSL "https://download.docker.com/linux/${DOCKER_DISTRO}/gpg" \
    -o /etc/apt/keyrings/docker.asc
  $SUDO chmod a+r /etc/apt/keyrings/docker.asc

  ARCH="$(dpkg --print-architecture)"

  if [ -z "$CODENAME" ]; then
    echo "Impossible de déterminer le nom de version de la distribution."
    exit 1
  fi

  echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${DOCKER_DISTRO} ${CODENAME} stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null

  echo
  echo "[3/5] Installation de Docker Engine et Docker Compose..."
  $SUDO apt-get update
  $SUDO apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

  echo
  echo "[4/5] Activation du service Docker..."
  $SUDO systemctl enable --now docker

  if [ -n "${SUDO}" ]; then
    $SUDO usermod -aG docker "$USER" || true
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  install_docker
else
  echo "Docker est déjà installé."
  if ! $SUDO systemctl is-active --quiet docker; then
    $SUDO systemctl enable --now docker
  fi
fi

if ! $SUDO docker compose version >/dev/null 2>&1; then
  echo "Docker Compose est absent. Installation du plugin..."
  $SUDO apt-get update
  $SUDO apt-get install -y docker-compose-plugin
fi

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Fichier .env créé."
fi

echo
echo "[5/5] Construction et démarrage de MEP Planner..."
$SUDO docker compose up -d --build

echo
echo "======================================"
echo " Installation terminée"
echo "======================================"
echo "Application : http://localhost:8080"
echo
echo "Configuration Redmine :"
echo "  nano .env"
echo
echo "Après modification :"
echo "  sudo docker compose up -d --build"
echo
echo "Remarque : le groupe Docker a été ajouté à ton utilisateur."
echo "Une reconnexion à la session peut être nécessaire pour utiliser docker sans sudo."
