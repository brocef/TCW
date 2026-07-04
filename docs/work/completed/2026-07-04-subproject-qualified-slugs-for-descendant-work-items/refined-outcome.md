# Refined outcome — Subproject-qualified slugs for descendant work items

## Verification decision

User approved closeout and selected a **minor** version bump. No functional tweaks
requested after the initial implementation; the result was accepted as shipped.

## Refinements after initial implementation

None to the runtime behavior. The only mid-implementation adjustment was the
backend serve-response re-stamping (echo the qualified slug in detail/action/PATCH
responses) so the unchanged web UI keeps addressing descendant items — recorded as
a deviation in `outcome.md` and covered by serve tests.

## Final verification evidence

- `pytest -q` → **466 passed** (30 new: resolver 14, CLI +10, serve 6).
- Manual CLI smoke: qualified `show`/`path` resolve to the descendant; bare
  descendant slug from the root reports "no such work item".

## Capability reconciliation

Ledger flipped: `cli/host-multiple-projects-in-one-repo` body extended to describe
qualified-slug addressing (commit `a615f67`); `tcw capabilities check` clean.
`work#view-the-board` and `web#*` remain `Supported` (scope broadened, not status).

## Closeout choices

- **Completion route:** committed directly to `main` (this repo's dogfooding
  convention; no PR).
- **Version:** minor bump (0.9.0 → 0.10.0) via `scripts/cut_version.py`.
- **Documentation:** README, `tcw-work` skill, changelog, and release notes updated
  (commit `71d6c41`).
- **Deferred follow-up (NOT yet a TCW item):** optional web-UI node-grouping/label
  polish for the descendant board. Functional without it; create a backlog item
  only if desired.
