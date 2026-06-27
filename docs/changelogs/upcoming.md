# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `f6d9e71..46457a1` — Added `tcw work audit-work-backlog` with read-only audit
  findings for duplicates/completed overlap, missing lifecycle artifacts, broken
  local references, stale blockers, malformed capability deltas, wrong-node
  candidates, and actionability issues.
- `c0d7724..12c92a1` — Added `tcw work consolidate-plans` with dry-run discovery,
  `--apply` backlog-item migration, lifecycle artifact import, optional
  post-migration `--delete`, and focused CLI tests.

## Changed

- `f6d9e71..46457a1` — Made work-item `capabilities.yaml` loading tolerant of YAML
  parse errors so malformed capability deltas can be reported by audits instead
  of crashing backlog reads.
- `909082a..866786b` — Changed `tcw work list` to print lifecycle artifact stages
  (`RSPOF`) in the third column instead of the usually-empty `phase` value, with
  tests for nonempty artifacts and empty-file omission.
