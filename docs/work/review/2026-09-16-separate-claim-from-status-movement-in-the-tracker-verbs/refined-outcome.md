# Refined outcome — separate claim from status movement in the tracker verbs

## Decision

**Accepted** by the requester on 2026-09-24.

## What the epic delivered

The tracker surface is split into verbs that each do one thing. Claiming a ticket
asserts ownership (assign, then read back) and moves nothing. Status movement is
`sync`'s job, and the lifecycle moves are built from the two. The children, all
completed:

| Child | What it did |
| --- | --- |
| `2026-09-16-make-claim-and-release-assert-ownership-without-moving-a-ticket` (C1) | `tracker claim` and `tracker release`; the optional `exclusive-claim-transition` |
| `2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item` (C2) | `sync` reconciles in both directions; the item is truth |
| `2026-09-16-retire-the-claim-transition-key-into-a-named-start-transition` (C3) | `transitions.claim` becomes `transitions.start` |
| `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync` (C4) | lifecycle moves built from claim and sync; `--sync-status` retired |
| `2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode` | strict mode requires `exclusive-claim-transition` |
| `2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move` | `transitions.start` optional |
| `2026-09-22-give-a-recordless-sync-a-move-and-let-strict-mode-work-without-transitions-start` | four defects the combined reviews found, including the exclusivity regression |

## Evidence

- **Criteria 1–12.** An independent verifier checked each against `main`: all met,
  with criterion 7 amended (below). Criteria 1–4 and 9–12 are held by tests that
  were run for this verify. Criteria 5–8 are held by tests and by the live-Jira
  walkthrough (`walkthrough.md`).
- **The six problems the epic existed to remove are no longer reachable** in their
  original form: GitHub #41 and #42, `start` moving a ticket backwards, strict
  exclusivity never asked for a held ticket, exclusivity needing the workflow
  definition, and claim state inside the sync record. Two residues are recorded
  below.
- **Full suite:** 4462 passed, 3 skipped, on `ca6f435b`. Only work-tracking files
  have changed since, which the verifier confirmed with `git diff --name-status`.
- **Live Jira** (2026-09-24, TCW project, tickets TCW-65 and TCW-66): criteria 5, 6,
  7 (as amended) and 8 hold, and nothing disagreed with the fake tracker.

## Decisions taken at verify

Folded in from `requester-decisions.md` (answered 2026-09-23), which this replaces:

- **Risk 2, "the item is truth":** the rule always applies. `sync` moving a ticket
  back to match its item is correct behavior, not a case needing a carve-out.
  Whether a `sync` that delivers a resolution over another account's ticket should
  say so on the way past was left as a separate question about output.
- **The live-Jira walkthrough** was required before shipping, and it ran (above).

Taken on 2026-09-24:

- **Criterion 7 amended** to "link, claim, sync". The design keeps `link` from
  taking the ticket, so a bare `sync` holds a ticket linked without its status and
  names `tracker claim`. The original wording predates that design.
- On the last child: `import` and `inbox accept` check `transitions.start` for
  exclusivity as well as `exclusive-claim-transition`, and a held ticket still in
  the backlog status is accepted unchecked. Both are recorded in that child's
  refined outcome.

## Known limits, stated rather than fixed

- A ticket bound with `--part` is never moved back by `sync`; it is reported as
  conflicting, because TCW cannot tell a sibling part's hold from a hand move.
  Criterion 8 therefore does not apply to part bindings. Lasting evidence of a hold
  is still `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`.
- The race in criterion 3 narrows but does not close without
  `exclusive-claim-transition`, as the spec said. Real two-account concurrency was
  not exercised against Jira; the fake tracker proves the logic.

## Closeout

In the plan's order:

1. **Subsumed items.**
   - `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery` stays
     open. Its §1 and §3 moved into this epic and are resolved here, and what is
     left (§2, whether each catch-up walk step lands where it aimed) is independent.
   - `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
     stays open, with a note explaining why (`5181494e`): it is what would settle
     the held-ticket-in-backlog case.
2. **Follow-up filed** during the last child's verify:
   `2026-09-24-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list`.
3. **Release:** 2.6.0 (minor), decided by the requester. The strict-mode breaking
   changes are opt-in and surface as a validation error that names what to set.
4. **GitHub #41 and #42 are deferred** until 2.6.0 is cut, pushed and live on
   PyPI, as this repository's CLAUDE.md requires. They are answered and closed then,
   and only with text the requester has approved.
5. **Walkthrough tickets:** Jira refused to delete TCW-65 and TCW-66 (403: the
   account lacks "Delete issues"). They stay closed, with the throwaway summary.
