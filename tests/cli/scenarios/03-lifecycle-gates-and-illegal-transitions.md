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
| 2 | Each refusal writes to **stderr** with stdout empty, and the message names the current status and the attempted destination. Do **not** require it to name the legal move — several refusals only report that the `from → to` pair is illegal, and asserting more than that pins wording the CLI does not promise. |
| 3 | `tcw work stage begin spec $SLUG` succeeds in `backlog` and fails in `active`. |
| 4 | `tcw work stage begin implement $SLUG` fails in `backlog` and succeeds in `active`. |
| 5 | `tcw work stage begin verify $SLUG` succeeds in **both `active` and `review`**, and fails in `backlog`, `completed` and `discarded`. `verify` is deliberately legal in `active` because `complete` moves from `review \| active`, so an item can be verified without ever having been submitted. (An earlier draft of this document asserted it fails in `active`. That was wrong.) |
| 6 | `verify` and `postmortem` are **both** legal in `review` — running one does not make the other illegal (a documented sharp edge: `review → review` is not a transition, so the two stages coexist in one status). |
| 7 | `tcw work rework $SLUG` from `review` returns the item to `active` and exits 0. |
| 8 | A full `submit → rework → submit → complete` round trip works, and the item's history shows both submits. |
| 9 | **There is no required-artifact gate, and this asserts that.** `complete --resolution done --confirm` on an item whose folder holds nothing but `state.yaml` **succeeds**, exit 0 — measured. The Definition-of-Done checklist is *printed* before confirmation and is not enforced; the source says `dod_ack` is "deliberately not persisted". Pin the current behaviour so a future decision to enforce it is a visible test change. |
| 10 | Completing from `active` (skipping `review`) succeeds but **warns on stderr** that the verify stage was skipped. The warning is the only thing standing in for the gate, so it is worth asserting. |
| 10a | The real completion gates, each asserted with its refusal **and** its acceptance: an unresolved blocker (see 12–13), an epic with open **initiative** children (scenario 10), a missing `--confirm`, and a completion run from inside the item's own worktree (scenario 09). |
| 11 | `--resolution duplicate|superseded|wontfix` routes the item to `discarded/`, not `completed/`. |
| 12 | An item with an unresolved blocker refuses `start`; `--force` starts it anyway and the blocker is still recorded. |
| 13 | An item with an unresolved blocker refuses `complete`; `--force` completes it. |
| 14 | `tcw work drop $SLUG` from `backlog` **requires `--confirm`**; with it, the item folder is gone from disk. |
| 15 | An unknown stage id (`tcw work stage begin nonsense $SLUG`) exits non-zero and lists the valid stages. |

## Refusals asserted

This scenario is nothing but refusals. The pairing rule: every refusal assertion
is immediately followed by the corresponding **acceptance**, so the test cannot
pass against a `tcw` that refuses everything.

## Explicitly not covered here

Nothing about *which* artifacts completion requires — because it requires none.
An earlier draft of this document claimed the required set was configurable per
node. **That configuration does not exist.** The claim is removed rather than
softened; a scenario that describes a configuration surface the product lacks
sends an implementer looking for it.

## Notes for the implementer

Assertion 1 needs a helper that snapshots the item's folder path before the call
and re-resolves it after. `tcw work path $SLUG` is the supported way to ask;
do **not** compose `docs/work/<status>/<slug>` in the script — the work store may
be external (scenario 01, assertion 10) and composing paths is exactly the
mistake TCW's own guide forbids.
