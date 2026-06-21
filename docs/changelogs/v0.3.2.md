# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

- `tcw work new` and `tcw work start` now print the **next lifecycle transition**
  to stderr (e.g. `→ next: … run \`tcw work start <slug>\``), so an agent is nudged
  to `start`/`complete` even when the `tcw-work` skill never loads. stdout is
  unchanged (slug-only for `new`); epic `new` omits the start-hint (its next step is
  delegate). `tcw-work` skill's lifecycle section rewritten into imperative,
  trigger-based cues. (`37e3984`..HEAD)
