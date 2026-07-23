# Installation

## Requirements

- Linux host with Docker Engine and Docker Compose v2
- Git, curl and unzip
- Access to a Redmine instance
- A reverse proxy with TLS for production use

## Deploy

```bash
git clone https://github.com/Maxime3d77/MEP-Planner.git
cd MEP-Planner
cp .env.example .env
nano .env
chmod +x install.sh scripts/*.sh
./install.sh
```

Verify the API with `curl -fsS http://127.0.0.1:8080/api/health`.
