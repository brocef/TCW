Parked on 2026-09-15 by 2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes (C4 of the tracker bridge epic), which the epic had given this job.

Read a Jira project's workflow definition (POST /rest/api/3/workflows with projectAndIssueTypes, measured answering in one call during the claim experiment) to decide, before any ticket exists, whether the configured claim transition can exclude a second claimant.

Prerequisite, from the epic's spec: settle with a non-admin API token whether this route is readable at all. The session that parked it had no Jira access.

Problems the epic named: it needs a project identifier no work.tracker key holds; it may need site-administrator permission; and tcw validate has no severity tier for it and must not call the network, because it is a pre hook on complete in this repository.

What C4 built instead: under strict mode, a claim is refused when the ticket, right after the claim, still offers the claim transition from its destination. That sees one account's view of the workflow only.

## Added 2026-09-24 — from the closeout of 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs

That epic was the place this item could have been resolved. Its plan said to
close it only if the optional claim-transition assertion covered what this item
was parked on. It does not, so this item stays open.

What shipped: `work.tracker.exclusive-claim-transition` (required under strict
mode). Every strict claim then checks, from the one ticket it has, that the
workflow does not offer that transition again from where it led. `import` and
`inbox accept` check `transitions.start` the same way. This is still one ticket's
view of the workflow, and it leaves one case unanswerable. A ticket the caller
already holds, sitting in the backlog status, is accepted by a strict `start`
without the check: what it offers from there says nothing about the active
status, and re-applying the transition would break the idempotent claim. Reading
the workflow definition is what would settle that case, so the requester accepted
the gap as this item's to close.
