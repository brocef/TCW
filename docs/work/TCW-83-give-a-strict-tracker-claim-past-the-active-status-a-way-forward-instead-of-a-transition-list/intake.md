# Give a strict tracker claim past the active status a way forward instead of a transition list

Under strict mode, `tcw work tracker claim` of an unassigned ticket that sits past
`statuses.active` (for example in the review status) refuses with the bare message
from `assert_ownership` — "SYNC-1 is in 'In Review' and does not offer 'Start
Progress' … It offers: …" — which names nothing to do. On a permissive workflow that
does offer the claim transition there, it goes further: it moves the ticket back to
the active status and only then refuses. `tcw work start` already handles this case
before sending anything (the `past` branch in `_strict_claim`, `tcw/work/cli.py`),
naming both ways out; `_tracker_claim` has no equivalent guard. The same bare list is
what a `--take-over` of a colleague's ticket on the active status gets on a directed
workflow, since `_unclaimable_on_active` covers only an unassigned ticket there.

The strict spec's goal is that every strict refusal about a claim names something the
user can do next; these two paths still do not.

## Origin

Follow-up found at verify of
`2026-09-22-give-a-recordless-sync-a-move-and-let-strict-mode-work-without-transitions-start`,
by the adversarial review and the verifier. Pre-existing — not introduced by that
item. The user chose to file it rather than fold it in.

## References

- `2026-09-22-give-a-recordless-sync-a-move-and-let-strict-mode-work-without-transitions-start` — added `_unclaimable_on_active` for the rung-0 case; this is the rungs above it and the take-over case.
- `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items` — related: other gaps in the same strict gate.
