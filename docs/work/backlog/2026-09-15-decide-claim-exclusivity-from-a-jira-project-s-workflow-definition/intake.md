Parked on 2026-09-15 by 2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes (C4 of the tracker bridge epic), which the epic had given this job.

Read a Jira project's workflow definition (POST /rest/api/3/workflows with projectAndIssueTypes, measured answering in one call during the claim experiment) to decide, before any ticket exists, whether the configured claim transition can exclude a second claimant.

Prerequisite, from the epic's spec: settle with a non-admin API token whether this route is readable at all. The session that parked it had no Jira access.

Problems the epic named: it needs a project identifier no work.tracker key holds; it may need site-administrator permission; and tcw validate has no severity tier for it and must not call the network, because it is a pre hook on complete in this repository.

What C4 built instead: under strict mode, a claim is refused when the ticket, right after the claim, still offers the claim transition from its destination. That sees one account's view of the workflow only.
