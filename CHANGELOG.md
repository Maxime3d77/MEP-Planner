# Changelog

## 5.1.1
- Nouveau centre de santé avec score, services, ressources et alertes.
- Centre de sauvegarde Web : création, historique, téléchargement, import, suppression et restauration.
- Sauvegarde de sécurité automatique avant restauration.
- Contrôle des archives importées et protection contre les chemins ZIP dangereux.

## 5.1.1 - 2026-07-21

- Added a dedicated SMTP administration tab with connection testing.
- Added persistent light/dark logos, favicon and login background assets.
- Added authentication and application log views and richer authentication events.
- LDAP login logs now contain only mapped MEP Planner groups and the resolved role.
- Added service health diagnostics.
- Added a safe host-side updater with backup, preserved `.env`/data/branding/logs, health check and rollback.
- Moved runtime data, logs and backups to persistent host directories.


## v5.1.1

### Fixed
- Status pie chart now includes in-progress, completed and every other status in the selected reporting window.
- Priority chart now includes all priorities from past and upcoming scheduled releases.
- Environment chart now includes every environment instead of only production values.

### Changed
- Status, priority and environment breakdowns now use the full selected window: past period, today and upcoming scheduled releases.
- Report totals and planning-quality metrics use the same complete reporting scope.

## v4.0.5

### Added
- Toggle between completed releases, scheduled releases and both trend series.
- Future scheduled releases are now included in the reporting API.
- Scheduled releases use a dedicated blue dashed line.

### Changed
- The trend chart selector is available directly in the report card.
- Completed releases retain the soft green visual style.

## v4.0.4

### Fixed
- Left navigation panel now scrolls independently when the viewport height is too small.
- Prevented menu items from becoming inaccessible on laptops and small screens.

## v4.0.4

### Changed
- The release trend chart now uses a soft, high-contrast green palette.
- Improved chart line, area and point visibility in dark mode.
- Added subtle glow and stronger point markers without making the graph visually aggressive.

### Fixed
- Low-contrast trend rendering that made the release series difficult to read.

## v4.0.2

### Added
- Total upcoming releases KPI on the dashboard.

### Changed
- Extended English translations across Communications, Redmine, Users and OIDC settings.
- User role and action labels now follow the selected interface language.

### Fixed
- Report trend area rendering as black in browsers without `color-mix()` support.
- Remaining French labels shown while the administration interface was set to English.

## v4.0.1

### Fixed
- Restored the Profile view HTML structure.
- Profile now contains only personal preferences.
- Fixed the Settings crash: `Cannot read properties of null (reading classList)`.
- Prevented view rendering errors from being reported as Redmine API failures.
- Aligned the README banner with the official MEP Planner logo.
- Updated visible and backend version numbers.

## v4.0.0

### Added
- Modern reports dashboard.
- SVG release trend chart.
- Status and notification donut charts.
- Priority column chart.
- Environment horizontal bar chart.
- 7, 30, 90 and 365-day reporting periods.
- README hero banner.

### Changed
- Reports API now returns timeline, status breakdown and planning quality.
- README rewritten and updated in English.
- Administration translation coverage improved.
- Application version updated to 4.0.0.

### Fixed
- Hardcoded English report labels.
- Multiple French administration labels displayed in English mode.

## v3.6.0

### Added
- LDAP group mapping
- JIT provisioning
- LDAPS CA certificate import
- LDAP diagnostics

### Changed
- Redesigned LDAP configuration
- Improved reports UI
- Improved translations

### Fixed
- HTTP 500 on LDAP login
- Redmine configuration
- Profile rendering
