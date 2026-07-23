# Refined outcome — Cross-node locator fix

## Verification decision

Approved for closeout by the user (2026-07-23). Verification evidence: full suite
**700 passed**, `tcw validate` clean on this repo, and the issue #7 reproduction
verified end-to-end from a throwaway reciprocal two-node graph (details in
`outcome.md`).

## Refinements after initial implementation

The plan deferred one pre-existing defect (phase 5): `resolve_tcw_ref` returned a
bare SPA key for the `tcw://W/<proj>/<slug>` spelling and bypassed the viewer
hosting gate, so a cross-node link resolved `ok` and then dead-ended in the web
viewer. **At the user's direction it was fixed here rather than deferred.**

The fix separates ref resolution (validate's question — now all `ok` answers,
with the owning project reported in `ResolveResult.project`) from viewer hosting
(serve's question — moved to `/api/resolve`'s `_hosted_projects()` gate). An
upward link now resolves and validates, and renders inert rather than dead in a
sub-project's viewer. Full detail and end-to-end evidence in `outcome.md`.

Web client TypeScript tests were not run — this checkout lacks web build tooling.
The `/api/resolve` JSON contract is unchanged (`project` is server-internal), so
no client test is affected, but this was explicitly not executed.

## Deferred work

- **Not filed as a backlog item** (the plan's phase-5 recommendation) because the
  SPA dead-end it described was fixed in-scope instead.
- One design-nicety noted, not filed: `parse_tcw_uri`'s first-bare-axis-wins rule
  makes the two work-ref spellings parse differently; documenting one canonical
  spelling would prevent the confusion recurring. Not a bug.

## Closeout choices

- **Resolution:** done. Closes GitHub issue #7.
- **Version:** patch bump (user decision), cut together with the blocker-refs fix.
- **Documentation:** README locator section, `tcw-work` skill quick-reference
  rows, `cross-node-epic.md` (epic back-link + viewer caveat), changelog, and
  release notes all updated; documentation-sync skill run.
- **Local review:** `bllm-review-many --models fast` run on the spec and both
  implementation diffs; findings dismissed with reasons in `outcome.md` (the one
  genuine edge — self-qualified refs — was verified correct).
