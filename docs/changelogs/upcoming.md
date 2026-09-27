# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `tcw work tracker import --parent <slug> --initiative <epic>`: nest the
  imported item, checked before the ticket is claimed — the way to nest a child
  under strict mode, where `new --parent` stays refused.

### Fixed

- A blocker naming another node's item resolves against that node (#28).
  `WorkStore.external_blocker_state(text)` (default: still blocks) is
  overridden by `FsWorkStore` to settle exactly `<project-id>/<slug>` through
  `resolve_qualified_work_ref`, live item or tombstone; a bare `external:` entry
  naming a tombstoned local slug resolves too. `unresolved_blockers` uses it,
  so `start`, `complete`, `list` and the strict tracker check agree; a declared
  project absent from this checkout keeps blocking with its reason in the label.
  `_entry_for` records a tombstoned local slug as `slug:`. `reconcile`'s Next
  line asks each row's own store and labels rows by node — it had keyed bare
  slugs across nodes and ignored local `slug:` blockers outside the epic.
- Epic completability reads the same in every checkout. `Tombstone` gains
  `initiative`, written on resolution and carried through retention deletion,
  nested items and `tombstone add`. `WorkStore.resolved_initiative_children`
  (default `[]`; FS: this node and every node below, a present item winning)
  feeds `epic_children_all_resolved` and `check_type_change`, so an epic whose
  children are resolved and absent can close from `backlog` and cannot be
  demoted. `incomplete_graph_note(below=True)` limits the epic gates to missing
  child projects. `update_work` refuses to change a resolved item's
  `initiative`. `reconcile` lists record-only children as
  `node | slug | <status> | -` rows and counts them in "Ready to close". Tombstones written before this carry no epic and behave as
  before.
- `delegate` and `reconcile` pass through a routing node — a registered child
  that keeps no board (GitHub #30). `delegate` resolves its target among
  `routed_children` (the nearest node with a work store on each branch; new in
  `tcw/store/fs.py`) and reports a target declared behind a routing node but
  absent from this checkout as such (`routed_unreachable_children`). `reconcile`'s
  table (`_tasks_for`) rolls up from every descendant with a board, the set
  `initiative_children` already gives the completion gate, so the table and the
  gate no longer disagree. `child_nodes` still backs `tcw work nodes`.
- An item started before its spec and plan is no longer stuck. `STAGE_STATUSES`
  makes `spec` and `plan` legal in `active` as well as `backlog` (nothing moves
  an item back), so their gates and `scaffold spec|plan` work on it.
  `tcw work start` and the `implement` gate print a warning naming whichever of
  `spec.md`/`plan.md` is missing and the gate command to write it; neither
  refuses. The `plan` next step names both branches. This repository binds
  `require_artifact.py spec` and `plan` as `pre` on `implement`, so here it
  refuses. `tests/fixtures/prompt_fallback` re-captured for the `plan` entry.
- Tracker commands refuse what they cannot read. `FsWorkStore.read_sidecar`
  raises `OSError` when something other than a regular file sits at the
  sidecar's name (it returned `None`, so a folder named `tracker.yaml` read as
  unbound: `link`/`unlink` went ahead and strict `drop` let the item go), and
  `binding_of` turns read errors into `unreadable_binding`. `tracker sync <slug>`
  names an unusable binding instead of calling it unbound. The web sidecar route
  answers such a file with 400.
- `JiraClient` raises `TrackerError` ("a response of an unexpected shape for
  <path>") for a response that is not a mapping, or whose `issues`,
  `transitions`, `comments`, `fields`, `status`, `statusCategory`, `assignee` or
  `to` is not the list or mapping read downstream (`_mapping`, `_entries`,
  `_check_issue`), instead of an `AttributeError` traceback. Null stays absent;
  `_document_text` ignores a `content` that is not a list.
- `tracker link` refuses an item waiting for deletion (`pending_deletion`),
  before any tracker call. Single-item `tracker create` runs the sweep's board
  check first (`_unreadable_sidecars`, which now counts any unusable binding):
  another item's unreadable `tracker.yaml` would let it make a ticket it then
  could not bind.
- When `complete`'s merge-back is refused, it lists every staged file in the
  merged repository's index (git refuses the merge over any of them), not only
  the item's own tracker record.
- Strict mode refuses a move its ticket cannot follow. `authorize`
  (`tcw/tracker/sync.py`) takes `move` and `resolution` and asks `assess_move`
  with the configured transition name, as `deliver` does, so a `submit`,
  `rework` or `complete` whose workflow offers no transition — or several and no
  name — is refused before the item moves, instead of leaving a conflicting
  record that refused the next move. Skipped for an unmapped target and while
  another open part holds the ticket. Not asked of a legacy `catch-up` binding, which
  `deliver` walks rung by rung.
- Inside a linked worktree, every node of the checked-out repository resolves to
  its worktree copy. `ProjectRegistry._locator_path`'s Rule 2 aliased only the
  current node's main-checkout path, so from a package node the repository's root
  and sibling packages loaded a second time from the primary checkout — duplicate
  project ids and reciprocity failures (GitHub #39). It now aliases any path
  under the main worktree whose counterpart under this worktree holds a config
  in the same repository (`_worktree_copy`), for a locator and a `repository:`
  declaration alike, leaving paths already inside the worktree and separate
  repositories nested in it alone (a submodule of this repository is followed); ids repeated across different repositories are still
  duplicates. `_counterpart_path` is gone.

- Store names are never read as patterns. Every git call in `tcw/store/fs.py`
  that takes a pathspec (`add`, `rm`, `rm --cached`, `status`, `commit --`,
  `ls-files`, `ls-tree`), pass each path as `:(literal)<path>` (`_literal`),
  so writing the capability `a*`
  no longer stages or commits `abc`. Per path, not `--literal-pathspecs`, which
  exports `GIT_LITERAL_PATHSPECS` to the hooks `git commit` runs; `git_rm`'s flag
  is replaced the same way. `git mv` takes plain paths and is unchanged.
- `FsWorkStore._claiming_dirs` returns no claims for a slug that is not one
  plain path segment, so `get`, `start` and `submit("/etc/passwd")` answer
  "no such work item" instead of `NotImplementedError` from `Path.glob`, and
  `GET /api/work/%2Fetc%2Fpasswd` is a 404.
- One item's unreadable `capabilities.yaml` no longer breaks the board.
  `FsWorkStore._read_item` caught only `yaml.YAMLError`, so a file that was not
  UTF-8 or a folder of that name made `tcw work list` exit 1 for every item, a
  named pipe blocked the read, and ten lines of nested YAML anchors made
  `show --json` walk 10⁹ values. Every such file now reads as the
  `_tcw_parse_error` value, which the completion gate already refuses: not a
  regular file, not UTF-8, over `SIDECAR_MAX_BYTES` (1 MB), any read error, or
  more than `SIDECAR_MAX_VALUES` (10,000) values counted through aliases, or
  nested deeper than `SIDECAR_MAX_DEPTH` (100) through them
  (`sidecar_value_problem` in `tcw/store/base.py`). The web detail computes the
  sidecar's revision from a tolerant read, and the sidecar route answers a
  non-UTF-8 file with a 400 naming it instead of the decoder's message
  (`read_sidecar` still raises `UnicodeDecodeError`, which tracker callers rely on).
  `tcw validate`'s scan of every `.yaml` and `.md` file (`_read_text` in
  `tcw/validate.py`) reports a file that is not regular, not UTF-8 or not
  readable as a problem line instead of crashing or blocking on a named pipe.

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


- Lifecycle `when.tags` / `when.not_tags` are normalized with `normalize_tag`
  at parse time, so `CLI` matches items tagged `cli`. **Behavior change:** a
  condition written in a non-canonical form now fires, and for `not_tags` now
  excludes; in a first-match artifact list, such a condition can now match
  before a later canonical one. An element holding a comma (`"cli,docs"`) or normalizing to nothing is
  a parse problem. `tcw validate` reports condition tags that are not
  registered (`FsWorkStore._condition_tag_problems`), in stages, transitions,
  artifacts and procedures, naming the entry by its `kind: value`; the policy
  still loads.
- `registered_tags` returns normalized, de-duplicated tags; an entry that is not
  a tag — a non-string, or a string holding a comma, which was registered as
  `cli-docs` — is reported by `check` instead of breaking tag reads. Plan-stage tags are
  normalized before the registry check. `_validate_tags` refuses a non-string tag
  with `ValueError` (was `AttributeError`, a 500 from the web API).
- An item's tags are read through the new `read_tags` (`tcw/store/base.py`):
  normalized, de-duplicated, in first-seen order, so a tag hand-edited into
  `state.yaml` as `CLI` is `cli` for conditions, `list --tag`, `edit --untag`,
  `check`, and the tracker's bug issue type (`TrackerCreate.type_for`), and is
  displayed as `cli` by `list`, `show` and the web app. An entry that cannot be
  a tag (a non-string, a comma, nothing left after normalizing) is kept as its
  text, so `check` reports it and `show` no longer raises on a bare `7`; a bare
  string rather than a list is one tag, not one per character.
- `_write_tags` (`tcw work tags add` / `rm`) refuses, naming the entry, while
  `work.tags` holds an entry that is not a tag. It used to rewrite the list
  without it, and raised `TypeError` on a mapping entry.
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

### Removed

- `ClaimOutcome.account_id` and `account_name`, which nothing read.
