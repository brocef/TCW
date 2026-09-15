# Outcome

Work completed successfully. Both mechanisms implemented across six phases; full
suite green at **601 passed** (up 34 from 567, no regressions). Independent code
review in progress at time of writing; not yet completed (see verification note).

## What changed

**Phase 1 — canonical sidecar parser** (`tcw/store/base.py`). `declared_capabilities()`
reads a work item's `capabilities.yaml` into `{new, changed}` from the canonical
`namespace/path` shape; `added:` is read as `new:` (deprecated alias); a trailing
` # comment` is stripped; the `_tcw_parse_error` sentinel raises the new
`SidecarError` so the gate can fail closed. **Deviation:** the plan's
`WORK_SIDECARS` validation-tightening was dropped — `capabilities.yaml` is the
only registered sidecar and existing tests use it as a generic mapping (`links:`),
so tightening would break that contract for no real gain; the gate's tolerant
parser is the actual protection.

**Phase 2 — unreviewed detection** (`tcw/store/fs.py`, `tcw/store/base.py`).
`CapabilitiesStore.unreviewed_inherited()` (new abstract method) flags inherited
capabilities whose status is the master's default. Detection keys on the override
index (`_status_is_local`), not `origin` — an override keeps `origin=alias` — and
requires the override to actually set `Status` (one editing only a body/field
re-inherits the master status).

**Phase 3 — the DoD gate** (`tcw/work/cli.py`). `_capability_gate` runs in
`_complete` after worktree merge-back, opening an `FsCapabilitiesStore` on the
work node. `new:` capabilities must not read `Missing`; `new:`/`changed:` paths
must resolve; `changed:` carries no status requirement. Fails closed with a
per-capability report unless `--force`. `WorkStore.complete` gains no capabilities
handle — the axes stay loosely coupled.

**Phase 4 — `tcw capabilities drift`** (`tcw/capabilities/cli.py`). Read-only
report: unreviewed inherited + local `Missing` whose `Planning doc` names a
completed work item. Exits non-zero on drift. The `Planning doc` scan
(`_shipped_but_missing`) is a read-only follow of an existing capability→work
forward pointer and degrades to silence when no work node is present.

**Phase 5 — docs.** `skills/tcw-work/SKILL.md`, `skills/tcw-capabilities/SKILL.md`
(enforced flip, canonical schema, drift row), `README.md`, changelog, release
notes.

## Verification performed

- **Full suite: 601 passed** (`python -m pytest tests/ -q`), +34, no regressions.
- New coverage: `tests/test_capabilities_sidecar.py` (9), gate tests in
  `tests/test_work.py` including a **worktree-branch-flip test** that pins the
  post-merge ordering (finding C from the spec review), drift tests in
  `tests/test_capabilities.py`, unreviewed-detection in
  `tests/test_capabilities_federation.py`.
- Dogfood: `tcw capabilities drift` on this repo → `no capability drift`, exit 0
  (this repo federates nothing and its declared capabilities are reconciled).
- `tcw validate` + `tcw capabilities check` clean.

## Deviations from plan.md

1. **`WORK_SIDECARS` validation not tightened** (Phase 1) — rationale above.
2. **`_capability_gate` handles `AmbiguousRef`** — the plan didn't call it out;
   `caps.get(path)` can raise on a bare ref matching two federated aliases, so the
   gate wraps resolution and reports the ambiguity as a problem rather than
   crashing.

## Follow-up notes (closeout decisions, not yet items)

- The gate catches *forgot to flip* (drift vector #1), **not** *flipped without
  building* — an author can still `set --status Supported` without doing the work.
  Honest scope, stated in the spec; no further action proposed.
- Mechanism 2's `drift` is a report, not a fixer. Auto-reconciliation was
  explicitly out of scope.
- The reporter offered a 5-node federation with ~10 known-drifted capabilities to
  validate a detector against. Validating `drift` against that real workspace
  would be worthwhile but needs their repo; candidate follow-up.

## Pending at closeout

- **Version decision.** v0.11.4 is cut and tagged locally but unpushed; the user
  wanted to consider rolling this item into it rather than cutting v0.11.5. If
  rolling in: move `docs/{changelogs,release-notes}/upcoming.md` into the
  `v0.11.4.md` files and re-tag; else cut a fresh version.
- Ledger flip (Phase 6, not yet run): `capabilities/detect-capability-drift`
  `Missing` → `Supported`; `work/complete-a-work-item` stays `Supported`.
