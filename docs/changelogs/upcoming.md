# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `init` (`tcw work init`, `tcw init`) no longer writes back a `work.path` it read
  from `tcw-config.yaml` when no path was given: `./store` now stays `./store`
  instead of becoming `store`, and `~/store` is no longer expanded into an
  absolute home-directory path in a committed file. A `~name` naming no user (in
  `work.path` or `--path`) is reported as `tcw init: …` instead of a traceback.
- The web app opened its "Stale write detected" banner for every 409 from a save,
  dropping the server's message. A stale-revision refusal now carries
  `"code": "stale-revision"` in its JSON body (`_map_store_error`), and the
  client (`isStaleWrite` in `web/client/src/model/api.ts`) opens the banner only
  for that; any other refusal — a write to a generated sidecar, for one — shows
  the server's message. Status codes are unchanged.
- `tcw work edit` changes nothing when it refuses any part of a command. It used
  to write `--unblocked-by`, `--blocked-by` and `--blocks` before `update_work`
  validated tags, so e.g. `--blocked-by Y --tag unregistered` recorded the
  blocker and then exited 1. New `WorkStore.check_blocker_edits` checks the
  blocker edits together, against the item's proposed blockers, before any write;
  `_edit` then runs `update_work` and only then the blocker writes.
- `update_work(blockers=...)` — the web app's save path — now refuses a newly
  added self-block or blocking cycle, through the same `_check_new_blocker`
  rule `add_blocker` uses. Entries the item already has are not re-checked, so
  an item already in a cycle stays saveable.

### Fixed

- Lifecycle `when.tags` / `when.not_tags` are normalized with `normalize_tag`
  at parse time, so `CLI` matches items tagged `cli`. **Behavior change:** a
  condition written in a non-canonical form now fires, and for `not_tags` now
  excludes. An element holding a comma (`"cli,docs"`) or normalizing to nothing
  is a parse problem. `tcw validate` reports condition tags that are not
  registered (`FsWorkStore._condition_tag_problems`), in stages, transitions,
  artifacts and procedures; the policy still loads.
- `registered_tags` returns normalized, de-duplicated tags; an entry that is not
  a tag is reported by `check` instead of breaking tag reads. Plan-stage tags are
  normalized before the registry check. `_validate_tags` refuses a non-string tag
  with `ValueError` (was `AttributeError`, a 500 from the web API).
- Six "unknown key" messages in `tcw/store/base.py` sort `map(str, keys)`, so an
  unquoted number key is named instead of raising `TypeError`.
- `tcw work list --tags X` with X registered in no listed node prints a note to
  stderr and still lists.
- A `skill:` binding whose value holds whitespace or a path separator is a parse
  problem; existence is deliberately not checked.
