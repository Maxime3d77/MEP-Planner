# MEP Planner v2.9

MEP Planner is a Docker-based dashboard designed to manage software release operations (MEP - *Mise En Production*) from Redmine.

It provides release planning, calendar visualization, email communications, PDF generation, tracking, and company branding in a modern web interface.

---

# Features

- Background Redmine synchronization
- Filter issues using a custom field (`Tag=MEP`)
- Day / Week / Month calendar views
- Dedicated area for releases without scheduled time
- Priority management (Low, Normal, High, Urgent, Immediate)
- SQLite communication history
- Automatic email deduplication
- Manual resend (global or custom recipients)
- Professional PDF generation
- MEP Planner branding with optional company logo
- Company customization through the Settings page
- Persistent Docker storage
- Light and Dark themes
- Complete French / English localization
- Independent language selection for emails and PDF reports
- GitHub version checking
- Secure administrator settings

---

# Architecture

- Static JavaScript frontend served by **nginx**
- **FastAPI** backend
- **Redmine REST API**
- **SQLite** database stored in `/app/data`
- **nginx** reverse proxy exposed on port **8080**

---

# Requirements

- Docker Engine
- Docker Compose Plugin
- Network access to Redmine
- SMTP server
- Redmine API key with issue read permissions

---

# Installation

```bash
cp .env_template .env
nano .env
sudo docker compose up -d --build
```

Open your browser:

```
http://YOUR_SERVER:8080
```

Verify installation:

```bash
curl -s http://localhost:8080/api/health | python3 -m json.tool
sudo docker compose logs -f backend
```

---

# Redmine Configuration

## Standard fields used

MEP Planner relies on the following standard Redmine fields:

- Start date
- Due date
- Priority
- Status
- Author
- Assignee
- Estimated time

## Custom fields

| Field | Purpose |
|--------|----------|
| Tag | Select release tickets (`MEP`) |
| Environment | PROD / PREPROD / TEST / DEV |
| Start Time | HH:MM |
| End Time | HH:MM |

## Creating time fields

```
Administration
→ Custom fields
→ Issues
→ New custom field
```

Create two **Text** fields:

```
Start Time
End Time
```

Recommended validation:

```
^([01][0-9]|2[0-3]):[0-5][0-9]$
```

Enable them in the required projects.

If **Start Time** is empty, MEP Planner displays:

```
Time to be defined
```

No artificial time is generated anymore.

If Start Time and Estimated Time are available but End Time is missing, End Time is automatically calculated.

---

# Themes & Languages

The sidebar provides:

- Light / Dark theme
- French / English interface

The selected theme is stored locally in the browser.

The interface language controls:

- menus
- tables
- filters
- dashboard
- popups
- notifications

Communication language (emails & PDF) is configured independently under:

```
Settings
→ Email & PDF Language
```

Default values:

```env
APP_LANGUAGE=fr
COMMUNICATION_LANGUAGE=fr
```

Supported values:

```
fr
en
```

---

# SMTP Configuration

Example:

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=25
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=MEP Planner <mep-planner@example.com>
SMTP_USE_TLS=false
SMTP_USE_SSL=false
SMTP_RECIPIENTS=ops@example.com;manager@example.com
```

Automatic emails are deduplicated using:

```
Issue
+
Redmine version
+
Communication type
+
Recipients
```

Manual resend is always available.

---

# Company Branding

MEP Planner always displays its own identity.

Optionally, a company branding can be added:

- Company logo
- Company name
- Subtitle
- Accent color
- Contact email
- Footer

The uploaded logo is stored inside the Docker persistent volume and automatically used in:

- Web interface
- Emails
- PDF reports

---

# Backup

Before upgrading:

```bash
./scripts/backup.sh
```

Custom output:

```bash
./scripts/backup.sh /path/backup.tar.gz
```

Restore:

```bash
./scripts/restore.sh /path/backup.tar.gz
```

---

# Upgrade

```bash
cd ../mep-planner-v2.8

./scripts/backup.sh

sudo docker compose down

cd ../mep-planner-v2.9

cp ../mep-planner-v2.8/.env .env

sudo docker compose up -d --build
```

---

# Useful Commands

```bash
sudo docker compose ps

sudo docker compose logs -f backend

sudo docker compose logs --tail=100 nginx frontend

sudo docker compose restart backend

sudo docker compose down

sudo docker compose up -d --build
```

---

# GitHub

Official repository

https://github.com/Maxime3d77/MEP-Planner

Initialize repository:

```bash
git init

git branch -M main

git add .

git commit -m "Initial release"
```

Connect GitHub:

```bash
git remote add origin https://github.com/Maxime3d77/MEP-Planner.git

git push -u origin main
```

Create a Release:

```bash
git tag -a v2.9.1 -m "MEP Planner v2.9.1"

git push origin main

git push origin v2.9.1
```

---

# Administrator Settings

The Settings page is protected by an administrator password.

```env
ADMIN_PASSWORD=your_secure_password
ADMIN_SESSION_HOURS=8
```

The password is never stored in the browser.

Only a temporary session token is kept until the browser tab is closed.

---

# GitHub Version Check

```env
GITHUB_REPOSITORY_URL=https://github.com/Maxime3d77/MEP-Planner

GITHUB_API_REPOSITORY=Maxime3d77/MEP-Planner

GITHUB_CHECK_TIMEOUT_SECONDS=8
```

MEP Planner compares the installed version with the latest GitHub Release.

If no Release exists, the latest Git tag is used.

The update checker is **informational only**.

No automatic download or installation is performed.

---

# Security

- Never commit your `.env`
- Revoke exposed API keys
- Use HTTPS for remote deployments
- Restrict access to the Settings page
- Backup the Docker volume before every upgrade

---

# Troubleshooting

## No Redmine issues found

```bash
sudo docker compose logs --tail=200 backend

curl -s http://localhost:8080/api/health | python3 -m json.tool
```

Verify:

- Tag field name
- Tag value (`MEP`)
- API key
- Redmine permissions

## Time fields not detected

Verify the custom field names:

```env
REDMINE_START_TIME_FIELD=Start Time

REDMINE_END_TIME_FIELD=End Time
```

## SMTP errors

```bash
sudo docker compose logs --tail=200 backend | grep -i smtp
```

SMTP failures are logged in the **Communications** page without interrupting Redmine synchronization.

---

# License

This project is distributed as open source.

Contributions, feature requests and bug reports are welcome via GitHub.

⭐ If you enjoy this project, consider giving it a star!