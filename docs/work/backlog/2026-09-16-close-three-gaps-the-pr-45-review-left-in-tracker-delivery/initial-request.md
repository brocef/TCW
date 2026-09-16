# Verify each step of the tracker catch-up walk lands where it aimed

## Request

The intake carries three findings from the pull request #45 review. **Two of them
moved to `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`**,
where they dissolve rather than need fixing; this item is the third, which
survives that change unaltered.

`tcw work tracker sync`'s catch-up walk brings a ticket forward through the
workflow one transition at a time. After each transition it re-reads the ticket
and plans the next step from wherever it now is. If something else moved the
ticket in between — a Jira automation, or a person — the next step is planned
from that status instead of the walk stopping and saying so. The walk cannot tell
"my transition landed where I aimed" from "my transition landed and then
something else moved it", because it only ever asks where the ticket is now.

Nobody has reproduced a harmful outcome. Every step is still bounded to statuses
the project mapped, so the walk cannot take a ticket somewhere `statuses` does not
name. What is missing is the check, not a known victim.

**What is wanted:** the walk compares where each step landed against where that
step aimed, and stops when they differ rather than replanning from the surprise.
Whether stopping means a refusal, a conflicting record, or a warning that
continues is for `spec`. A test against the fake tracker that moves the ticket
mid-walk is what would settle whether the current behaviour is harmful, and is
worth writing before deciding how loud the stop should be.

## Notes

- **Why the other two parts left.** §1 — `start` applying the claim transition
  from wherever the ticket sits, so it can move a ticket backwards — is a symptom
  of claim and status movement being one operation; under the new verbs the claim
  does not transition, so it cannot move anything. §3 — strict mode never asking
  whether a claim is exclusive for a ticket already held by the caller — becomes
  claim's ordinary idempotent success case. Both are recorded in the epic's
  request with the mechanism that removes them. The intake still holds all three
  as filed, which is the record of what the review found.
- **Sequencing against the epic.** This defect is independent of the verb model:
  the walk survives it, and a "did this step land where it aimed" check is
  additive either way. But both touch `deliver` in `tcw/tracker/sync.py`, so
  whichever runs second should expect to rebase onto the other. Not recorded as a
  blocker, because neither has to wait for the other to be correct.
- The intake's §3 also carries a cross-reference to
  `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`;
  that reference now belongs to the epic, which owns the exclusivity question.
- Reference material: the review that found this supplied no material beyond the
  finding itself; the requester's input was taken on the verb model instead, which
  is what removed the other two parts.

## References

- `tcw/tracker/sync.py`, `deliver` and the catch-up walk — the re-read-and-replan
  loop this item changes, and the one place the aimed-for status is known at the
  moment the step is taken.
- `tests/tracker_fake.py` — the fake tracker the reproduction needs; it already
  gained helpers for the walk in pull request #45, so moving a ticket mid-walk
  should be expressible there.
- `2026-09-15-follow-late-linked-tickets-and-name-transitions-in-tracker-sync`
  (completed; pull request #45) — the item that built the walk. Its plan records
  why the walk replans from the ticket rather than from a precomputed route,
  which is the design this item constrains rather than reverses.
- `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs` — took
  §1 and §3 of this item's intake; also reshapes `deliver`, hence the sequencing
  note above.
