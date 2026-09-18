# Compose the lifecycle moves from claim and sync

The last of four children under
`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. The first
three built the pieces; this one makes the lifecycle use them.

`tcw work start`, `submit`, `rework`, `complete` and `discard` each implement
their own claim handling and their own status logic today. After C1, C2 and C3
there are primitives that do those jobs on their own — `tcw work tracker claim`
and `release` for ownership, `tcw work tracker sync` for bringing a ticket into
step with its item — and the lifecycle moves should call them rather than carry
private copies of the same reasoning.

## What is being asked for

**The five moves stop implementing claim and status logic and call the
primitives.**

**The rule the requester settled, at the epic:** a claim gates work, not
resolution. `submit` and `rework` verify the claim is held. `complete` and
`discard` require none — finishing or abandoning work is not something a person
needs to own the ticket to do.

**An active item with no holder has to be answered for.** C1's `release` may be
run on an active item; that is the point of the verb. It leaves the item active
with an empty `owner`, which is a state no earlier version of TCW could produce.
Under the rule above, `submit` on such an item is refused, and the way back is
`tcw work tracker claim`.

The requester decided the two questions the epic left open:

- **`tcw work start` on an active item nobody holds takes the claim and carries
  on.** There is nobody to displace, so it succeeds rather than refusing. Today
  it renders `AlreadyClaimed(slug, "", started)` with an empty holder name — a
  refusal that names nobody.
- **`tcw work start --take-over` is retired.** C1's `tcw work tracker claim
  --take-over` does the ownership half, and after this item `start` is composed
  from the primitives, so two flags for taking over somebody else's work is one
  too many. This is a breaking change to the CLI surface.

**`link --sync-status` is retired too** (`tcw/work/cli.py:2341`). It becomes
`link`, then `claim`, then `sync`.

## Constraints

- **Do not plan around old versions of TCW reading new data.** Assume everybody
  runs the new version. New code reading old files on disk is still a real
  constraint — a `tracker.yaml` or a `tcw-config.yaml` written before this epic
  must still be readable.
- The version is not cut per item. This epic's entries are already written in
  `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md`, and the cut
  happens once, after this item.
- The abstraction litmus test governs every operation this item changes.

## Explicitly out of scope

- **The web app.** Recorded as out of scope at the epic rather than assumed.
- **Durable evidence of a `--part` hold**, which stays
  `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`.
- **Widening `sync --all`** to sweep every bound item, a stated non-goal of C2.

## References

- `docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/spec.md`
  — the epic. Its "C4" section is the scope; its Goals, Non-goals and Acceptance
  criteria bound it. The authoritative statement of what this child is for.
- `git show 108446fa` — C2's documents, including a defect it deferred here by
  name: `deliver` treats a sync record's `move` as a statement about what to do
  now, rather than what was last attempted. C3 reached the same conclusion
  independently and added a guard so it strands nobody meanwhile. This item is
  where that coupling is meant to be rewritten.
- `git show a2b72dac` — C3's documents. Its `refined-outcome.md` records the
  regression it shipped and fixed, and why the sweep that missed it was the wrong
  shape: adding a key to a shared mapping means auditing every reader of that
  mapping, not every mention of the key. Worth reading before touching
  `move_transitions` again.
- `git show ee59c22a` — C1's documents, for what `claim` and `release` guarantee
  and what they deliberately do not. Its read-after-write exclusivity has a
  stated race window, and `work.tracker.exclusive-claim-transition` is the opt-in
  ceiling above it.
- `tcw/tracker/ownership.py`, `tcw/tracker/sync.py` — the primitives themselves.

## Notes

The requester was asked for reference material beyond the epic and its children
and offered none at the epic level; the references above are the ones this
session identified while completing C1, C2 and C3.

Two observations from those three items that bear on how this one should be
worked, recorded because they were expensive to learn:

- **A green suite proved nothing about the defects that mattered.** Every defect
  found at the verify stage of C1, C2 and C3 passed the full suite. Three
  separate tests were caught asserting something other than what they claimed —
  twice by reading a value through a parser or an overwriting writer that hid the
  thing under test.
- **The most valuable single finding came from reading two children's diffs
  together**, and neither child's own review could have produced it.
