As a user, I run `tcw init --id <project-id> [taxonomy|capabilities|work]` to
scaffold component trees in the current git work tree and create a
`tcw-config.yaml` marker with a canonical project ID. The per-component mirrors
accept the same `--id`. On an already configured node I may omit `--id` or repeat
the same value; a conflicting value is rejected. I can backfill a legacy marker
with `tcw init --id <project-id>` without losing tags or other configuration.
