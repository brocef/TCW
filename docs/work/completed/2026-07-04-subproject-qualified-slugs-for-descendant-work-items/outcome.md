# Outcome — Subproject-qualified slugs for descendant work items

Work completed successfully. All four phases implemented; full suite green
(**466 passed**, incl. **30 new tests** — 14 resolver + 10 CLI + 6 serve).

## What changed

- **Phase 1 — resolver** (`tcw/store/fs.py`, `tests/test_qualified_ref.py`):
  `resolve_qualified_work_ref(anchor, ref)` maps a work ref to
  `(FsWorkStore, bare_slug)`. Bare → anchor; `sub/proj/<slug>` → descendant store.
  Guards (in order): `anchor.resolve()`; `rpartition` last `/`; `target.resolve()`;
  `is_relative_to` traversal guard; reject if the **resolved** target's
  anchor-relative segments include `.git`/`.worktrees`; node-sentinel check. 14
  unit tests incl. the symlink-into-`.worktrees` and `..`-recombination cases.
- **Phase 2 — CLI** (`tcw/work/cli.py`, `tests/test_work.py`): `_render_board`
  gains a `prefix`; `_list` qualifies descendant rows; a `_resolve(slug, label)`
  helper routes `show`/`path`/`start`/`edit`/`complete`/`drop` to the resolved
  store. Store/git calls use bare (incl. reverse `add_blocker(ref, bare)` and
  `remove_worktree(…, bare, …)`); echoes print the qualified ref. `_path` now
  catches `MultipleMatch`; dead `_run` removed. 10 new tests.
- **Phase 3 — serve** (`tcw/serve/__init__.py`, `tcw/cli.py`,
  `tests/test_serve_descendants.py`): `--include-descendants` (default off) threads
  through `TcwServer`; `GET /api/work` aggregates descendant boards; gated
  `_resolve_work` routes all 10 `/api/work/<slug>…` handlers. 6 new tests.
- **Phase 4 — docs**: README (list + serve + multi-project sections),
  `skills/tcw-work/SKILL.md`, `docs/changelogs/upcoming.md`,
  `docs/release-notes/upcoming.md`.

## Verification performed

- `pytest -q` → **466 passed** (436 pre-work baseline + 30 new: `test_qualified_ref.py`
  14, `test_work.py` +10, `test_serve_descendants.py` 6). Existing
  `--include-descendants` and single-node serve tests unaffected.
- Manual CLI smoke (temp repo + `SubprojectA/` node): `list --include-descendants`
  prints `SubprojectA/<slug>`; `show`/`path` on the qualified slug resolve to the
  descendant; a bare descendant slug from the root correctly reports "no such work
  item" (exit 1).

## Deviations from plan.md

- **Serve response re-stamping (added, not in plan).** The plan asserted "frontend:
  no change required." That held for the board and read chaining *except* the detail
  payload: the web UI derives artifact/sidecar/action URLs from `payload.item.slug`
  (app.js:1419), so returning the *bare* slug would break editing a descendant's
  artifacts — an acceptance criterion ("opening/editing one via the web app resolves
  to the descendant"). Fix kept the frontend unchanged by having the **backend**
  echo the *qualified* slug in the detail, action, and PATCH responses (store calls
  still use bare). Covered by `test_detail_via_qualified_slug_flag_on` and
  `test_mutating_action_on_descendant_flag_on`.
- One residual spec/plan contradiction (the "serve default" paragraph still claiming
  always-on resolution is harmless) was fixed in `spec.md` before implementation.

## Follow-up notes (not yet TCW items — closeout decision)

- Frontend polish: the web board renders a flat list; descendant items show their
  qualified slug but are not visually grouped by node. Optional node-grouping/label
  UI was deferred (functional without it). Candidate follow-up if desired.
- Taxonomy/capabilities have no descendant aggregation; qualified addressing is
  work-only by design. If either later aggregates descendants, the same resolver
  pattern applies.

## Closeout still pending (do NOT run without user approval)

- Capability ledger flip (tcw-capabilities): extend the
  `cli/host-multiple-projects-in-one-repo` body; confirm `work#view-the-board` /
  `web#*` scope. Recorded in this item's `capabilities.yaml`.
- Version: **minor** bump offered (user-facing feature addition).
- `tcw work complete … --resolution done --confirm`.
