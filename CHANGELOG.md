# Changelog

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
