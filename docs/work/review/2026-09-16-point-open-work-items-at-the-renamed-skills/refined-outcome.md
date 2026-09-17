# Refined outcome: Point open work items at the renamed skills

## Decision

Accepted, unattended (`autonomous-work`); reasoning in `outcome.md`, "Autonomous
decisions".

## Evidence

- `tcw-verifier`: criteria 1-4 met at `fc1cb4f4` (16 remaining matches equal the
  plan's leave list; 17 files, all under `docs/work/backlog/`; no slug,
  `tcw-config` or `tcw-cli` touched; `validate OK`).
- After the wildcard fixes: the intake's search still returns the same 16 lines;
  the wildcard search returns only the removed-skill list on the refine item's
  line 78; `tcw validate` → `validate OK`.

## Closeout choices

- **Route:** committed directly on `main`; nothing to merge. Not pushed.
- **Documentation:** no entry fires — only `docs/work/` prose changed; no changelog
  line.
- **Capabilities:** nothing to reconcile.
- **Version:** none cut.
- **GitHub issue:** none.

## Deferred follow-ups

- Not filed, by the spec's scope: staleness other than the rename in open items —
  `…record-a-time-of-day…/plan.md:248` cites text no longer in
  `skills/work/references/procedures/search.md`, and line numbers such as
  `hooks.md:83` have drifted. The requester declined a guard against recurrence.
