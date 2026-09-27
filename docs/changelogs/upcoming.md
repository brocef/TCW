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
- `find_node` now answers "no node here" (`None`) only for
  `StoreLocationUnusable`, the ladder's own "no store at this location". Any other
  `ValueError` from opening a store — an `extends` naming an unreachable project,
  a store extending itself, a malformed `extends` list, an empty
  `<component>.path` — reaches the user as `tcw: <message>` instead of "no tcw
  <component> node here — run `tcw init`", which could scaffold a second, empty
  store beside the real one. One exit code changes with it: `tcw work procedure
  prompt` in a node whose `work.path` is empty or not a string now fails with
  that error (exit 1) instead of printing TCW's built-in text.

### Fixed

- `FsTaxonomyStore.remove` refuses a term a local capability names in `Subject`
  or `Feature` (`_capability_referrers`, compared by folder identity), and
  refuses — failing closed — when the node's capabilities store cannot be opened
  or read. The abstract `TaxonomyStore.remove` contract says so.
- It also refuses, before anything is removed, when any file under the term is
  not tracked by git (`_untracked_under`), and a term whose own files are not
  tracked gets a TCW message instead of git's. `.DS_Store`, `Thumbs.db` and
  `desktop.ini` do not block: they are deleted with the term, so the term (and a
  folder holding only them) stops listing. `rm` no longer reports removing a term
  that still lists.
