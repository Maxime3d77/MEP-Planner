<p align="center">
  <img src="docs/images/mep-planner-banner.png" alt="MEP Planner — Open Source Change & Release Planning Platform" width="100%">
</p>

# MEP Planner

MEP Planner is a self-hosted change and release planning application for operational teams. It centralizes Redmine releases, schedules, notifications, enterprise authentication and reporting in one responsive interface.

## Highlights in v5.1.1

- Modern reports dashboard with responsive, dependency-free SVG and CSS charts.
- Configurable reporting periods: 7, 30, 90 or 365 days.
- Completed and scheduled release trends, status, priority, environment and notification delivery visualizations.
- LDAP / LDAPS group mapping with Just-In-Time provisioning.
- OIDC / SSO, Redmine, SMTP and Matrix integrations.
- Improved English and French administration translations.
- New lightweight README banner.

## Reports

The Reports page provides:

- total releases, unscheduled releases and urgent releases;
- planning quality percentage;
- notification success and failure counters;
- release trend over the selected period;
- breakdowns by status, priority and environment;
- notification delivery distribution.

Charts are rendered locally with SVG and CSS. No external analytics or chart CDN is required.

## LDAP example

```env
LDAP_ENABLED=true
LDAP_DIRECTORY_TYPE=openldap
LDAP_URL=ldaps://ldap.example.com
LDAP_PORT=636
LDAP_BIND_DN=cn=ldap-reader,ou=Services,dc=example,dc=com
LDAP_BIND_PASSWORD=change_me
LDAP_VERIFY_TLS=true
LDAP_JIT_PROVISIONING=true

LDAP_USER_BASE_DN=dc=example,dc=com
LDAP_USER_LOGIN_ATTRIBUTE=uid
LDAP_USER_FILTER=(&(objectClass=person)(uid={username}))
LDAP_USER_FIRSTNAME_ATTRIBUTE=givenName
LDAP_USER_LASTNAME_ATTRIBUTE=sn
LDAP_USER_EMAIL_ATTRIBUTE=mail

LDAP_GROUP_BASE_DN=ou=Groups,dc=example,dc=com
LDAP_GROUP_OBJECT_CLASS=posixGroup
LDAP_GROUP_NAME_ATTRIBUTE=cn
LDAP_GROUP_MEMBER_ATTRIBUTE=memberUid
LDAP_GROUP_REFERENCE_ATTRIBUTE=uid
LDAP_GROUP_FILTER=({member_attribute}={reference})
LDAP_GROUP_MAP=operations:user;mep-admins:admin
```

## Upgrade

```bash
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d
```

Preserve your existing `.env` and persistent Docker volumes during the upgrade.

# MEP Planner v3.0

MEP Planner est un tableau de bord Docker pour piloter les mises en production enregistrées dans Redmine. Il centralise le planning, les priorités, les communications email, leur traçabilité et les fiches PDF.

## Fonctionnalités

- synchronisation Redmine en arrière-plan ;
- sélection des tickets par champ personnalisé `Tag=MEP` ;
- vues Jour, Semaine et Mois ;
- affichage séparé des MEP sans horaire ;
- hiérarchie Bas/Normal, Haut, Urgent et Immédiat ;
- historique SQLite des emails et anti-doublon ;
- renvoi manuel global ou ciblé ;
- pièces jointes PDF ;
- branding MEP Planner + logo entreprise facultatif ;
- menu Paramètres pour personnaliser l'entreprise ;
- sauvegarde persistante dans un volume Docker ;
- thème clair adouci avec champs, recherche et listes déroulantes cohérents ;
- traduction complète de l’interface française et anglaise ;
- langue des emails et PDF configurable séparément dans Paramètres.

## Architecture

- frontend statique JavaScript servi par nginx ;
- API FastAPI ;
- Redmine via son API REST ;
- SQLite dans `/app/data` ;
- nginx en reverse proxy sur le port `8080`.

## Prérequis

- Docker Engine ;
- plugin Docker Compose ;
- accès réseau à Redmine et au serveur SMTP ;
- clé API Redmine autorisée à consulter les tickets.

## Installation

```bash
cp .env_template .env
nano .env
sudo docker compose up -d --build
```

Ouvrir ensuite :

```text
http://ADRESSE_DU_SERVEUR:8080
```

Vérification :

```bash
curl -s http://localhost:8080/api/health | python3 -m json.tool
sudo docker compose logs -f backend
```

## Configuration Redmine

### Champs utilisés

MEP Planner utilise les champs standards Redmine :

- date de début ;
- date d'échéance ;
- priorité ;
- statut ;
- auteur ;
- assigné ;
- temps estimé.

Il utilise également ces champs personnalisés :

| Champ | Usage |
|---|---|
| `Tag` | sélectionner les tickets contenant `MEP` |
| `Environnement` | PROD, PREPROD, RECETTE, DEV... |
| `Heure de début` | horaire au format `HH:MM` |
| `Heure de fin` | horaire au format `HH:MM` |

### Création des champs horaires

Dans Redmine :

```text
Administration → Champs personnalisés → Demandes → Nouveau champ
```

Créer deux champs de type **Texte** :

```text
Heure de début
Heure de fin
```

Expression régulière recommandée :

```text
^([01][0-9]|2[0-3]):[0-5][0-9]$
```

Activer ensuite ces champs dans les projets concernés.

Sans heure de début, MEP Planner affiche **Heure à préciser**. Il n'invente plus 09:00. Si une heure de début et un temps estimé sont fournis mais pas l'heure de fin, celle-ci est calculée automatiquement.


## Thèmes et langues

Le bouton situé en bas de la barre latérale permet de basculer entre le thème sombre et le thème clair. Le choix du thème est mémorisé dans le navigateur.

La langue de l’interface peut être choisie entre français et anglais. Tous les titres, tableaux, filtres, statistiques, calendriers, fenêtres et messages sont issus du dictionnaire de traduction centralisé.

La langue des communications est indépendante et se règle dans **Paramètres → Langue des emails et PDF**. Valeurs initiales dans `.env` :

```env
APP_LANGUAGE=fr
COMMUNICATION_LANGUAGE=fr
```

Valeurs autorisées : `fr` et `en`. Les réglages enregistrés depuis l’interface sont prioritaires sur les valeurs initiales du `.env`.

## Configuration SMTP

Exemple pour un relais SMTP sans authentification sur le port 25 :

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.example.fr
SMTP_PORT=25
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=MEP Planner <mep-planner@example.fr>
SMTP_USE_TLS=false
SMTP_USE_SSL=false
SMTP_RECIPIENTS=exploitation@example.fr;responsable@example.fr
```

Les communications automatiques sont dédupliquées avec la combinaison :

```text
ticket + version Redmine + type de communication + destinataires
```

Un renvoi manuel reste toujours possible et est enregistré séparément.

## Branding entreprise

Le logo MEP Planner reste permanent. Le menu **Paramètres** permet d'ajouter une identité entreprise complémentaire :

- nom ;
- sous-titre ;
- couleur ;
- email de contact ;
- pied de page ;
- logo PNG jusqu'à 3 Mo.

Le logo entreprise est stocké dans le volume `mep-state`, puis utilisé dans l'interface, les emails et les PDF. Il survit aux reconstructions Docker.

Les variables `COMPANY_*` du `.env` servent de valeurs initiales. Les réglages enregistrés depuis l'interface sont prioritaires.

## Sauvegarde

La base SQLite, l'état Redmine et le logo entreprise sont dans le volume Docker. Avant une mise à jour :

```bash
./scripts/backup.sh
```

Pour choisir le fichier :

```bash
./scripts/backup.sh /chemin/sauvegarde-mep.tar.gz
```

Restauration :

```bash
./scripts/restore.sh /chemin/sauvegarde-mep.tar.gz
```

## Mise à jour depuis une ancienne version

```bash
cd ../mep-planner-v2.5
./scripts/backup.sh  # si le script existe dans cette version
sudo docker compose down

cd ../mep-planner-v2.9
cp ../mep-planner-v2.5/.env .env
sudo docker compose up -d --build
```

Pour récupérer un ancien volume portant le même nom de projet, conservez le même nom de dossier ou restaurez la sauvegarde avec le script fourni.

## Commandes utiles

```bash
sudo docker compose ps
sudo docker compose logs -f backend
sudo docker compose logs --tail=100 nginx frontend
sudo docker compose restart backend
sudo docker compose down
sudo docker compose up -d --build
```

## Intégration GitHub

Le fichier `.env` est exclu par `.gitignore`. Vérifiez toujours qu'aucune clé API ou mot de passe n'est ajouté au dépôt.

Création du dépôt local :

```bash
git init
git branch -M main
git add .
git commit -m "Initial release of MEP Planner v2.9"
```

Association à GitHub :

```bash
git remote add origin git@github.com:VOTRE-COMPTE/mep-planner.git
git push -u origin main
```

Création d'une release :

```bash
git tag -a v2.9.1 -m "MEP Planner v2.9.1"
git push origin main
git push origin v2.9.1
```

Mise à jour suivante :

```bash
git checkout -b feature/ma-fonctionnalite
git add .
git commit -m "Ajoute ma fonctionnalité"
git push -u origin feature/ma-fonctionnalite
```

## Sécurité

- ne publiez jamais `.env` ;
- révoquez toute clé API exposée ;
- placez l'application derrière HTTPS pour un usage distant ;
- limitez l'accès réseau au menu Paramètres ;
- sauvegardez le volume avant chaque montée de version.

## Dépannage

### Redmine ne remonte rien

```bash
sudo docker compose logs --tail=200 backend
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

Vérifiez le nom exact du champ `Tag`, sa valeur `MEP`, la clé API et les droits Redmine.

### Les horaires ne remontent pas

Vérifiez que les champs sont activés dans le projet et que les noms correspondent exactement à :

```env
REDMINE_START_TIME_FIELD=Heure de début
REDMINE_END_TIME_FIELD=Heure de fin
```

### L'email échoue

```bash
sudo docker compose logs --tail=200 backend | grep -i smtp
```

Une erreur SMTP est enregistrée dans la page Communications sans bloquer la synchronisation Redmine.


## Thème clair / sombre et langue

Deux commandes sont disponibles en bas de la barre latérale, juste au-dessus de l’état Redmine :

- sélecteur **Français / English** ;
- bouton **Thème clair / Thème sombre**.

La langue est enregistrée dans SQLite et utilisée par l’interface, les emails et les PDF. Le thème est mémorisé localement dans le navigateur. Les valeurs initiales peuvent être définies dans `.env` avec `APP_LANGUAGE` et `APP_THEME`.

Le nom de l’entreprise est une information de configuration uniquement. Dans les emails et PDF, seul le logo d’entreprise facultatif apparaît à côté de l’identité MEP Planner.


## Administration des paramètres

Les modifications dans **Paramètres** sont protégées par le mot de passe défini dans `.env` :

```env
ADMIN_PASSWORD=utilisez-un-mot-de-passe-long-et-unique
ADMIN_SESSION_HOURS=8
```

Le navigateur conserve uniquement un jeton temporaire dans la session. Le mot de passe n’est jamais renvoyé à l’interface après authentification. Fermer l’onglet supprime le jeton local.

## Dépôt GitHub et mises à jour

Dépôt officiel : https://github.com/Maxime3d77/MEP-Planner

```env
GITHUB_REPOSITORY_URL=https://github.com/Maxime3d77/MEP-Planner
GITHUB_API_REPOSITORY=Maxime3d77/MEP-Planner
GITHUB_CHECK_TIMEOUT_SECONDS=8
```

La page Paramètres compare la version installée avec la dernière **Release GitHub**. En l’absence de release, elle consulte le dernier tag. Pour publier une version détectable :

```bash
git tag -a v2.9.1 -m "MEP Planner v2.9.1"
git push origin v2.9.1
```

Créez ensuite une Release GitHub à partir de ce tag. Le contrôle de mise à jour est informatif : il ne télécharge et n’installe rien automatiquement.

## Calendar invitations

When a scheduled release has a start time, MEP Planner attaches an iCalendar (`.ics`) invitation to notification emails. The event includes the actual start and end time, environment, priority, status, assignee, description, and Redmine link. A stable event UID is used so later release updates modify the existing calendar event rather than creating duplicates.

---

# Matrix Integration

MEP Planner can post formatted release notifications to a Matrix room.

Open **Settings → Team messaging → Matrix**, then configure:

- **Server URL**: Matrix homeserver URL, for example `https://matrix.example.com`
- **User access token**: access token of the Matrix account used by MEP Planner
- **Room ID**: internal room identifier, for example `!roomId:example.com`

The Matrix account must already be a member of the target room and must be allowed to send messages.

Available notification triggers:

- new scheduled releases;
- updated releases;
- optional daily reminders.

Messages include:

- a priority-specific visual color;
- issue number and subject;
- schedule;
- environment;
- priority and status;
- assignee;
- direct Redmine link;
- optional MEP Planner link.

Use **Test Matrix connection** to save the current Matrix configuration and send a test message to the selected room.

The access token is stored in the persistent SQLite settings database. It is never returned to the browser after it has been saved. Leaving the token field empty keeps the existing token.

Initial values can also be provided through `.env`:

```env
APP_PUBLIC_URL=https://mep-planner.example.com
MATRIX_ENABLED=false
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_ACCESS_TOKEN=
MATRIX_ROOM_ID=!roomId:example.com
MATRIX_NOTIFY_NEW=true
MATRIX_NOTIFY_CHANGED=true
MATRIX_NOTIFY_DAILY=false
```

Microsoft Teams, Slack, Discord and Mattermost are displayed in the integrations area as disabled future connectors.


## v3.2.1 interface correction

The administration area is now a dedicated full-width page rather than a modal dialog. Tabs use application-native styling, horizontal and nested modal scrollbars have been removed, and the Users section remains separate from Communications.


## Administration v3.4

The Settings page can configure Redmine, SMTP, Matrix, LDAP/Active Directory and OpenID Connect. Local accounts support User and Administrator roles. LDAP users can be searched and imported. Standard users use the Profile page to select interface language, communication language and email notification preference.


## Authentication

MEP Planner now requires a local or LDAP account before the application is displayed. Administration menus are available only to users with the `admin` role.


### LDAP / LDAPS

Version 3.5 adds an LDAP configuration assistant, optional private CA certificate import, group discovery, role mapping and just-in-time user provisioning. LDAP-backed accounts are validated and synchronized when users sign in; passwords are never copied into MEP Planner.


## Safe updates and persistent customization

MEP Planner 5.0 stores runtime configuration and branding outside the application code. Updates preserve `.env`, `data/`, `logs/`, `backups/` and `docker-compose.override.yml`. Company logos, favicon, login background, SMTP settings, LDAP/OIDC configuration and user data therefore survive upgrades.

Run an update from the installation directory:

```bash
./scripts/update.sh
```

The updater creates a pre-update backup, downloads the latest GitHub release, rebuilds the containers, checks `/api/health` and rolls the application code back automatically when the health check fails.
