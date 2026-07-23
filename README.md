<p align="center">
  <img src="docs/images/mep-planner-banner.png" alt="MEP Planner banner" width="100%">
</p>

<h1 align="center">MEP Planner</h1>
<p align="center"><strong>Plan smarter. Deploy with confidence.</strong></p>
<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-5.1.4-4ade80">
  <img alt="License" src="https://img.shields.io/badge/license-GPL--3.0-blue">
  <img alt="Docker" src="https://img.shields.io/badge/deployment-Docker-2496ED">
  <img alt="Languages" src="https://img.shields.io/badge/UI-FR%20%7C%20EN-8b5cf6">
</p>

MEP Planner is a self-hosted operations dashboard for planning, tracking and communicating production deployments stored in Redmine. It provides day, week and month views, operational notifications, PDF summaries, access control, backups and application health monitoring.

## Highlights

- Redmine synchronization with configurable custom fields
- Day, week and month deployment calendars
- Clear handling of urgent releases and releases without a scheduled time
- SMTP email, PDF and calendar invitation workflows
- Matrix notifications
- Local, LDAP/Active Directory and OpenID Connect authentication
- Role-based access for users and administrators
- French and English interfaces
- Health Center with service, storage and persistence checks
- Backup Center with create, import, download, restore and delete operations
- Safe update script with backup, health check and automatic rollback

## Quick installation

```bash
git clone https://github.com/Maxime3d77/MEP-Planner.git
cd MEP-Planner
cp .env.example .env
nano .env
chmod +x install.sh scripts/*.sh
./install.sh
```

Open `http://SERVER_IP:8080` after the containers start.

## Updating

```bash
./scripts/update.sh
```

The updater preserves `.env`, `data/`, `branding/`, `logs/`, `backups/` and `docker-compose.override.yml`. It creates a safety backup before deployment and automatically rolls back when the health check fails.

## Documentation

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [SMTP](docs/smtp.md)
- [LDAP / Active Directory](docs/ldap.md)
- [OpenID Connect](docs/oidc.md)
- [Redmine](docs/redmine.md)
- [Backup Center](docs/backup.md)
- [Health Center](docs/health.md)
- [Updates](docs/update.md)
- [API](docs/api.md)

## Data persistence

Persistent application data is stored outside the container image. Before any upgrade, keep a copy of `.env`, `data/`, `branding/`, `logs/` and `backups/`.

## Security

Place MEP Planner behind a TLS reverse proxy, use a dedicated Redmine API account, restrict administrative access and regularly verify that backups can be restored.

## License

MEP Planner is licensed under the [GNU General Public License v3.0](LICENSE).

## Support

Report reproducible issues through the GitHub issue tracker and include the application version, browser, deployment method and relevant sanitized logs.
