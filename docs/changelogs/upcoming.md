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

- `tcw validate` finds the taxonomy and capabilities stores the way `find_node`
  does (`_tree_roots`): each is opened, reported if it will not open (a broken
  `extends` included), and checked at its resolved root when that is a
  directory. A store moved by `<c>.path` or declared by `<c>.repository` is now
  YAML-scanned, link-checked and component-checked; path mode matches resolved
  roots, falling back to `docs/<c>` for a store that will not open.
- `FsCapabilitiesStore._taxonomy` finds a moved taxonomy (`tree_store_present`:
  the default folder, or `taxonomy.path` / `taxonomy.repository` set), so
  Subject/Feature references are checked against it on write and in `check`. A
  configured taxonomy that will not open now refuses a capability write that
  needs it, and `check` reports "Subject and Feature not checked: …" once,
  beside its other problems, when a checked capability names a Subject or
  Feature — instead of skipping those references silently.
- `tcw validate` no longer crashes when `taxonomy.path` points nowhere while
  `docs/capabilities` exists: `_run_check` reports a `ValueError` raised inside
  `check()` as a problem.
- The stopgap pass after the component checks now runs only when a YAML problem
  skipped them; everything else it reported is reached by the component checks.

### Fixed

- `tcw work start <slug> --take-over` recovers an interrupted claim again. `_start`
  read the item with `get` for the `pre` hook before reaching the store, and
  `get` raises for an item left in `.claiming/`, so the documented remedy
  printed the same error. New `WorkStore.interrupted_claims()` (default `[]`;
  `FsWorkStore` reads `.claiming/<slug>-<hex>`, reporting each item as it was,
  status `backlog`) supplies the item for the hook, `before` and `previous`.
  Under strict tracker mode a recovery runs the same ticket claim as a start,
  with the binding rebuilt from the claimed item (`_recovered_binding`;
  `binding_refusal` gained `binding=`), since no store read reaches a claim.
- The web app can recover one: `GET /api/work/interrupted-claims` (every node
  the board shows, slugs qualified the same way), and the start action's
  `recover: true`, which claims for the server's identity (`_local_owner`)
  through the store's new `start(..., recover=True)`: a take-over that refuses
  any item settled in a status, decided against the same read it acts on, so a
  claim published meanwhile is never taken from its owner. The board shows a
  notice with a Recover button. `_strict_refuses` reads an interrupted claim
  instead of raising on it.
