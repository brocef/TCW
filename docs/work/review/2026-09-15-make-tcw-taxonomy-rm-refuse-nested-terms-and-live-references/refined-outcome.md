# Refined outcome: Make tcw taxonomy rm refuse nested terms and live references

## Decision

Accepted, unattended (`autonomous-work`); reasoning in `outcome.md`, "Autonomous
decisions".

## Evidence

- `tcw-verifier`: criteria 1-7 met — 116 targeted tests (the case-variant test ran,
  not skipped) and its own CLI runs of every refusal and removal, plus the three
  review fixes.
- Full suite at `4c099f78`: 3628 passed (criterion 8).

## Closeout choices

- **Route:** committed directly on `main`; nothing to merge. Not pushed.
- **Documentation:** README, `skills/taxonomy/SKILL.md`, CLI scenario 08, changelog,
  release note (flagged as a behaviour change of a shipped command).
- **Capabilities:** `taxonomy/remove-a-local-term` updated; stays `Supported`.
- **Version:** none cut.
- **GitHub issue:** none.

## Deferred follow-ups

- `docs/work/inbox/2026-09-17-tcw-taxonomy-rm-does-not-check-capabilities-that-name-the-term.md`
- `docs/work/inbox/2026-09-17-tcw-taxonomy-rm-reports-removed-while-an-unstaged-child-keeps-the-term-listed.md`
