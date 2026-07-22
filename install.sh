#!/usr/bin/env bash
set -e
mkdir -p data logs backups

echo "=== Installation MEP Planner ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker n'est pas installé."
  echo "Installe Docker Engine et le plugin Docker Compose, puis relance ce script."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Le plugin Docker Compose n'est pas disponible."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env créé à partir de .env.example"
fi

docker compose up -d --build

echo
echo "MEP Planner est lancé."
echo "URL : http://localhost:8080"
echo
echo "Pour configurer Redmine, édite le fichier .env puis exécute :"
echo "docker compose up -d --build"
