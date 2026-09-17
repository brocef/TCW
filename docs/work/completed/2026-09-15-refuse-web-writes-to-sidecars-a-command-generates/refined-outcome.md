# Refined outcome: Refuse web writes to sidecars a command generates

## Decision

Accepted, unattended (`autonomous-work`); reasoning in `outcome.md`, "Autonomous
decisions".

## Evidence

- `tcw-verifier`: criteria 1-5 met — targeted tests (13 sidecar, strict web test,
  39 binding tests) and a hands-on `TcwServer` + curl run: `rollup.md` and
  `tracker.yaml` 409 naming their commands with folder hashes unchanged,
  `capabilities.yaml` 200, discovery flags true/true/false, no strict branch left.
- Full suite at `79bef735`: 3625 passed (criterion 6).

## Closeout choices

- **Route:** committed directly on `main`; nothing to merge. Not pushed.
- **Documentation:** changelog (Fixed), release note, `skills/work/references/commands.md`.
- **Capabilities:** `web/editing` and `work/require-tracker-backed-work` updated;
  both stay `Supported`.
- **Version:** none cut.
- **GitHub issue:** none.

## Deferred follow-ups

- `docs/work/inbox/2026-09-17-the-web-client-shows-any-409-as-a-stale-write.md`
