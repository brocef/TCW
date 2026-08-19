# 03 — Lifecycle gates and illegal transitions

The state machine's refusals. This is the scenario that fails if the lifecycle
becomes permissive.

## Functionality covered

- Stage legality by status: `spec`/`plan` in `backlog`, `implement` in `active`,
  `verify`/`postmortem` in `review`
- Transitions: `start`, `submit`, `rework`, `complete`, `drop`
- The definition-of-done gate on `complete --resolution done`
- Resolutions: `done`, `duplicate`, `superseded`, `wontfix`
- Blockers and `--force`

## What is tested

| # | Assertion |
| - | --------- |
| 1 | Every illegal transition exits non-zero **and leaves the item's folder where it was**: `submit` from `backlog`, `rework` from `backlog`, `rework` from `active`, `start` from `review`, `start` from `completed`, `drop` from `active`. |
| 2 | Each refusal names the current status and the legal move in its message on **stderr**, with stdout empty. |
| 3 | `tcw work stage spec $SLUG` succeeds in `backlog` and fails in `active`. |
| 4 | `tcw work stage implement $SLUG` fails in `backlog` and succeeds in `active`. |
| 5 | `tcw work stage verify $SLUG` fails in `active` and succeeds in `review`. |
| 6 | `verify` and `postmortem` are **both** legal in `review` — running one does not make the other illegal (a documented sharp edge: `review → review` is not a transition, so the two stages coexist in one status). |
| 7 | `tcw work rework $SLUG` from `review` returns the item to `active` and exits 0. |
| 8 | A full `submit → rework → submit → complete` round trip works, and the item's history shows both submits. |
| 9 | `tcw work complete --resolution done --confirm` on an item **missing required artifacts** is refused by the DoD gate, non-zero, item unmoved. |
| 10 | The same item with the artifacts present completes. |
| 11 | `--resolution duplicate|superseded|wontfix` routes the item to `discarded/`, not `completed/`. |
| 12 | An item with an unresolved blocker refuses `start`; `--force` starts it anyway and the blocker is still recorded. |
| 13 | An item with an unresolved blocker refuses `complete`; `--force` completes it. |
| 14 | `tcw work drop $SLUG` from `backlog` **requires `--confirm`**; with it, the item folder is gone from disk. |
| 15 | An unknown stage id (`tcw work stage nonsense $SLUG`) exits non-zero and lists the valid stages. |

## Refusals asserted

This scenario is nothing but refusals. The pairing rule: every refusal assertion
is immediately followed by the corresponding **acceptance**, so the test cannot
pass against a `tcw` that refuses everything.

## Explicitly not covered here

Which artifacts the DoD gate requires — that is configurable per node and is
covered as configuration in scenario 04, not as a fixed list here.

## Notes for the implementer

Assertion 1 needs a helper that snapshots the item's folder path before the call
and re-resolves it after. `tcw work path $SLUG` is the supported way to ask;
do **not** compose `docs/work/<status>/<slug>` in the script — the work store may
be external (scenario 01, assertion 10) and composing paths is exactly the
mistake TCW's own guide forbids.
