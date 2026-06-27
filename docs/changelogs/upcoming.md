# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `f6d9e71..46457a1` — Added `tcw work audit-work-backlog` with read-only audit
  findings for duplicates/completed overlap, missing lifecycle artifacts, broken
  local references, stale blockers, malformed capability deltas, wrong-node
  candidates, and actionability issues.

## Changed

- `f6d9e71..46457a1` — Made work-item `capabilities.yaml` loading tolerant of YAML
  parse errors so malformed capability deltas can be reported by audits instead
  of crashing backlog reads.
