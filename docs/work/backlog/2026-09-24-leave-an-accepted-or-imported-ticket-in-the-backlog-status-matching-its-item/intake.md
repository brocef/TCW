# Leave an accepted or imported ticket in the backlog status, matching its item

`tcw work inbox accept <KEY>` and `tcw work tracker import <KEY>` claim the ticket
through `work.tracker.transitions.start`, which on a typical workflow lands it in
the active status (In Progress). The item they create is a **backlog** item —
`docs/guide/jira.md` says so on purpose: "importing is not starting". The ticket
and the item therefore disagree from the moment the item exists, and nothing
brings them back together: `tcw work tracker sync <slug>` reports the item as
"current", because no sync record is owed.

The ticket should end up in the status `work.tracker.statuses` maps the item's
status to — the backlog status — while still being claimed (assigned) by the
person who accepted it.

## Origin

Observed on 2026-09-24 while accepting TCW-1 during the backlog cleanup: the
ticket went Triage → To Do (pre-backlog `Accept`) → In Progress (`Start`), and
the item landed in `backlog`. It had to be moved back by hand; the TCW Jira
workflow had no way back to To Do until a `Stop` transition (In Progress / In
Review → To Do) was added the same day. Bug.

## References

- `tcw/tracker/intake.py` `claim` / `_claim_from` — the claim that applies
  `transitions.start`, then assigns only after the transition applied (the
  ordering that keeps two claimants apart on an exclusive workflow).
- `docs/guide/jira.md` "What `import` creates" and the strict-mode table row for
  `tcw work tracker import` — strict mode currently *requires* the ticket to be in
  `statuses.active` after the claim; the fix must say how strict mode is affected.
- `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  — related: how exclusivity is judged from the workflow.
- `2026-09-22-refuse-an-unconfigured-start-before-the-ticket-leaves-triage` —
  related: same claim path, different defect.

No blockers.
