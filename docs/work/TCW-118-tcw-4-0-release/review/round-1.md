---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-118, TCW 4.0: release

Reviewed by a separate read-only `tcw:reviewer` agent at `main` `fb72a7d7`,
over Phases A to C (Steps 1 to 26 of the plan), against the implement round
and the release folder's raw records (`~/.tcw-4.0-release/`). It did not run
the full suite, which the dispatching session ran separately (round 2).

**Rejected, for the record, not the work.** Every release step's raw record
held up, and `tcw validate` gave `0 errors, 0 warnings, 0 unresolved`. But
several criteria say "the implement round records X", and the round did not.

## Criteria

- Met: 2, 3, 4, 5, 6, 8, 9, 11, 13, 14, 15, 17, 18, 19, 20, 21, 22, 43, 44,
  45, 47, 48, 49, 53 (with the deviation the round reports: the clean list
  after Step 21's adoption was read, not saved), 54.
- Partly met, because the round lacked the record:
  - 1 and 10: no Step 1 record (the twelve `stage:` lines; TCW-116's proof
    2 status).
  - 7: TCW-111's entry files were edited by `88dda46b`, with the user's
    permission recorded only in the handoff.
  - 12: no time for Step 11's message; nothing on Step 12's messages.
  - 16: no comparison with TCW-116's proof count.
  - 46: the round held only a superseded CI run (`08e59cdf`), though
    `step-10j.out` proves CI on V `f6a61093`.
  - 52: the round did not record that gate 2's request said the tickets'
    way back had never run against a live board.

## Capabilities

The five declared paths are present and describe the code. Six more
capability records changed by this item were not declared:
`capabilities/add-a-capability`, `cli/group-objects-in-organising-folders`,
`cli/run-from-a-git-worktree`, `skills/work`, `taxonomy/add-a-term`,
`work/decompose-a-work-item-into-children`.

## Documentation entries

`tcw work docs` evaluated against the change. Two fire without a matching
change: Project-Setup-Change (the worktree and sibling-repository behaviour
has no S-4 requirement in `docs/use-cases.md`), and Any-Code-Change for
`08e59cdf` (the Python 3.11 fix has no changelog line; arguable, since it
fixes code no release shipped).

## What implement must do

Fill the round's gaps above; declare the six capabilities; add the S-4
requirement. All are edits in the item's folder and `docs/use-cases.md`; no
code changes. Nothing needs a separate change.
