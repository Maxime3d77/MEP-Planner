# 5.2.0

## Added
- Optional Rollout Logger source configured from `.env` or the administration interface.
- Unified MEP history combining completed Redmine tickets and completed Rollout Logger deployments.
- Rollout Logger connection test, filtering proxy, pagination and logs.

## Unchanged
- Redmine remains the source for planning and completed MEP tickets.
- Existing Redmine synchronization, statuses and history behavior are preserved.

# Changelog

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
