<p align="center">
  <img src="docs/images/mep-planner-banner.png" alt="MEP Planner Banner">
</p>

<h1 align="center">MEP Planner</h1>

<p align="center">
Enterprise Maintenance, Change Management & Deployment Planning Platform
</p>

---

# Enterprise Maintenance Planning Made Simple

**MEP Planner** is an open-source web application designed to simplify **maintenance planning**, **change management**, and **production deployments** for IT Operations, Infrastructure and DevOps teams.

Instead of managing maintenance windows with spreadsheets, emails and disconnected calendars, MEP Planner centralizes everything into a single, intuitive web interface.

Whether you manage a few servers or an entire enterprise infrastructure, MEP Planner helps you plan, communicate, monitor and document every maintenance operation.

---

# Why MEP Planner?

Managing infrastructure changes often involves multiple disconnected tools:

- Excel spreadsheets
- Outlook calendars
- Email exchanges
- Instant messaging
- Ticketing systems

MEP Planner replaces these fragmented workflows with a centralized platform built specifically for IT teams.

Benefits include:

- Centralized maintenance planning
- Professional communication
- Automatic reporting
- Better operational visibility
- Reduced human error
- Faster deployment preparation

---

# Core Features

## Maintenance Planning

- Day, Week and Month calendar views
- Maintenance scheduling
- Priority management
- Environment management
- Search and filtering
- Maintenance history

---

## Change Management

- Production deployments
- Infrastructure changes
- Application releases
- Rollback planning
- Change tracking

---

## Authentication

- Local accounts
- LDAP
- OpenLDAP
- Microsoft Active Directory
- OpenID Connect (OIDC)
- Role-Based Access Control (RBAC)

---

## Notifications

- SMTP email notifications
- Matrix integration
- Daily reminders
- Scheduled notifications
- PDF attachments

---

## Redmine Integration

- Automatic synchronization
- Maintenance creation from Redmine issues
- Status synchronization
- Environment support
- Tags support

---

## PDF Reports

Generate professional PDF reports including:

- Maintenance summary
- Schedule
- Environment
- Impact
- Rollback procedure
- Contacts
- Company branding

---

## Health Center

The integrated Health Center provides real-time monitoring of the application.

It includes:

- Global Health Score
- API status
- Database status
- Scheduler status
- SMTP connectivity
- LDAP connectivity
- Redmine connectivity
- Matrix connectivity
- CPU usage
- Memory usage
- Disk usage
- Database size
- Backup status
- System alerts

---

## Backup Center

Protect your application directly from the web interface.

Features include:

- One-click backup
- Backup download
- Backup history
- Import backups
- Full restore
- Partial restore
- Automatic backup before updates

No command-line access required.

---

## Automatic Updates

MEP Planner includes a built-in update system.

Before installing a new version it automatically:

- Creates a backup
- Downloads the update
- Applies migrations
- Restarts services
- Performs health checks
- Rolls back automatically if necessary

---

# Installation

Clone the repository:

```bash
git clone https://github.com/Maxime3d77/MEP-Planner.git

cd MEP-Planner
```

Start the application:

```bash
docker compose up -d
```

Open your browser:

```
http://YOUR_SERVER_IP:8080
```

The setup wizard will guide you through the initial configuration.

---

# First Configuration

Recommended setup order:

1. Administrator account
2. Company branding
3. SMTP server
4. LDAP or OIDC
5. Redmine integration
6. Matrix integration
7. Automatic updates
8. Backup configuration

---

# Directory Structure

```
data/
├── backups/
├── branding/
├── database/
├── logs/
├── uploads/
└── certificates/
```

---

# Configuration

Everything can be configured directly from the web interface.

Available settings include:

- General
- Branding
- SMTP
- LDAP
- OIDC
- Redmine
- Matrix
- Notifications
- Security
- Health
- Backup
- Updates

No manual configuration files are required for everyday administration.

---

# Technologies

## Backend

- FastAPI
- Python
- SQLAlchemy
- SQLite

## Frontend

- HTML5
- Bootstrap
- JavaScript

## Infrastructure

- Docker
- Docker Compose
- Nginx

---

# Roadmap

## Completed

- Maintenance Planning
- Calendar Views
- Multi-language
- SMTP Notifications
- PDF Reports
- Redmine Integration
- Matrix Integration
- Automatic Updates
- Health Center
- Backup Center

## Planned

- Microsoft Teams Integration
- Slack Integration
- Webhooks
- PostgreSQL Support
- REST API Documentation
- Audit Logs
- Advanced Dashboard
- High Availability

---

# Contributing

Contributions are welcome.

You can help by:

- Reporting bugs
- Suggesting new features
- Improving documentation
- Submitting pull requests

Please open an Issue before starting major changes.

---

# License

MEP Planner is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

You are free to use, modify and distribute this software under the terms of the GPL-3.0 license.


---

# Support

If you encounter an issue, please open a GitHub Issue.

Feature requests and suggestions are always welcome.

---

# Acknowledgements

MEP Planner has been designed with a single goal:

**Helping IT Operations teams manage maintenance windows more efficiently through a modern, simple and reliable platform.**

---

<p align="center">

**Made with ❤️ for IT Operations, Infrastructure & DevOps Teams**

</p>
