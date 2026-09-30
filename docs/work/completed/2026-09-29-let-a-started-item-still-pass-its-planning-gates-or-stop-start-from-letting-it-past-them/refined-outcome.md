# Refined outcome

**Accepted.** A started item can still pass its planning gates:
- `request` is legal in `backlog` and `active`, and `spec` and `plan` already
  were;
- `start` warns about each missing planning document and points at the first
  stage still to run.

A stage refused for an item's status now names the way forward:
- `rework` for a reviewed item;
- `start` for a backlog item;
- `submit` before `postmortem`;
- `stage prompt` to read a stage's instructions without entering it.

## Evidence

- **`tcw:verifier`:** criteria 1-5 and 7 met, each with a named test and a
  hand run. Full suite, bare `pytest` at `2cb33236`: 5062 passed, 3 skipped.
  `tcw validate` and `tcw capabilities check` pass.
- **Hands-on, in a scratch repository with the branch's code:**
  - `start` on a title-only item → next step `stage gate request`;
  - the `request`, `spec` and `plan` gates pass on the active item;
  - `postmortem` on an active item names `tcw work submit` and
    `stage prompt postmortem`.

## Found at verify

- **Criterion 6 named checks that cannot see stage legality.** Neither the
  baseline fixture nor `tcw work lifecycle` records it. The fact is asserted by
  `test_request_is_legal_in_backlog_and_active` and the legality table in
  `test_stage_verb.py`. Criterion 6 was reworded to say that.
- **The completeness test gained the new `start:request` key.** That goes
  slightly beyond "updated only where they pinned the old legality or hint",
  but it follows directly from the change.

## Deferred

- **Closing GitHub issue #71 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
