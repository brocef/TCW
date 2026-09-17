# Refined outcome: Fill the Codex gaps in the setup and stage skills, and give each skill one capability

## Decision

Accepted, unattended (`autonomous-work`); reasoning in `outcome.md`, "Autonomous
decisions".

## Evidence

- `tcw-verifier`: criteria 1-6 met — the install command ran against a scratch plugin
  root with no `tcw` or `pipx` on `PATH` (exit 0, silent); both `<plugin>` locations
  resolve; `work-stage` appears in `run-a-lifecycle-stage` only in its `validate`
  paragraph; the issue-closing rules live in one capability, linked from the other.
- `tcw capabilities check`: OK; skill tests 209 passed; full suite at `4c099f78`:
  3628 passed (criterion 7).

## Closeout choices

- **Route:** committed directly on `main`; nothing to merge. Not pushed.
- **Documentation:** changelog and release note.
- **Capabilities:** four `changed:` entries; all stay `Supported`.
- **Version:** none cut.
- **GitHub issue:** none.

## Deferred follow-ups

- `docs/work/inbox/2026-09-17-codex-s-sandbox-may-block-the-tcw-install-the-setup-skill-gives.md`
