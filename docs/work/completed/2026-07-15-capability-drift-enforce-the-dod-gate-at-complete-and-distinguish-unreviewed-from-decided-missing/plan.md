# Plan — capability-drift DoD gate + drift detector

Implements the revised `spec.md`. Both mechanisms; gate fails closed with
`--force`. Enforcement in the CLI orchestration layer, not `WorkStore.complete`.

Execution: **sequential**. Phase 1 (schema) is a prerequisite for the gate; the
gate and the detector share the override/status helpers. One `tcw/` area with
interdependent pieces — subagent parallelization would collide.

## Phase 1 — pin the canonical sidecar schema (TDD)

The gate can't be trusted on today's three-shape sidecar, so canonicalize first.

- **Parser** (`tcw/store/fs.py` or a small `tcw/work/capabilities_sidecar.py`
  helper): `declared_capabilities(capabilities_obj) -> {"new": [...], "changed": [...]}`.
  - Accept a mapping with `new:` / `changed:` (canonical) and `added:` (read as
    `new:`, deprecated alias).
  - Values are strings; strip a trailing ` # comment` (space-hash); keep the
    token otherwise verbatim (a bare internal `#` stays, so it fails resolution
    downstream rather than being silently "fixed").
  - The `_tcw_parse_error` sentinel (`tcw/store/fs.py:1465`) → raise a typed
    `SidecarError` so the gate can block on it (fail-closed), distinct from
    "no declared deltas".
  - A list-form sidecar (reconcile's `{file,heading,...}` shape) → not a
    declaration source for the gate; return empty new/changed. (reconcile keeps
    its own reader; untouched.)
- **Validation** (`tcw/store/base.py` `WORK_SIDECARS` + the writer that enforces
  it): tighten `capabilities.yaml` from `yaml_mapping` to a keyed rule — top-level
  keys ⊆ {`new`, `changed`, `added`}, each value a list of strings. Find the
  enforcement point (`write_sidecar` / `validation` dispatch in the store editor,
  `tcw/store/fs.py:2012` neighborhood) and add the check there.

Tests (`tests/test_work.py` or a new `tests/test_capabilities_sidecar.py`):
canonical parse; `added:` alias; trailing-comment strip; parse-error → `SidecarError`;
list-form → empty; validation rejects non-list value + unknown key.

## Phase 2 — status/override helpers on the capabilities store (TDD)

Both mechanisms need "is this capability's status a local decision?" Add to
`FsCapabilitiesStore` (and declare the read-only shape on `CapabilitiesStore` if
it needs to be callable through the interface — it does, for litmus cleanliness):

- `status_is_local(cap) -> bool` — `True` for a local capability; for an inherited
  one, `True` iff an override matching `cap.id` / `f"{alias}/{cap.id}"`
  (`_override_index`, exactly as `_apply_override` keys) exists **and** that
  override's meta sets `Status`. Mirrors `tcw/store/fs.py:944,948-955`.
- `unreviewed_inherited() -> list[Capability]` — inherited caps where
  `not status_is_local(cap)`.

Tests (`tests/test_capabilities_federation.py`): bare inherited → unreviewed;
override setting Status → decided; override setting only a body/field → still
unreviewed; local cap → decided.

## Phase 3 — the DoD gate (TDD)

`tcw/work/cli.py` `_complete`. Open a capabilities store on the work node
(`FsCapabilitiesStore.open(st.node_root)` guarded by
`(st.node_root/"docs"/"capabilities").is_dir()` — mirror `_taxonomy_for`,
`tcw/capabilities/cli.py:29`). Insert the gate **after** `merge_worktree`
(so worktree-branch flips are visible) and before `st.complete(...)`:

- Read `item.capabilities` → `declared_capabilities(...)`; on `SidecarError`,
  refuse with the parse error (fail-closed).
- For each `new:` path: resolve via `caps.get(path)`; unresolved → collect
  "does not resolve"; `Missing` → collect "still Missing".
- For each `changed:` path: resolve only; unresolved → collect. No status check.
- If no caps store on the node → skip silently (a work-only node has nothing to
  reconcile).
- Any collected problems and not `--force` → print the per-capability report
  (path, status, both exits) and return 1; item stays `active`.

Tests (`tests/test_work.py`): new-still-Missing refuses; reconciled passes;
`--force` passes; unresolved refuses; changed-Missing passes; unparseable refuses;
no-sidecar unaffected; Omitted passes; **worktree flow** — flip on branch, gate
passes after merge-back (drive via the real `--worktree` path or a focused unit
that asserts ordering).

## Phase 4 — `tcw capabilities drift` (TDD)

`tcw/capabilities/cli.py`: new `drift` subcommand (`_drift`, subparser).

- Unreviewed inherited: `caps.unreviewed_inherited()`.
- Shipped-but-Missing: local `Missing` caps whose `Planning doc` resolves (via a
  work store opened on the same node, guarded like the gate) to a **completed**
  item. Degrade to silence if no work store.
- Print grouped report; exit non-zero iff any drift. Empty → exit 0.

Tests (`tests/test_capabilities.py` + federation): unreviewed listed;
override-with-Status clears it; local Missing → completed Planning doc flagged;
→ active Planning doc not; no work store → no error; clean node exit 0;
`check` still passes on an unreviewed-but-structurally-sound node.

## Phase 5 — documentation sync

- `skills/tcw-work/SKILL.md` — the complete gate now enforces reconciliation;
  the canonical `capabilities.yaml` schema.
- `skills/tcw-capabilities/SKILL.md` — `tcw capabilities drift`; the gate makes
  the ledger flip mandatory, not by-convention.
- `README.md` — the gate + `drift` in the capabilities/work sections.
- `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`.
- Run `skill-cefailures:documentation-sync` before reporting complete.

## Phase 6 — ledger flip (at completion)

- `tcw capabilities set capabilities/detect-capability-drift --status Supported`.
- `work/complete-a-work-item` stays `Supported` (behavior extended, not new).
- `tcw capabilities check` + `tcw validate` clean; and dogfood: run
  `tcw capabilities drift` on this repo — it should surface real drift here
  (this repo federates nothing, so expect only any local shipped-but-Missing).

## Touch points

| File | Phase |
|---|---|
| `tcw/store/fs.py` (sidecar parse, status_is_local, unreviewed_inherited) | 1, 2 |
| `tcw/store/base.py` (`WORK_SIDECARS` validation, `CapabilitiesStore` method decl, `SidecarError`) | 1, 2 |
| `tcw/work/cli.py` (`_complete` gate) | 3 |
| `tcw/capabilities/cli.py` (`_drift`) | 4 |
| `tests/test_capabilities_sidecar.py`/`test_work.py`/`test_capabilities*.py` | 1–4 |
| `skills/tcw-work/SKILL.md`, `skills/tcw-capabilities/SKILL.md`, `README.md`, changelog, release notes | 5 |

## Verification

```sh
pytest tests/ -q
tcw capabilities check && tcw validate
tcw capabilities drift            # dogfood on this repo
```

Plus end-to-end: a scratch node with a declared-but-unflipped capability must
fail `complete`, pass after `set`, and pass under `--force`; a scratch federation
must surface an unreviewed inherited capability in `drift`.

## Out of scope

Rewriting existing sidecars; a `--force-capabilities` scalpel; enforcing the
spec's `## Capability changes` prose section (the sidecar is the machine-readable
source); auto-fixing drift (the detector reports, it does not flip).
