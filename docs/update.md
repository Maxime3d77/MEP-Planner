# Updating

Run:

```bash
./scripts/update.sh
```

The script preserves persistent paths, creates a safety backup, downloads the release, rebuilds containers and checks `/api/health`. It automatically restores the previous version when deployment health validation fails.
