# Refined outcome

## Verification decision

Approved for closeout by the user. Resolution: **done**. Landed on `main`.
**Rolled into v0.11.4** (not a fresh version) — the release was never pushed, so
both this item and the inherited-`set` fix ship as one v0.11.4. Push after
completion.

## Refinements after the initial implementation

An independent `targeted-code-reviewer` pass (own read + a local `bllm` pass)
judged both mechanisms solid and well-tested, and found one real defect plus two
minor items — all addressed in commit `91fcf6b`:

1. **Pre-merge declaration snapshot (MEDIUM, fixed).** The gate read capability
   *status* from the merged primary tree but the *declared-paths list* from the
   pre-merge `item` snapshot. A `new:` capability declared **on the worktree
   branch** and left `Missing` would slip through — the exact drift the gate
   exists to catch. The original worktree test only covered a flip on the primary
   branch, so it missed this. Fixed by re-fetching the item after
   `merge_worktree`; pinned by `test_complete_gate_catches_declaration_added_on_branch`
   (fails without the fix).
2. **`new:`/`added:` double-count (cosmetic, fixed).** A path in both lists could
   emit doubled problem lines; added a dedup.
3. **Alias-qualified override key (coverage gap, closed).** `unreviewed_inherited`
   was only tested with the bare-id override form; added `shared/cap-…` coverage.

The review explicitly **cleared** the litmus boundary (no hard cross-axis store
coupling; `WorkStore.complete` untouched; the `drift` work-store read degrades to
silence), subproject-qualified completion (resolves the right node's
capabilities), the override keying (matches `_apply_override` exactly), and the
Omitted/Missing/changed-only/no-sidecar cases. It also caught that the local
reviewers' "narrow the except clause" suggestion would *introduce* a crash
(`MultipleMatch` is not a `RefError`), so that broad catch was kept by design.

## Key decisions

- **Two spec judgment calls confirmed** (user did not redirect): `changed:`
  entries are checked only for resolution, not status (routine doc/wording edits
  shouldn't trip the gate); `tcw capabilities drift`'s `Planning doc` scan reads
  the work store read-only and degrades to silence (litmus-clean).
- **Version:** rolled into v0.11.4 per the user.

## Final verification evidence

- **Full suite: 604 passed** (`python -m pytest tests/ -q`), no regressions, +37
  over the pre-item 567 across four test files.
- Dogfood: `tcw capabilities drift` on this repo → `no capability drift`, exit 0.
- `tcw validate` + `tcw capabilities check` clean, including after the ledger flip.
- Self-hosting proof: completing this item passes through its **own** new gate —
  its `capabilities.yaml` declares `capabilities/detect-capability-drift` (now
  `Supported`) and `work/complete-a-work-item` (resolves), so the gate lets it
  complete.

## Capabilities reconciled (ledger flip)

- `capabilities/detect-capability-drift` `Missing` → `Supported` (commit `9142e21`).
- `work/complete-a-work-item` stays `Supported` (behavior extended, not new).

## Closeout choices

- Resolution `done`, on `main`, no PR.
- Documentation sync: both skills, README, changelog, release notes updated.
- Version: rolled into v0.11.4; changelog/release-note entries consolidated into
  the `v0.11.4.md` working files; tag moved to include this item; then pushed.
- Follow-ups noted in `outcome.md` (validate `drift` against the reporter's real
  5-node workspace) — not filed as items unless the user asks.
