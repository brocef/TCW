# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Added

- `capability_gate` (`tcw/work/recursion.py`) checks child-qualified
  `capabilities.yaml` paths: a first segment naming a project declared under
  `connected-projects.children` routes the rest of the path to that child's
  ledger, via `get` for `new:`/`changed:` and `get_local` for `removed:`. The
  rule lives in the new public `route_capability_path` (returns a `Route` or a
  problem string), intended for reuse by the early sidecar check (GitHub #27).
  Order: an `extends` alias of the node's own ledger wins; then a declared child
  (refused as ambiguous when the node's resolved view, inherited entries
  included, lists anything under that namespace); then the node's own ledger.
- `tcw work complete`'s remedy line and discard hint say to reconcile a
  child-qualified path inside the child, naming each owning child and its
  location (`child_path_owners` in `tcw/work/recursion.py`); they say nothing
  about children when no declared path is child-qualified.

### Changed

- An unqualified path on a node with no ledger is refused (it used to pass
  silently); the message lists the node's declared children.
  `test_complete_gate_work_only_node_unaffected` is now
  `test_complete_gate_work_only_node_refuses_an_unqualified_path`.
- A `removed:` path whose first segment is an `extends` alias of the routed
  ledger is refused, since `rm` deletes only local capabilities; it used to pass
  because `get_local` found nothing at the literal path.
- The gate reads `capabilities.yaml` before opening the registry or any store,
  and turns every `ValueError` from `FsCapabilitiesStore.open` or
  `FsProjectRegistry.require_valid` into one problem line per declared path, so a
  discard is never aborted by a store failure. A `yaml.YAMLError` raised while
  checking one path (a malformed `meta.yaml` in a ledger it reads) becomes that
  path's problem line for the same reason.

### Changed

- `FsTaxonomyStore.check` and `FsCapabilitiesStore.check`, when not scoped to
  one identifier, report a pre-2.5.0 `config.yaml` / `.config.yaml` left at the
  store root, through the new `FsTreeStore._legacy_config_problems`. It tests
  only that the file exists — never opens, rewrites or deletes it — and names
  the file (relative to the node root, or absolute outside it) and
  `_extends_label()` as where any `extends` belongs. This reverses v2.5.0's
  "not reported by the component `check()`": a project that never moved its
  `extends` silently lost every inherited entry. A retained copy now fails
  `check` and `validate`, and so `tcw work complete` wherever `tcw validate` is
  a `pre` check.
- `validate()` reports that leftover directly for each tree store whose
  `check()` it did not run — a store outside `docs/<component>`, or any run
  whose component checks were skipped after a YAML problem — and, when such a
  store will not open, the open failure once in `_run_check`'s
  `<component> check: <error>` shape. Consequence: a tree store `validate` did
  not check before is now opened on every whole-node run, and any failure to
  open it is reported. On a node with no `docs/<component>` that includes a
  store declared in `<component>.repository` and not yet provisioned (naming
  `tcw provision`, as the work store already did), a `<component>.path` that
  does not exist — for example `../missing-tax` in a CI or cloud clone without
  the sibling checkout (`taxonomy.path is not a directory`) — and an
  inherit-only node whose `<component>.extends` names a project that is not
  reachable (`project 'ghost' is not reachable through connected-projects`).
  Any of these can refuse `tcw work complete` in a project whose `pre` hook
  runs `tcw validate`. The block is marked temporary, to be removed once
  `validate` covers relocated stores generally.
- `FsCapabilitiesStore._override_problem`: `overrides → unknown alias '<alias>'`
  gains `(not declared in <path>/tcw-config.yaml: capabilities.extends)`.

- `scripts/check_versions.sh`: compares the plugin manifest's version
  (`.claude-plugin/plugin.json`, else `.codex-plugin/plugin.json`) with
  `tcw --version` and, when they differ, prints both and the remedy for the side
  that is behind. Exits 0 on every path, is silent when it cannot tell, and
  abandons a `tcw --version` that has not answered within 3 seconds (a
  plain-bash deadline, killing the command's whole process group). It writes no
  file, temporary ones included, so it also works inside Codex's read-only
  sandbox. Lives in the
  plugin rather than the CLI because a CLI-side check would be absent whenever
  the CLI is the older side.
- `scripts/session_bootstrap.sh` runs the check from an `EXIT` trap registered
  once the plugin root is known, so it runs after any install attempt and on
  every early exit, including for a plugin root with no `tcw/__init__.py`. It is
  invoked through `bash`, so it does not depend on the executable bit.
- Every `skills/*/SKILL.md` opens with a line asking agents under any harness
  other than Claude Code to run the check once per session.
- `tests/test_check_versions.py`, and version-check cases in
  `tests/test_session_bootstrap.py` for each install branch.

### Changed

- `skills/setup/references/install.md` points at the warning;
  `skills/extras-report`'s bug skeleton asks for the plugin version.
- `test_real_editable_checkout_is_left_alone` accepts the version warning as
  its only output, since a maintainer's editable CLI can differ from the
  checkout's manifest.

### Fixed

- `capability_gate` found a ledger only at `<node root>/docs/capabilities`, so a
  ledger moved by `capabilities.path` or declared by `capabilities.repository`
  was never checked. It now asks the resolved store, as `find_node` does (part 1
  of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`).
- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.
- A `--parent` child created under an already-active parent was born `active`
  (its status was the top-level folder it was nested in), so its `request`,
  `spec` and `plan` stage gates refused it. A child's own transition also moved
  it to the top level and dropped the relation, and re-parenting through
  `update_work` changed an item's status by moving its folder.
- `tcw validate` reported a nested child carried into `completed/` by its parent
  as having no resolution.
- `delete_resolved` under `work.retain: false` removed children nested in a
  resolved item's folder without recording them in the graveyard.

### Changed

- **A child records its parent and has its own status.** `create_work` writes a
  child to `backlog/<slug>` with `parent: <slug>` in `state.yaml`, whatever the
  parent's status. `FsWorkStore._parent_slug` reads the field and falls back to
  folder nesting only when it is absent, so children written by earlier versions
  (nested, no field) keep following their parent. A nested child's own
  transition or claim writes `parent:` in the same move; a claim writes it
  before the folder enters `.claiming/`, and take-over stages the vacated path
  found from the git index (`_tracked_source`). `start --worktree` commits the
  real source path.
- `WorkStore` gains `independent_descendants` and `open_descendants` (whole subtree, walking through children that follow their
  parent, cycle-safe; the filesystem store also counts items mid-claim, including
  anything nested in a claimed folder), `require_nothing_open_beneath` and
  `_require_live_parent`. The pre-merge check in `tcw work complete` asks the
  branch copy only about children the primary copy does not have, since the
  branch copy is frozen at `start --worktree`.
- `complete` refuses while `open_descendants` is non-empty, for either
  resolution, outside the `--force` block. `drop` refuses while any independent
  descendant exists, open or resolved. `epic_completable` is false while any
  descendant is open, so `reconcile --complete-when-ready` agrees with
  `complete`. `tcw work complete` runs the check before merging a worktree
  branch, against the primary and the branch copy of the store.
- `create_work` and `update_work` refuse a parent that is missing, resolved or
  has a resolved ancestor (for an open item), and a cycle. Re-parenting is a
  field write; only a nested child is moved, to the top of its status folder.
- `delete_resolved` lists nested children from `git ls-tree` and records them
  with the parent in one graveyard write (`_write_tombstones`);
  `_require_writable_graveyard(also=...)` tolerates their uncommitted entries on
  a resumed removal. `_committed_item_path` and `_commit_holds` find a nested
  item in a past commit.
- `tcw validate` reports a `parent:` naming no item or tombstone, one that
  disagrees with the folder a nested item sits in, and a loop of `parent:`
  fields.
- The `.claiming/` scan stops walking at the claim folder, so a claim that
  lands mid-scan cannot send it climbing to the filesystem root. A claim an
  earlier version left (no `parent:` field) takes its parent from where git's
  index holds it, and `--take-over` writes it.

- `tcw work drop` on an item that is not in backlog now refuses before the
  `--confirm` gate and names the discard command
  (`tcw work complete <slug> --resolution wontfix --confirm`); a resolved item
  is reported as already resolved. Before, it advised `--confirm` and then
  refused with "cannot drop from active (only backlog)", naming no alternative.
  `skills/work/SKILL.md` spells out that `discard` is reached through
  `complete --resolution`.

### Added

- `work.tracker.pre-backlog`: tracker status → transition name to
  `statuses.backlog`, for statuses a workflow puts before its backlog.
  `TrackerConfig.pre_backlog`, parsed by `_parse_tracker_pre_backlog`, which
  fails closed on a non-mapping, blank names, a status listed twice (normalized),
  a status also mapped under `statuses`, and a missing `statuses.backlog`.
  `pre_backlog_entry` is the one lookup deciding whether a status is one of them.
- `intake.leave_pre_backlog`, called first by `intake.claim` (whose old body is
  now `_claim_from`). Applies the named transition only when the ticket's status is
  a `pre-backlog` key and the ticket is unassigned or the caller's; refuses before
  sending unless the transition is offered once and leads to `statuses.backlog`;
  re-reads the ticket and hands the claim that fresh read. New claim rows `0a`
  (refused before sending), `0b` (landed elsewhere), `0d` (the tracker refused it),
  `0e` (accepted but not moved), `0f` (uncertain, not arrived) and `0-read` (sent,
  not read back; counted as moved only when the tracker said it applied). The
  step's messages carry no recovery step: `deliver`'s caller names `sync`, strict
  `start` says to start again, and `import` says to run itself again.
- `deliver` gives no "take it with `tcw work tracker claim`" advice after rows
  `1b`/`3b` or any step row (`_NO_CLAIM_ADVICE`), since the snapshot it used to
  decide that can be stale after the step.
- `store.base.mapped_statuses`, shared by the `pre-backlog` parser,
  `intake._mapped_anywhere` and `sync.lowest_rung`.
- `ClaimOutcome.left_status`, and the same attribute on a `TrackerError` raised
  after the step, so every caller reports that the ticket left triage;
  `intake.moved_out` words it.
- `intake.pre_backlog_hint`: the sentence naming the key, for a ticket whose
  status is mapped nowhere.

### Changed

- Row `1f`'s refusal, `deliver`'s "claimed …, but it is in …" refusal (only when
  the claim applied no transition), and `tracker import` of a row-`1e` ticket (as a
  warning) name `work.tracker.pre-backlog` when the status is mapped nowhere.
- `deliver` records rows `0-read` and `0f` as `pending`.
- `_strict_claim`, `_tracker_import` and `deliver` print the moved-out sentence on
  success, refusal and a raised error; a strict refusal after the step says to run
  `start` again, since it writes no sync record. `tracker show`/`inbox show` add a
  note for a ticket in a `pre-backlog` status.

### Internal

- `tests/test_tracker_pre_backlog.py`: the setting, the step against the fake
  Jira, and every caller.

- `tests/test_taxonomy.py`: the malformed-leftover test asserts the YAML
  parser's own line; `any("config.yaml" in p)` would also have matched the new
  leftover report. The well-formed-leftover test now expects the report.
