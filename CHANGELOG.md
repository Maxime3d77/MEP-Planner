# Changelog

## v5.3.9

- Correction définitive du calendrier du tableau de bord : toutes les entrées Redmine déjà présentes dans les historiques sont injectées dans la source calendrier.
- Le filtre Type d’historique est construit à partir des catégories réellement observées dans les tickets actifs/terminés puis enrichi avec la configuration dynamique.
- Une ancienne configuration de catégorie incomplète ne peut plus masquer Historique MEP/DC dans le calendrier.
- Ajout d’un cache-busting sur app.js/styles.css pour éviter qu’un navigateur conserve le frontend d’une version précédente.

## v5.3.8

- Correction robuste du calendrier du tableau de bord : aucune entrée Redmine n’est supprimée lorsque la liste `categories` de l’API est vide ou incomplète.
- Les catégories du filtre sont reconstruites dynamiquement depuis la configuration ET depuis les tickets Redmine actifs/terminés déjà chargés.
- Les options `enabled`, `history` et `calendar` restent prioritaires lorsqu’une catégorie est explicitement configurée.
- Le filtre « Type d’historique » affiche désormais un compteur par source afin de rendre immédiatement visible le nombre d’entrées Redmine/BO-FO chargées.
- « Tous » inclut toujours les tickets Redmine suivis, même si leurs métadonnées de catégorie sont momentanément absentes.
- Conservation du correctif backend `from datetime import date`.

## v5.3.7

- Correction du calendrier du tableau de bord : les historiques Redmine terminés restent visibles avec les entrées actives.
- Le filtre « Type d’historique » est maintenant généré à partir des catégories Redmine dynamiques activées pour l’historique.
- La configuration dynamique courante est utilisée comme source de vérité pour le libellé et la couleur des événements du calendrier.
- Déduplication des tickets Redmine présents à la fois dans les jeux actif/historique.
- Rollout Logger reste une source séparée et filtrable lorsqu’il est activé pour le calendrier.
- Correction du démarrage backend : import explicite de `date` utilisé par les rapports Rollout Logger.

## v5.3.6

- Calendar now merges scheduled and completed Redmine actions for every enabled dynamic category.
- Completed DC actions and any future Redmine categories remain visible in dashboard/day/month calendars.
- Added a dynamic calendar history-type filter (all Redmine categories plus Rollout Logger).
- Added a dynamic legend using each configured category color.
- Today view now includes completed Redmine actions for the current day.
- Improved collision layout with a readable minimum event height.
- Completed Redmine events are visually marked with a check.


## v5.3.4

### Fixed
- Automatic Redmine notifications are now permanently locked after an action reaches a terminal status (`Done`, `Closed`, `Resolved`, etc.).
- The transition to a terminal status still sends one final modification notification.
- Redmine journal/comment updates no longer trigger notifications because `updated_on` is excluded from the business signature.
- Tickets already terminal at startup are registered silently and cannot be re-announced as new actions.

### Changed
- Rollout Logger deployments are counted as completed BO/FO MEPs in Reports.
- Rollouts are included in completed timelines, environment statistics, status statistics (`Deployed`) and source/category statistics.
- Rollouts remain excluded from scheduled and priority statistics.

## v5.3.3

### Fixed
- Restored the Reports dashboard after a missing runtime configuration variable caused the summary API to fail.
- Added a visible error state when report data cannot be loaded.
- Individually imported LDAP users can now sign in without belonging to a mapped LDAP group.
- LDAP users imported manually retain the role assigned in MEP Planner.
- Existing LDAP accounts are migrated with direct-access compatibility; new JIT accounts remain restricted by LDAP group mappings.

## v5.3.2

### Added
- Dedicated, configurable Rollout Logger history menu.
- French and English Rollout Logger menu labels.
- Rollout Logger display options for the sidebar, calendar and reports.

### Changed
- Simultaneous calendar events are laid out side by side.
- Redmine category histories now contain only their own completed Redmine tickets.

### Fixed
- Rollout Logger deployments appearing in every Redmine category history.
- Overlapping calendar event text when several deployments occurred at the same time.

## v5.3.1

### Added
- Visible dynamic Redmine category editor at the top of the Redmine settings page.
- Per-category controls for dashboard, sidebar, calendar, history, notifications and reports.
- Per-category display order and live menu/dashboard preview.

### Changed
- Removed the obsolete single “Tag value” field from the visible settings form.
- Redmine tags are now managed exclusively through dynamic categories.
- Disabled categories are ignored by synchronization and public views.

### Fixed
- Category configuration area not visible in the Redmine settings page.
- User save handler referencing an undefined configuration variable.

## v5.3.1

### Added
- Dynamic Redmine tag categories with configurable labels and colors.
- Dedicated history menus generated from Redmine category settings.
- Scheduled DC actions displayed below scheduled MEP releases.
- Rollout Logger events displayed in the shared calendar.
- Category and source breakdown in Reports.
- Email and Matrix notifications for every enabled Redmine category.

### Fixed
- Rollout Logger email notifications now use SMTP settings saved from the web interface.
- Redmine notification jobs now use runtime SMTP recipients instead of startup-only environment values.

## 5.3.1

### Changed

- Published the Rollout Logger notification feature as version 5.3.1.
- New Rollout Logger deployments trigger the configured email and Matrix notifications.
- Existing Rollout Logger history remains ignored during first synchronization to prevent notification flooding.
- Persistent deduplication continues to prevent duplicate notifications after application restarts.

## 5.2.1

### Added
- Automatic detection of every new Rollout Logger deployment.
- Email notification to configured SMTP recipients for every new rollout.
- Matrix notification to the configured room for every new rollout.
- Persistent duplicate protection and automatic retry after delivery errors.
- Configurable notification polling interval and channel switches.
- Safe initial baseline to avoid sending the existing Rollout Logger history.

# 5.2.0

## Added
- Optional Rollout Logger source configured from `.env` or the administration interface.
- Unified MEP history combining completed Redmine tickets and completed Rollout Logger deployments.
- Rollout Logger connection test, filtering proxy, pagination and logs.

## Unchanged
- Redmine remains the source for planning and completed MEP tickets.
- Existing Redmine synchronization, statuses and history behavior are preserved.


All notable changes to MEP Planner are documented in this file.

## [5.1.4] - 2026-07-23

### Added
- Backup operation progress indicators and accessible live status messages.
- Application version metadata in the local backup history.
- Platform and Health Center refresh timestamps.
- Complete administrator documentation under `docs/`.
- GPL-3.0 license file.

### Changed
- Reworked the GitHub README for a clean, English-only project presentation.
- Improved Backup Center history readability and empty/error states.
- Simplified the Updates page to avoid duplicated installation information.
- Standardized application version references across backend and frontend.

### Fixed
- Backend and frontend version mismatch left in the previous 5.1.3 package.
- Backup table column alignment in empty and error states.
- Busy-state handling for backup creation and import.
- Update command text displaying encoded HTML after switching language.

## [5.1.3] - 2026-07-23

### Changed
- Initial documentation and release preparation update.

## [5.1.2]

### Fixed
- Health, SMTP and Updates interface corrections.
