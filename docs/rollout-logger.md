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
