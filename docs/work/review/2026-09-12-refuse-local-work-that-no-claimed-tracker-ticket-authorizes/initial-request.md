# Refuse local work that no claimed tracker ticket authorizes

## What is being asked for

Child **C4** of `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
A project that takes its work from a tracker should be able to say so in
configuration and have TCW hold it to that: no local work unless a ticket assigned
to the person doing it authorizes it, checked against the tracker at the moment of
the change rather than against what a file in the repository says.

The epic's `spec.md` (§ Design, C4) is the authoritative statement of the boundary
and is not restated in full. In summary it asks for:

- **A `strict` configuration key** under `work.tracker`, introduced together with
  every gate that honours it. No earlier child accepts the key, and a flag that is
  only partly honoured would tell a user their work is gated when it is not.
- **Gates.** With strict mode on: `tcw work new` and `tcw work start` refuse an
  unlinked item; a mutation of a linked item first re-reads the ticket's assignee
  and workflow state from the tracker and refuses when the ticket is no longer
  assigned to whoever the local credentials authenticate as, or has moved to an
  incompatible state; and `tcw work drop` refuses a linked item in favour of a
  discard, which keeps the item and its binding.
- **Drift blocks a strict-mode mutation.** The conflict is reported, and no local
  artifact is deleted or rewritten. Following the tracker's change automatically is
  a non-goal of the whole epic.
- **No bypass flag.** Changing strictness is a reviewable edit to
  `tcw-config.yaml`.
- **The authoritative workflow-shape verdict**, moved here from C1 on 2026-09-12:
  reading a project's workflow definition to decide, before any ticket exists,
  whether the claim transition can exclude a second claimant. The epic records
  three problems with it that this item has to answer — it needs a project
  identifier no configuration key holds, it may need site-administrator
  permission, and `tcw validate` has no severity tier for it — and two
  instructions: settle the permission question with a non-admin token before
  designing around the route, and put no network call on any lifecycle-transition
  path, because `tcw validate` is a `pre` hook on `complete` in this repository's
  own configuration.

## Constraints carried from the epic and the completed siblings

- **The identity rules in the epic's § Design, "The identity decision belongs to
  the epic", bind this item.** Strict mode verifies the *tracker* identity — the
  ticket is still assigned to the account the credentials authenticate as — and
  never compares it to `WorkItem.owner`. A second developer who starts a linked
  item gets the local claim and no tracker claim, and their next linked mutation
  is refused with a message naming both facts.
- **A binding is never proof of a claim** (epic criterion 11). A hand-written
  `tracker.yaml` naming a ticket nobody claimed must not let a strict-mode
  mutation through.
- **Since C6, a linked ticket is not necessarily claimed.** `tcw work tracker link`
  records a cross-reference and changes nothing in the tracker, and claiming a
  linked item's ticket moved to `tcw work start` under C3
  (`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`). This item
  must be designed against what C3 actually built, not against the epic's
  original text — the epic's plan says to re-read C4 against C3 after C3
  completes.
- **Epic acceptance criteria owned here:** 7 (reassignment refuses the next linked
  mutation, names the conflict, deletes nothing), 9 (a strict configuration
  missing a required mapping fails `tcw validate` and still lets `list` and `show`
  run), 11 (above), and 12 (`work/require-tracker-backed-work` reads its final
  status).
- Strict mode can lock a project out of its own backlog (epic Risk 6): enabling it
  before open items are linked blocks their next mutation by design, so the
  refusal must name the fix.
- A project with no tracker configured, or with strict mode off, behaves exactly
  as it does today (epic criterion 1).

## Notes

- This document was written on 2026-09-14 by an autonomous session driving the
  epic's remaining children. **Everything in it is compiled from existing
  evidence, not taken from a requester**: the epic's `initial-request.md` (§ Remote
  drift blocks strict-mode mutations, § Proposed CLI surface, § Configuration),
  its `spec.md` § Design C4, § Acceptance criteria and § Risks, the
  `work/require-tracker-backed-work` capability (`cap-38f44c`, Missing, planning
  doc this item), and the completed siblings. No user was available to ask what is
  unclear or for reference material — asked of nobody; none provided.
- **Live Jira is out of reach for this session.** The session driving it is not
  permitted to write to a real tracker and has no credentials, so the non-admin
  permission question about the workflow-definition route cannot be settled by
  experiment here. This item's spec has to decide what to do about that rather
  than assume an answer.

## References

- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`,
  `spec.md` § Design → C4 and "The identity decision belongs to the epic" — the
  boundary and the identity rules.
- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`,
  `jira-claim-experiment.md` — what was measured about the workflow-definition
  route and about exclusive and non-exclusive workflows.
- `tcw/tracker/claim.py`, module docstring — why C1 chose one ticket's transitions
  over the workflow definition, and what that leaves for this item.
- `tcw/store/base.py`, `TRACKER_TRANSITION_KEYS` and `parse_tracker_config` — where
  a new configuration key is parsed and refused when unknown.
- `tcw/work/hooks.py` and `tcw-config.yaml` — `tcw validate` bound as a `pre` hook on
  `complete`, which is why no network call may sit there.
