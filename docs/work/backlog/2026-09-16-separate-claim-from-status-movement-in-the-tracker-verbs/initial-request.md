# Separate claim from status movement in the tracker verbs

## Coordination goal

The tracker surface offers four verbs, each doing one thing, and the lifecycle
moves compose them instead of reimplementing them. Claiming a ticket asserts
ownership and nothing else; moving a ticket's status is a separate act. What the
children are collectively for is dissolving a cluster of defects that are all the
same defect — claim and status movement being one operation — rather than fixing
each where it surfaced.

## Request

The requester's framing, in their terms:

> I could see the first step being **link**, where we simply create the
> association between a work item on disk with a ticket on Jira. The second could
> be **claim** where we assert ownership of that ticket and fail if somebody else
> has already claimed it — that is the gate to prevent multiple people from
> working on the same task at the same time. Conversely claim should be safe for
> the same person to call as many times as they want. Then we have **sync** which
> is to synchronize the statuses, in particular making sure the ticket status
> matches the corresponding TCW work item status. Lastly, we have the various
> **lifecycle transition** functions which change the status of the work item on
> disk as well as the Jira ticket upstream.

### The verbs, as agreed

| Verb | Ownership | Status | Local |
| ---- | --------- | ------ | ----- |
| `link` | — | — | writes the binding |
| `claim` | asserts; idempotent for the holder; fails if held by another | — | — |
| `release` | drops ownership | — | — |
| `sync` | — | ticket ← item | — |
| `start` | claim | → `statuses.active` | backlog → active |
| `submit` / `rework` | verify still held | → mapped status | moves the item |
| `complete` | verify still held | → mapped status | resolves |
| `discard` | **none** | → `discarded` | resolves |
| `import` | claim | — | creates item + link |

### Decisions the requester made when asked

- **Ownership is one fact kept in two stores.** `claim` asserts ownership once;
  where a binding exists it also assigns the ticket. The local owner and the Jira
  assignee are required to agree, and a disagreement is drift that `sync` reports.
  This was chosen over "the Jira assignee is the gate wherever a ticket is bound"
  (rejected: it makes every claim a network call and breaks offline work on bound
  items) and over keeping the two independent (rejected: `claim` could then
  succeed locally while someone else holds the ticket, which is the case the gate
  exists to prevent).
- **Release is its own verb**, not a flag and not a side effect of resolving the
  item. Stepping away or handing off without discarding needs a name.
- **The item is the source of truth for status, and `sync` moves the ticket either
  way** — forward or backward — to match it. Chosen over today's forward-only rule
  and over a report-only `sync`. The requester should know what this costs: a
  deliberate manual move made in Jira will be undone by the next `sync`, silently
  unless the children decide otherwise. Whether that warrants a warning, a
  confirmation or a record is for `spec`.

### What this is expected to dissolve

Each of these is open today, and each is a symptom rather than its own defect:

| Open problem | Why it exists |
| ------------ | ------------- |
| GitHub #42 — linking an active item strands its ticket for good | `link` cannot move the ticket, and `sync` reads "ticket behind item" as drift it must not undo |
| GitHub #41 — discarding unstarted work is refused | every move demands the ticket be assigned to the caller, because assignment is a claim side effect |
| `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery` §1 — `start` moves a ticket backwards | `deliver` skips the "already past the claim's status" check when the move is `start` (`tcw/tracker/sync.py:297`), so the claim transition fires from wherever the ticket sits |
| that item's §3 — strict mode never asks exclusivity for a ticket already held by the caller | `claim_refusal` runs only for a ticket sitting on the claim's own status |
| `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` | you must read the workflow definition to learn whether a claim was exclusive, because the claim rides the workflow |
| the `claim: owed \| done` state inside the sync record | claim state is entangled in `tracker.yaml`'s sync record rather than being its own answer |

None of these should be fixed individually while this is in flight.

## Notes

**The hard part, and it is the crux of the spec.** Jira offers no
compare-and-swap on the assignee field, which is the whole reason the claim rides
a workflow transition today. `docs/guide/jira.md:236` states the dependency:

> Assigning only after the transition applied is what keeps two people apart on a
> workflow that refuses a second claim: the second person's transition is
> refused, so they never reach the assignment step and cannot take the ticket
> from the first.

An ownership-only claim gives that up. What makes the trade acceptable is that
today's guarantee is already conditional and undetectable — it holds only on a
workflow that stops offering the claim transition from the status it leads to,
and TCW says so itself (`jira.md:200`):

> Many Jira workflows allow every status change from every status. On one of
> those, applying the claim twice succeeds, so two people who both take a ticket
> both succeed and neither is told.

So the choice is between atomic-on-some-workflows-unknowably and
weak-but-uniform-and-detectable. Read-after-write — assign, re-read, confirm the
assignee is still you — closes most of the remaining gap, since a direct issue
read is strongly consistent and the loser of a race sees the winner's id. Keeping
the transition as an *optional* exclusivity assertion, for projects whose workflow
supports it, is available if the spec wants the strong form back. **This is the
decision the spec must make explicitly and argue for; it must not be inherited
from this request.**

**A config simplification falls out.** `transitions.claim` is the only required
key in `transitions` today, while `submit`/`rework`/`complete`/`discard` are
optional and were added by pull request #45. But `MOVE_STATUS`
(`tcw/tracker/sync.py:50`) already maps `start → active`, so the transition the
claim applies *is* the transition for the `start` move. Once `claim` stops
transitioning, that key stops being special and becomes `transitions.start`,
uniform with the rest — and `transitions.claim` ceases to exist as a concept. On
an ordinary To Do → In Progress workflow the observable behaviour of
`tcw work start` is unchanged, because the ticket still lands in In Progress;
it lands there because `statuses.active` says so rather than because claiming
dragged it there. That makes most of the migration invisible, which is worth
protecting when the children are sequenced.

**Open, and deliberately not decided here.** Whether `complete` requires a held
claim. `discard` needs none, because closing work nobody started takes nothing
from anyone; completing work nobody claimed is stranger, but the GitHub #41 shape
— a bound backlog item that was never started — reaches both. Asked and left for
`spec`.

**Reference material:** asked as part of the verb design; the requester supplied
the model itself rather than external material. Everything cited below was found
in this repository while taking the request.

**Scope not yet settled.** Whether the six subsumed problems above are closed as
superseded, re-pointed as children, or left open and allowed to no-op when this
lands, is a decomposition question for the plan. Nothing has been re-pointed or
closed yet.

## References

- `docs/guide/jira.md:190-240` — the claim's four steps and the exclusivity
  discussion; the two quoted passages are the evidence for the crux above, and
  this guide is what has to change with the verbs.
- `tcw/tracker/sync.py` — `MOVE_STATUS`/`MOVE_ONTO` (`:50-66`) define the
  move→status mapping the new `transitions.start` key would slot into; `:297`
  holds the `if not starting:` guard that is §1's defect; `deliver`,
  `authorize`, `claim_refusal` and `binding_refusal` are where claim and status
  are entangled.
- `tcw/tracker/intake.py` — `claim()` and `ever_bound()`; the claim's current
  implementation and the dead `ClaimOutcome.account_id`/`account_name` fields that
  an ownership-bearing claim would give a purpose to.
- `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  — parked precisely on the question this change makes optional; read before
  specifying, because its constraints record what a non-admin token can and
  cannot see.
- `2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`
  — the *local* claim mechanism (claim directories, `--take-over`, interrupted
  claims) that "one fact, two stores" has to reconcile with the Jira assignee.
- `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`
  — owns what strict mode refuses today; its `authorize` and `binding_refusal`
  scope overlaps this epic's and has to be settled during decomposition.
- `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket` — the
  `--part` hold, which is a second reason a ticket legitimately lags its item;
  "the item is truth, move the ticket either way" has to not break it.
