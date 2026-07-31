# Rollout Logger integration

Rollout Logger is an optional, read-only source displayed in **Release History**. It does not replace or alter Redmine. Completed Redmine tickets remain available exactly as before.

## Configuration

```env
ROLLOUT_LOGGER_ENABLED=true
ROLLOUT_LOGGER_URL=http://rollout-logger.edd
ROLLOUT_LOGGER_VERIFY_TLS=true
ROLLOUT_LOGGER_TIMEOUT_SECONDS=15
```

The backend calls `GET /data.json` and supports `project`, `environment`, `requester`, `limit`, and `offset`.

Use **Settings → Rollout Logger → Test connection** to validate access.


## Automatic notifications

MEP Planner polls the 100 most recent records and detects new deployments with a persistent fingerprint. On the first start after enabling the integration, existing records are registered as a baseline and are not sent, preventing a notification flood. Every later rollout is sent to the configured SMTP recipients and Matrix room. Failed deliveries are retried during later polling cycles.

Settings:

- `ROLLOUT_LOGGER_POLL_INTERVAL_SECONDS` (minimum 30 seconds)
- `ROLLOUT_LOGGER_NOTIFY_EMAIL`
- `ROLLOUT_LOGGER_NOTIFY_MATRIX`
