# Claim an external tracker ticket and bind it to a work item

This is child C2 of the epic
`2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`, and
with C1 (`2026-09-12-configure-an-external-tracker-and-read-its-tickets`,
completed 2026-09-14) it finishes the first delivery the epic agreed on
2026-09-12.

## What is being asked for

C1 lets a developer see Jira tickets from the terminal (`tcw work tracker list`,
`tcw work tracker show`) but not act on them. This item lets a developer or agent
**take a ticket and turn it into TCW work**, so that:

1. **Claiming a ticket in Jira and creating the local work item are one step.** A
   developer names a ticket; TCW claims it in the tracker and then creates a
   backlog work item that carries the ticket's product text and a record of which
   ticket it answers. If the claim does not succeed, no local item is created.
2. **The record that an item answers a ticket is machine-readable,** not a ticket
   key typed into a title.
3. **Running the same import again does not create a duplicate.** One ticket can
   still deliberately become several items when the developer names separate
   parts of it.
4. **A claim that succeeded in Jira but whose local step failed can be finished
   by running the command again,** rather than being reported as someone else's
   claim.
5. **An existing work item can be bound to a ticket after the fact,** and a wrong
   binding can be removed with a recorded reason.

All three commands the epic names for this child stay in this one item: import
(claim, then create a bound item), link (bind an existing item), and unlink (an
audited repair). Confirmed by the user at this stage.

## Who may claim

A ticket may be claimed when it is **unassigned, or already assigned to the
account TCW's credentials sign in as**. Claiming an unassigned ticket assigns it
to that account. A ticket assigned to someone else is refused. Confirmed by the
user at this stage.

## Constraints already fixed by the epic

These are decisions made in the epic's spec and plan. They are listed so the
`spec` stage starts from them rather than re-deciding them; the epic says a child
that needs to depart from them returns to the epic.

- **Importing does not set the item's local `owner`.** Importing binds a ticket to
  a backlog item; it does not start work. The tracker account that won the claim
  is recorded separately and never overwrites `owner`.
- **The ticket's product text goes into the item's intake, not its request.** The
  `request` stage still has to be run on an imported item.
- **Whether a claim worked is decided by reading the ticket back, never from the
  Jira response to the transition.** The epic's experiment recorded three
  different `HTTP 400` bodies for the same logical condition, one of them blaming
  permissions for a lost race.
- **No credential is ever written** to the repository, to the binding, or to any
  output.
- **The web app must not offer to edit the binding.** The epic's Risk 1 assigns
  this to C2, because C2 is where the binding becomes an editable named resource.
- **A project with no tracker configured behaves exactly as it does today.**
- No provider abstraction, no new runtime dependency, Jira Cloud only.

## Out of scope

- Pushing later lifecycle changes out to the tracker, and `tracker sync` (C3).
- Strict mode, refusing work no ticket authorizes, and reading a project's
  workflow definition (C4).
- Showing the binding in `tcw work list`, `tcw work show`, `--json`, or the web app
  (C5).
- Inheriting `work.tracker` from parent nodes
  (`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`).

## Notes

- **The user does not want import to care whether the workflow can exclude a
  second claimant.** Asked what import should do on a workflow whose claim
  transition is still offered after it applies, the user answered: "We don't care
  if multiple claimants is possible or not." So import neither refuses nor warns
  on that basis.

  The `spec` stage should reconcile this with two things written earlier. The
  epic's goal 1 promises a single winner "when the tracker's workflow can express
  that", and epic acceptance criterion 2 (two concurrent imports of one ticket
  produce exactly one local item) is assigned to this child. On a workflow that
  does exclude, reading the ticket back after claiming may still deliver that
  property without import ever having to judge the workflow; on one that does
  not, the property may not be achievable. The answer above means the spec should
  not add an exclusivity check to make it achievable, and should say what the
  criterion then covers.
- **The epic spec's notes say C2 must build a conforming workflow in `TCWTEST` and
  rerun the experiment before freezing.** That was done the same day in a second
  project, `TCWCLAIM` (Part 2 of `jira-claim-experiment.md`), so it is not an open
  task for this item.
- **The epic spec's C2 section asks that `tracker.yaml` be marked generated** so
  the web app shows no edit button, and says the missing server-side refusal for
  generated sidecars "should be filed separately rather than absorbed here". No
  such item or inbox note was found when this request was written.
- **Reference material:** asked; none provided beyond the documents listed below.

## References

- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/spec.md`
  — the C2 boundary, the identity decision binding on this item, acceptance
  criteria 2, 3, 4, 8 and 11, and Risk 1.
- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/plan.md`
  — the documentation updates this child is expected to schedule.
- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/initial-request.md`
  — the original binding shape, idempotency key, default imported title, and
  failure scenarios.
- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/jira-claim-experiment.md`
  — measured Jira claim behavior on a workflow that does not exclude (`TCWTEST`)
  and one that does (`TCWCLAIM`).
- `docs/work/completed/2026-09-12-configure-an-external-tracker-and-read-its-tickets/spec.md`
  and `outcome.md` — what C1 built that this item uses (the Jira client, its error
  types, the claimability assessment), and the note that confirming exclusivity at
  claim time was left to this item.
