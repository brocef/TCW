# Point open work items at the renamed skills

## Desired outcome

No open work item tells whoever picks it up to edit, read or declare something
under an old `tcw-…` skill or capability name that no longer exists.

## Context

Found while reviewing PR #46, which dropped the `tcw-` prefix from every shipped
skill and agent name (`skills/tcw-work` → `skills/work`, and so on). That
change's spec deliberately left everything under `docs/work/` alone, because
those documents record what things were called when they were written.

That reasoning fits finished items. It fits open ones less well: 22 files across
the backlog still name an old skill, and some are instructions rather than
record. Two examples:

- `docs/work/backlog/2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title/plan.md`
  and `2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes/plan.md`
  name `skills/tcw-work/references/commands.md` and
  `skills/tcw-configure/references/<document>.md` as files to edit.
- `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root/intake.md`
  says to declare `skills/tcw-work` under `changed:` in `capabilities.yaml`.
  That capability path is now `skills/work`.

To list them all:

```sh
git grep -nE '(^|[^A-Za-z0-9_-])tcw-(work-stage|work-create|work|taxonomy|capabilities|setup|configure|post-mortem|commands-[a-z-]+|extras-[a-z-]+|backlog-auditor|verifier)([^A-Za-z0-9_-]|$)' -- docs/work/backlog docs/work/active docs/work/blocked docs/work/review
```

Decide per file whether the old name is an instruction (rewrite it, matching
whole names only, never `tcw-config` or `tcw-cli`) or a quoted record of what
happened (leave it). A backlog audit could do this as part of its normal pass.
