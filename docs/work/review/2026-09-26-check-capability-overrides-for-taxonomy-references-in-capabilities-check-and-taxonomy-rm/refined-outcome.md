# Refined outcome — Check capability overrides for taxonomy references in capabilities check and taxonomy rm

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–6 met. Hands-on in a scratch graph (a
  child node extending a `base` ledger, a local taxonomy, an override `ov`):
  `tcw capabilities check` reports `ov: Feature → dangling ref 'nope'`,
  `ov: Subject → dangling ref 'ghost'` and `ov: Blocked by → dangling
  identifier 'missing-cap'`; `Subject: null` reports nothing; `tcw taxonomy rm
  zed` is refused naming `capability override ov (Subject)` and, for a
  Feature-kind term, `(Feature)`; once the override names another term, the
  removal succeeds.
- Full suite after the review fixes (started after `3a8b7c23`), from the item
  worktree with its private virtual environment: **4770 passed, 3 skipped**
  (exit 0). Two timing tests the verifier saw fail in a targeted run under a
  load average of 35 pass when rerun alone; neither touches this change.

## Accepted deviations from the spec

- Scope covers every reference an override sets (`Blocked by`, `Superseded
  by`, `Roles`, `When`), as the spec's own sweep said.
- Review fold-in: `check(identifier)` checks a selected capability's override
  references once (they were reported twice), and skips a selected upstream
  path with no local folder (it crashed; that crash predates this change). The
  spec's Design sentence on `check(identifier)` was corrected.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md`,
  changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed. Recorded, not filed: an override whose target does
  not resolve still has its references checked and still blocks `taxonomy rm`
  (a conservative choice; `check` reports the dead target).
