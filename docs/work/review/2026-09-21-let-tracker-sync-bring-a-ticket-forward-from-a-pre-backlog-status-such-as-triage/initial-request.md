# Let tracker sync bring a ticket forward from a pre-backlog status such as Triage

## Request

A ticket that already exists in a status before the backlog, such as Jira's
`Triage`, should be something `tcw work tracker link --sync-status` and
`tcw work tracker sync` can bring forward to match its item, rather than a
conflict someone has to clear by running the workflow's transition by hand.

The requester chose **opt-in configuration** on 2026-09-21. A new `work.tracker`
setting names the pre-backlog status (or statuses) and the transition out of it
(for example `Accept`), and only then do link and sync walk Triage → backlog →
active. Without that setting the refusal stays, but it names the setting that
would resolve it. The alternative, walking forward from any unmapped status with
no configuration, was not chosen. Accepting a ticket out of triage can be a team's
deliberate decision.

## Constraints

- v2.5.1 (the release carrying v2.5.0's contents, whose tag never reached PyPI) is
  held until all five items filed from the proposit-app reports on 2026-09-21 are
  fixed and accepted. This is one of them.

## Notes

- Asked for reference material, deadlines and exclusions on 2026-09-21: none
  beyond the reporter's account in `intake.md` and the related items it names.
- The active epic `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`
  (its child `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`) is
  rewriting the claim-within-delivery path this refusal comes from.
