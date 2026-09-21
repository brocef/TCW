# Let tracker sync bring a ticket forward from a pre-backlog status such as Triage

A Jira ticket that already exists in a status before the backlog, such as `Triage`,
cannot be brought into step with its work item. `tcw work tracker link <slug> <KEY>
--sync-status` claims it, then refuses to move it: "claimed PRPI-147, but it is in
'Triage', not 'In Progress', so it was not brought forward from there. Run `tcw work
tracker sync <slug>` once that is resolved." `sync` cannot move it either. Link and
sync treat Triage as a conflict, when it is a known earlier status that the workflow
has a configured way out of.

The refusal comes from `tcw/tracker/sync.py` (around line 631): once a claim lands
on a status that isn't mapped in `work.tracker.statuses`, nothing moves on from it.

## What happened

In proposit-app, the reporter created Jira tickets, which land in Triage, and linked
them to active items. To get link and sync working, they had to run the project's
`Accept` transition (id 11) by hand through the Jira API on all 22 tickets first.

2.5.0's `tracker create` avoids this for tickets TCW creates, because it places them
in `work.tracker.statuses.backlog`. What remains is a ticket that already exists in
Triage.

## What is wanted (reporter's suggestion)

A `work.tracker.statuses.triage` entry, or reuse of the claim transition, so that
sync can walk Triage → backlog → active.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app on tcw CLI 2.5.0
(Jira project PRPI). The requester asked for it to be tracked at high priority.

## References

- `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs` (active epic)
  already notes `TCW-1` in Triage offering only `Accept` and `Cancel`, for
  `inbox accept`. Its child `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`
  rewrites the claim-within-delivery path this refusal comes from, so the design here
  should fit that child's result.
- GitHub #40: letting `work.tracker` name the transition for a status move; a
  configured way out of Triage would be a named transition.
- `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`:
  checking a new status key against the real workflow.
