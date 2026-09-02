# Plan — Answer capabilities drift from the tombstone

Small change, one function. The ordering below exists so the tests that prove
the defect are written and watched red before the code that removes it, and so
the suite is green at every commit boundary.

## Tasks

### 1. Tests for the reproducibility gap — `tests/test_capabilities.py`

Four tests beside the existing drift tests, which already establish the fixture
shape (`write_cap` + a `Planning doc` pointed at a real item).

- `test_cli_drift_reports_a_shipped_item_whose_folder_is_gone` — spec criterion
  1. Complete the item, remove its `completed/` folder, assert `drift` exits 1
   and names the capability.
- `test_cli_drift_gives_the_same_verdict_either_side_of_the_ignore_rule` —
  criterion 2. Capture output and exit code before and after removing the
  folder; assert both are equal. This is the criterion the whole item exists
  for, so it asserts equality rather than re-asserting the value.
- `test_cli_drift_still_ignores_a_discarded_item_whose_folder_is_gone` —
  criterion 3. The distinction the command makes deliberately, now reached
  through the record instead of the folder.
- `test_cli_drift_is_silent_when_the_record_kept_no_resolution` — criterion 4.
  Backfill with `tcw work tombstone add` (no `--resolution`), assert exit 0.

**Proves:** all four fail against the current tree. Watch each red and read the
failure text — criterion 3's test can pass for the wrong reason, because "not
reported" is also what a *broken* lookup produces, so its red run must show the
capability being reported before the fix, not silence.

That last point is why criterion 3's test is written here rather than after the
fix: a test that asserts an absence has to be seen failing, or it proves nothing.

### 2. Answer from the tombstone — `tcw/capabilities/cli.py`

In `_shipped_but_missing`, where `work.get(slug)` returns `None`, consult
`work.tombstone(slug)` and treat a recorded resolution of `done` as shipped,
mapping through `resolution_status` rather than a second literal comparison. A
live item keeps answering from its own status. A tombstone with no resolution
reports nothing.

**Proves:** the four tests from task 1 go green; the seven existing `drift`
tests stay green.

### 3. Guard the negative that the store cannot express — `tests/test_capabilities.py`

One test asserting `_shipped_but_missing` does not report a capability whose
`Planning doc` names a slug that never existed (criterion 5), with no folder and
no tombstone. Cheap, and it is the case that separates "resolved" from "typo" —
the same distinction the tombstone work exists to make.

**Proves:** criterion 5. Expected to pass before *and* after the change, so it
is a regression guard rather than a defect test, and the plan says so rather
than pretending it goes red.

## Documentation Sync

One block, at the end, over the finished diff.

- **`README.md` [Public-API]** — expected to fire. The README documents
  `tcw capabilities drift`; if its description implies the answer depends on the
  local tree, correct it. Check rather than assume.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires. User-visible: the
  command now reports in CI and in a colleague's clone. Must also carry the two
  honest limits — silence where no resolution was recorded, and that
  `epic_completable` is still machine-dependent, so nobody reads this as the
  whole class being closed.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires. Record the fix,
  the sweep, and the second instance the sweep found and this item does not fix.
  The existing changelog already carries a corrected note about the earlier
  sweep being incomplete; extend it rather than contradicting it.
- **`skills/tcw-capabilities/SKILL.md` [Skill-Driven-Component]** — check. The
  skill drives `tcw capabilities`; if it describes drift detection in terms of
  the work item being present, it needs the same correction as the README.

## Verification

Beyond the suite:

- **Run `tcw capabilities drift` in this repository** before and after, and
  confirm the verdict does not change here. This repo has no `Missing`
  capability pointing at a resolved item, so the expected result is "no
  capability drift" both times — a silent no-op is the correct outcome and worth
  confirming rather than assuming.
- **The sweep is part of the deliverable.** `spec.md` carries the table; nothing
  in the suite can check that it is complete. The `verify` stage should read it
  as a claim, not as a result.

## Follow-up to file, not to fix

`epic_completable` (`tcw/store/base.py:2141-2150`) has the identical defect and
is confirmed in `spec.md` with a measured before/after. It blocks a completion
rather than under-reporting, so it is the more damaging of the two — but the
tombstone does not record which epic a child belonged to, so fixing it changes
what the record carries. File it as its own item during implementation, before
closeout, so it is not left to memory.

## Notes

- No blockers. Nothing else in flight touches `tcw/capabilities/cli.py`.
- Task 2 is four or five lines. The weight of this item is in task 1 and in the
  sweep already written into the spec, which is the right distribution for a
  defect whose entire character is "it silently answers differently depending on
  who asks".
