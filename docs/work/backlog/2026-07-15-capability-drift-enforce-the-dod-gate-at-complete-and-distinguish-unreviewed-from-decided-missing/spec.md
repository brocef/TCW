# Spec — enforce the DoD gate at complete + distinguish unreviewed from decided Missing

Source: https://github.com/brocef/TCW/issues/4.

Scope confirmed with the user: **both** mechanisms; the DoD gate **fails closed
with `--force` override**.

## Capability changes

- **Changed — `work/complete-a-work-item`** (`Supported`): `complete` gains a
  capabilities-reconciliation gate. Recorded in this item's `capabilities.yaml`.
- **New — `capabilities/detect-capability-drift`** (`cap-c38e6d`, seeded
  `Missing`): surface capabilities that drifted from ground truth — declared-but-
  unreconciled, and inherited-but-unreviewed. Flips `Supported` at completion.

Contradiction check: `tcw capabilities check` clean; neither change conflicts
with a `Supported` entry. Mechanism 1 extends the existing complete capability
rather than replacing it.

## Problem

`Missing` is overloaded: "deliberately not built" and "built, nobody flipped it"
are indistinguishable without reading the code, and `tcw capabilities check`
reports `capabilities OK` in both states. Two independent drift vectors produce
this:

1. **Deferred at completion.** An item ships, `outcome.md` says the flips are
   deferred, the item completes `--resolution done`, nothing flips. The DoD
   "capabilities reconciled" line is self-attested: `complete()`
   (`tcw/store/base.py:772`) just records `dod_ack=checklist` wholesale — nothing
   verifies it. This repo hit exactly this on the item completed immediately
   before this one; the reporter's workspace has 10 such capabilities across 5
   nodes.
2. **Inheritance default.** A capability added to a federated master lands on
   every consumer as `Missing` with no signal a new entry appeared; a consumer
   that already shipped it never overrides, so its `Missing` is the master's
   default, not a local decision.

Downstream artifacts that quote gap counts then go wrong silently — one epic was
scoped around a stale number.

## Current-state findings

- **DoD acknowledgment is wholesale and unverified.** `_complete`
  (`tcw/work/cli.py:417`) prints the checklist, requires `--confirm`, then calls
  `st.complete(..., dod_ack=checklist)`. The store records the list as
  acknowledged; there is no per-item verification. "capabilities reconciled" is a
  string, not a check.
- **The declared deltas exist but the schema is not canonical.** A work item's
  `capabilities.yaml` sidecar (`WORK_SIDECARS`, `tcw/store/base.py:351`) is meant
  to carry the work→capability back-pointer, and `WorkItem.capabilities` parses it
  (`tcw/store/fs.py:1460`). But live items use three shapes — `new:`/`changed:`,
  `added:`/`changed:`, and (in `reconcile`'s reader, `tcw/work/recursion.py:41`) a
  top-level list of `{file, heading, from, to}` — and `WORK_SIDECARS` validation
  is only `yaml_mapping`. Legacy `#` entries are `namespace#slug`, not
  `path#anchor` (`work#open-a-work-item` → today's `work/open-a-work-item`), so a
  naive `#`-strip is wrong. The gate depends on this, so **the schema is pinned
  first** (see "The sidecar schema the gate reads").
- **The work CLI can reach the capabilities store.** `_complete` resolves the
  node via `find_node("work")`; the same node hosts `docs/capabilities/`, so the
  CLI can open `FsCapabilitiesStore` alongside `FsWorkStore` — exactly how
  `_check` pairs a taxonomy store (`tcw/capabilities/cli.py:159`,
  `_taxonomy_for`). Enforcement belongs in the CLI orchestration layer, **not**
  in `WorkStore.complete()` (which has no capabilities handle and must not grow
  one — the two axes link by loose pointers, never a hard store dependency).
- **`check` today** (`tcw/store/fs.py`, `FsCapabilitiesStore.check`) validates
  structure only: ids, vocabulary, override targets, cycles, attachments. It does
  not compare status against any notion of ground truth, and inherited entries
  are folded into `list_all` with the master's status verbatim.

## Abstraction litmus test

> Could a non-filesystem store implement each operation?

- **Mechanism 1 (gate).** *Compare each declared capability's current status
  against a "reconciled" predicate.* Yes — `WorkStore` reads its sidecar,
  `CapabilitiesStore` reads status; the CLI orchestrates. Both operations are
  already in the abstract vocabulary. This is the litmus-clean framing the
  request prefers over the old phase-6 "declared files appear in the commit
  range" hook — a commit-range check is filesystem-flavored (a Jira-backed store
  has no commit range) and is **rejected** here.
- **Mechanism 2 (detector).** *Flag inherited capabilities lacking a local
  override.* Yes — "is this capability inherited" (`origin != "local"`) and "does
  a local override exist" (`_override_index`) are both abstract. The FS adapter
  realizes them; a remote adapter answers the same two questions its own way.

## Proposed behavior

### The sidecar schema the gate reads (pin it first)

Spec review found the `capabilities.yaml` schema is **not** canonical today: live
items use `new:`, `added:`, and (in `reconcile`'s reader, `tcw/work/recursion.py:41`)
a top-level list of `{file, heading, from, to}` mappings — three shapes, none
authoritative, and `WORK_SIDECARS` validation is only `yaml_mapping` (dict-or-not).
Building the gate on an assumed `new:`/`changed:` shape would let an `added:`-keyed
sidecar declare nothing and sail through — the drift it's meant to stop.

So this item **pins the canonical sidecar schema** before adding the gate:

```yaml
# capabilities.yaml — work→capability back-pointers.
new:            # capabilities this item declares (seeded Missing at planning)
  - namespace/path
changed:        # existing capabilities this item alters
  - namespace/path
```

- Values are **current path-addressed capability paths** (`namespace/path`), the
  form `get()` resolves. No `#` — the legacy `namespace#slug` / `path#heading`
  forms are **not** parsed (they map ambiguously: `work#open-a-work-item` →
  `work/open-a-work-item` resolves, but `web/editing#edit-…` → `web/editing/edit-…`
  does not). Every legacy-form sidecar in the repo is on an **already-completed**
  item, so none re-enters the gate; canonical is the only go-forward shape.
- A trailing ` # comment` (space-hash) is stripped; a bare `#` inside a token is
  not, and makes the token fail to resolve (caught below).
- `added:` is accepted as a deprecated alias of `new:` for reading (one line, and
  it exists in the repo), but the skill/docs teach `new:`/`changed:` only.
- Strengthen `WORK_SIDECARS["capabilities.yaml"]` validation from `yaml_mapping`
  to a keyed check (known top-level keys, list-of-strings values) so a malformed
  or wrong-shape sidecar is caught at write time, not silently at the gate.

### Mechanism 1 — DoD gate teeth (fail closed, `--force` overrides)

`tcw work complete` gains a capabilities gate, enforced in the CLI `_complete`
(orchestrating an `FsCapabilitiesStore` opened on the same `node_root` as the work
store — the loose-pointer boundary stays intact; `WorkStore.complete` gains no
capabilities handle). Ordering, corrected from the review:

1. existing blocker / epic-children gate (unchanged);
2. `--confirm` checklist (unchanged);
3. **worktree merge-back** — for a `--worktree` item the reconciling `set` ran on
   the work branch, and the primary checkout the store reads (`node_root`) sees
   those flips **only after** `merge_worktree`. So the caps gate runs **after**
   merge-back, reading post-merge status. A gate failure here leaves a fully
   merged branch and the item still `active` — re-runnable, not half-applied
   (there is no "half-merged" state: `merge_worktree` already fails closed on a
   conflict before this point);
4. **the caps gate** (new);
5. status move + worktree teardown.

The gate reads the item's declared deltas (canonical sidecar above) and checks
each against the ledger:

- **`new:` (and `added:`) capabilities** — reconciled iff current status is **not
  `Missing`**. Seeded `Missing` at planning; shipping means a decided status
  (`Supported` / `Partial` / `Blocked` / `Omitted`). Still-`Missing` is drift
  vector #1.
- **`changed:` capabilities** — reconciled iff the capability **still resolves**.
  No status requirement: `changed` routinely means a body / `Feature` / wording
  edit that legitimately leaves status untouched (the repo's history shows this),
  so requiring non-`Missing` here would false-fail ordinary doc edits. Only a
  *dangling* `changed` entry fails — it catches a renamed/deleted target.
- **Any declared path that doesn't resolve** fails as an unresolved declaration
  ("declared capability '<x>' does not resolve — fix the path or the sidecar"),
  which also catches a stray legacy `#` form. Not labeled "dangling" (which
  implies a deleted target).
- **Unparseable sidecar** (the `_tcw_parse_error` sentinel `_item_from_dir`
  produces on bad YAML, `tcw/store/fs.py:1465`) → the gate **blocks** with the
  parse error, honoring fail-closed. It must special-case the sentinel rather
  than see "no delta keys" and pass.

On failure `complete` refuses with a per-capability report — same posture as the
blocker and worktree-conflict gates — naming each path and its current status, and
the two exits: reconcile (`tcw capabilities set <path> --status <S>`, now possible
for inherited paths as of v0.11.4) or `--force`. The item stays `active`.

A status check, not a diff-of-status check: no stored baseline, and its failure
("declared X still reads Missing") is exactly the observed drift. Honest scope:
the gate catches *forgot to flip* (vector #1), **not** *flipped without building*
— an author can still `set --status Supported` without doing the work. It moves
self-attestation from a checklist string down to a per-capability field; it does
not eliminate it. A capability legitimately deferred-in-scope is expressible via
`--force` with the rationale in `outcome.md` (the honest path); `Omitted` fits
only genuine "we deliberately don't have this", not "not yet".

**`--force` is coarse** (deliberately): the one flag bypasses blockers, open epic
children, and now the caps gate together — no per-gate scalpel. Noted, not fixed;
a `--force-capabilities` split is out of scope unless it proves needed.

### Mechanism 2 — distinguish unreviewed from decided

Give `Missing` its meaning back by separating an inherited capability the local
node **never ruled on its status** from one it **decided**:

- *Unreviewed* — an inherited capability whose **status is inherited, not locally
  set**. Detection must use the override index, not `origin`: an override keeps
  `origin=<alias>` (`tcw/store/fs.py:967`), so `origin != "local"` cannot tell an
  overridden entry from a bare inherited one. Match the override exactly as
  `_apply_override` does — `_override_index()[base.id]` or `[f"{alias}/{base.id}"]`
  — **and** require the override to actually set `Status` (an override that edits
  only a body/field re-inherits the master's `Status`, so its status is still not
  a local decision, `tcw/store/fs.py:948-955`).
- *Decided* — a local capability, or an inherited one whose override sets `Status`.

Surface as a new read-only `tcw capabilities drift`: lists unreviewed inherited
capabilities; exits non-zero when any drift is found, zero when clean (CI-usable).
Kept **out of `check`** — `check` is structural validation that must stay green on
a correct-but-unreviewed federation; a freshly-federated node is not *broken*.

It **also** flags any **local `Missing` whose `Planning doc` points to a completed
work item** — declared, shipped, never flipped: drift vector #1 after the fact,
and the exact shape of the reporter's 10 stuck capabilities. This is the one place
the capabilities axis reads the **work** store, so state the litmus explicitly:
`Planning doc` is an existing capability→work forward pointer (`CAP_FIELDS`,
`tcw/store/base.py:192`); resolving it **read-only** to check the target's status
is store-implementable (a remote adapter resolves the same pointer its own way)
and creates **no** hard dependency — if no work store is present the check
degrades to silence, never errors. A write coupling would fail the litmus; a
read-only pointer follow does not.

## Acceptance criteria

Sidecar schema:
- A `capabilities.yaml` whose values are canonical `namespace/path` strings is
  read correctly by the gate; a trailing ` # comment` is ignored.
- An `added:`-keyed sidecar is read as `new:` (deprecated alias).
- Strengthened `WORK_SIDECARS` validation rejects a non-list value or unknown
  top-level key at write time.

Mechanism 1:
- An item whose `new:` names a capability still reading `Missing` → `complete`
  refuses, names the path + status, exits non-zero, item stays `active`.
- Reconciling it (`set --status Supported`) then `complete` → succeeds.
- `--force` completes despite an unreconciled declaration.
- A `new:`/`changed:` path that doesn't resolve → refuses as unresolved (message
  says "does not resolve", not "dangling").
- A `changed:` capability still reading `Missing` but resolving → **passes** (no
  status requirement on `changed`).
- An unparseable `capabilities.yaml` → refuses with the parse error (fail-closed),
  does **not** silently pass.
- An item with no `capabilities.yaml` and no declared deltas → unaffected
  (byte-identical to today's flow).
- An `Omitted` `new:` capability → passes the gate (decided).
- **Worktree flow:** an item started `--worktree` whose reconciling `set` ran on
  the branch → the gate reads the flipped status **after** merge-back and passes;
  it does not false-fail on pre-merge primary-tree status.

Mechanism 2:
- `tcw capabilities drift` lists a bare inherited capability (no override) as
  unreviewed; exits non-zero.
- An override that sets `Status` removes it from the report; an override editing
  only a body/field does **not** (status still inherited).
- A local `Missing` whose `Planning doc` names a completed item is flagged; one
  pointing to a still-active item is not.
- With no work store resolvable, the `Planning doc` check degrades to silence
  (no error).
- A fully-decided node → empty report, exit zero.
- `tcw capabilities check` is unchanged — drift never makes structural validation
  fail.

## Risks / dependencies

- **Depends on the preceding item** (inherited-path `set`, just completed): the
  gate tells authors to `set` an inherited capability to reconcile it — which was
  impossible before v0.11.4. Ordering was correct.
- **False-positive gate friction on `new:`.** An item that legitimately ships a
  `new:` capability unbuilt now needs `--force`. Acceptable — that is the point —
  but the refusal message must teach both exits so it doesn't read as a wall.
  (`changed:` no longer carries a status requirement, so ordinary doc/wording
  edits don't trip it — see the corrected rule above.)
- **Schema migration is documentation-only.** Pinning the canonical sidecar shape
  does not rewrite existing sidecars (all on completed items); `added:` stays
  readable. No data migration; the skill/docs teach the canonical form going
  forward.
- Doc-sync triggers expected to fire: `README.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` (the complete gate),
  `skills/tcw-capabilities/SKILL.md` (the drift command + the reconciliation the
  gate now enforces).

## Related work

- `2026-07-15-capabilities-set-rejects-inherited-capability-paths-that-show-list-accept`
  (completed, v0.11.4) — made inherited reconciliation possible; this gate assumes it.
- `2026-06-19-hard-dod-gate-commit-range-enforced` (dropped stub) — its
  commit-range framing is explicitly superseded by the status-comparison gate here.
