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
- **The declared deltas already exist in a bounded, abstract form.** A work
  item's `capabilities.yaml` sidecar (`WORK_SIDECARS`, `tcw/store/base.py:351`)
  carries `new:` / `changed:` lists of capability paths (the work→capability
  back-pointer). `WorkItem.capabilities` already parses it
  (`tcw/store/fs.py:1460`). Legacy entries may carry a `#heading` suffix and a
  trailing comment — parsing must tolerate both (`path#heading` → `path`).
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

### Mechanism 1 — DoD gate teeth (fail closed, `--force` overrides)

At `tcw work complete`, after the existing blocker gate and before the status
move, when the item declares capabilities (its `capabilities.yaml` `new:` /
`changed:` lists, else the spec's `## Capability changes` section is out of scope
here — the sidecar is the machine-readable source), check each declared path
against the ledger:

- **`new:` capabilities** — reconciled iff current status is **not `Missing`**.
  A newly declared capability is seeded `Missing` at the planning gate; shipping
  it means a decided status (`Supported` / `Partial` / `Blocked` / `Omitted`).
  Still-`Missing` at completion is the exact drift vector #1.
- **`changed:` capabilities** — reconciled iff the capability **still resolves**
  (not dangling) and is not `Missing`. A `changed` entry that reads `Missing`
  after the work landed is the same smell. (Rationale: `changed` means the item
  altered the capability; a decided post-change status is required.)
- A declared path that **doesn't resolve at all** fails the gate as a dangling
  declaration (surfaces typos and renames).

On any failure, `complete` refuses with a per-capability report — same posture as
the worktree-merge-conflict and blocker gates — naming each unreconciled path and
its current status, and stating the two ways forward: reconcile it
(`tcw capabilities set <path> --status <S>`, now possible for inherited paths
after the preceding item) or `--force`. `--force` overrides, matching the blocker
gate. The item stays `active` on refusal.

This is deliberately a *status* check, not a diff-of-status check: it needs no
stored baseline, and its failure ("declared X still reads Missing") is precisely
the observed drift. A capability that legitimately ships `Missing` (deferred
within scope) is expressible: mark it `Omitted` ("we deliberately don't have
this"), or `--force` with the rationale in `outcome.md`.

### Mechanism 2 — distinguish unreviewed from decided

Give `Missing` its meaning back by separating an inherited capability the local
node **never ruled on** from one it **decided** stays `Missing`:

- An inherited capability (`origin != "local"`) with **no local override** is
  *unreviewed* — its status is the master's default, echoed, not a local
  decision.
- An inherited capability **with** a local override, or any local capability, is
  *decided*.

Surface this as a new read-only report, `tcw capabilities drift`, listing
unreviewed inherited capabilities (and, usefully, any local `Missing` with a
`Planning doc` pointer to a **completed** work item — declared, shipped, never
flipped: drift vector #1 after the fact). Exit non-zero when drift is found, zero
when clean, so it is CI-usable. Kept **out of `check`**: `check` is structural
validation that must stay green on a correct-but-unreviewed federation; drift is
advisory review state, a different question. (`check` gaining a drift section
would make a freshly-federated node fail structural validation, which is wrong.)

## Acceptance criteria

Mechanism 1:
- An item whose `capabilities.yaml` `new:` names a capability still reading
  `Missing` → `complete` refuses, names the path + status, exits non-zero, item
  stays `active`.
- Reconciling it (`set --status Supported`) then `complete` → succeeds.
- `--force` completes despite an unreconciled declaration.
- A declared path that doesn't resolve → refuses as dangling.
- An item with no `capabilities.yaml` and no declared deltas → unaffected
  (byte-identical to today's flow).
- An `Omitted` declared capability → passes the gate (decided).
- The gate runs after the blocker gate and before the worktree merge-back, so a
  refusal leaves no half-merged branch.

Mechanism 2:
- `tcw capabilities drift` lists an inherited capability with no local override
  as unreviewed; exits non-zero.
- Adding a local override (any `set` on it) removes it from the report.
- A local `Missing` whose `Planning doc` names a completed item is flagged.
- A fully-decided node → empty report, exit zero.
- `tcw capabilities check` is unchanged — drift never makes structural validation
  fail.

## Risks / dependencies

- **Depends on the preceding item** (inherited-path `set`, just completed): the
  gate tells authors to `set` an inherited capability to reconcile it — which was
  impossible before v0.11.4. Ordering was correct.
- **False-positive gate friction.** An item that legitimately ships a capability
  as `Missing` now needs `Omitted` or `--force`. Acceptable — that is the point
  (make the decision explicit) — but the refusal message must teach both exits so
  it doesn't read as a wall.
- **`changed:` semantics are the softest call.** Flagging a `changed` entry that
  reads `Missing` could annoy if a change legitimately left something unbuilt.
  Mitigated by `--force` + `Omitted`; revisit if it proves noisy.
- **Sidecar parse tolerance.** Legacy `path#heading` entries and comment lines
  must degrade cleanly (strip `#…`), never crash `complete`. A malformed sidecar
  should warn and (per fail-closed posture) block, not silently pass.
- Doc-sync triggers expected to fire: `README.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` (the complete gate),
  `skills/tcw-capabilities/SKILL.md` (the drift command + the reconciliation the
  gate now enforces).

## Related work

- `2026-07-15-capabilities-set-rejects-inherited-capability-paths-that-show-list-accept`
  (completed, v0.11.4) — made inherited reconciliation possible; this gate assumes it.
- `2026-06-19-hard-dod-gate-commit-range-enforced` (dropped stub) — its
  commit-range framing is explicitly superseded by the status-comparison gate here.
