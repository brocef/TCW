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

### Fixed

- Lifecycle `when.tags` / `when.not_tags` are normalized with `normalize_tag`
  at parse time, so `CLI` matches items tagged `cli`. **Behavior change:** a
  condition written in a non-canonical form now fires, and for `not_tags` now
  excludes; in a first-match artifact list, such a condition can now match
  before a later canonical one; and an item whose tags were hand-edited into a
  non-canonical form (`CLI`) no longer matches a condition written the same
  way. An element holding a comma (`"cli,docs"`) or normalizing to nothing is
  a parse problem. `tcw validate` reports condition tags that are not
  registered (`FsWorkStore._condition_tag_problems`), in stages, transitions,
  artifacts and procedures, naming the entry by its `kind: value`; the policy
  still loads.
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
- `tcw validate` checks the `capabilities.yaml` of every item in backlog, active
  or review (`_open_sidecar_problems`), reporting `<file>:<line>: <problem>` for
  an unroutable or ambiguous path, a `changed:` path that does not resolve, a
  `new:` path that does not resolve once the item is active, and a `removed:`
  path naming an inherited capability. `capability_gate(..., in_progress=True)`
  shares the completion gate's routine without its completion-only checks
  (`new` still `Missing`, `removed` still resolving). Resolved items are never
  checked (GitHub #27).
