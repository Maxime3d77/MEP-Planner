$ErrorActionPreference = "Stop"

Write-Host "=== Installation MEP Planner ==="

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop n'est pas installé ou n'est pas dans le PATH."
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env créé à partir de .env.example"
}

docker compose up -d --build

Write-Host ""
Write-Host "MEP Planner est lancé : http://localhost:8080"
Write-Host "Pour configurer Redmine, modifie .env puis relance docker compose up -d --build"
