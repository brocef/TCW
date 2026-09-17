# Refined outcome: Fix the guide's taxonomy example and a stale README citation

## Decision

Accepted, unattended (`autonomous-work`); the reasoning is in `outcome.md`,
"Autonomous decisions".

## Evidence

- `tcw-verifier`: criteria 1-4 met at `c4652143`, including a before/after run of
  the guide's 24 example commands in a fresh project (4 refusals before, 0 after).
- After review fixes (`acd8e758`): the 24 commands re-run, 0 refusals; the work
  guide's `tags add bug cli tech-debt` → `tags rm tech-debt` →
  `new "Login crash" --tags bug,cli` → `list --tags bug,cli` all exit 0 (criterion 5).
- `pytest -q -x` at `8822ca20`: 3605 passed. Later commits change Markdown only.

## Closeout choices

- **Route:** committed directly on `main`; no branch to merge. Not pushed.
- **Documentation:** `docs/changelogs/upcoming.md` (Fixed + Internal). No other
  entry fired.
- **Capabilities:** nothing to reconcile — no capability delta was planned or shipped.
- **Version:** none cut; accumulates in `upcoming.md`.
- **GitHub issue:** none; the item came from an inbox entry.

## Deferred follow-ups

- None filed. `docs/guide/work.md:279` (`--blocks downstream-slug`) refuses when
  run, but it sits in a placeholder reference block and is not a runnable sequence.
