# Outcome — The leftover claiming directory

One line of production code, five tests, and the invariant written down.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `e165a054` | Five cases in `tests/test_non_git_writes.py`, one red |
| 2 | `9cd69e83` | `.claiming` discarded from `init`'s pristine comparison |
| 3 | `9cd69e83` | The invariant, and the test docstring corrected |
| 4 | `dac7e707`, `f2ba258b` | Release note and changelog |
| — | `7965069b` | Notes moved beside the code they warn about (combined review) |

## Acceptance criteria

All eight met.

1. A store whose only extra entry is an empty `.claiming` relocates. Was refused.
2. The same store without it still relocates.
3. A store holding a real item is still refused as non-pristine.
4. A store holding both is still refused.
5. `FsWorkStore.start` unchanged by this item: `git diff` showed one hunk in
   `init` and one docstring.
6. `tests/test_non_git_writes.py:190` keeps its fresh-node fixture and its
   absence assertion; only the docstring explaining *why* changed.
7. The invariant is recorded — relocated during the combined review, see below.
8. Suite green.

Driven by hand as well: a scratch node where an item was started and removed
relocates, and the original refusal reproduces on an otherwise pristine store
whose only change is that one directory.

## What the intake, spec and plan got wrong

- **The intake misdescribed both the symptom and the harm**, and that is why the
  item sat at no priority for three weeks. It said the leftover directory makes
  the assertion `assert not (root / "docs/work/.claiming").exists()` "pass for
  the wrong reason"; on a node that has started an item, that assertion *fails*.
  And it called the directory "harmless in itself", when it made
  `tcw init --work-path` refuse to relocate an otherwise-empty store with
  "move existing work manually" and nothing to move. **A misdescribed symptom
  costs more than a missing one: nobody can weigh the item.**

- **The obvious fix was wrong and I had to be talked out of it.** Removing the
  directory after a successful claim was my first instinct and the plan's
  starting point. Three independent reasons killed it, and both advisors reached
  them separately: it races the next claim, with `os.replace` into a vanished
  parent read as a lost race and reported as an interrupted claim on an untouched
  item; the race fires when two agents start *different* items, which is the
  ordinary case here; and a claim leaves by three renames, so a cleanup at one
  would not even deliver the property it paid for.

- **My own middle option was also wrong.** I proposed retrying the rename once
  after recreating the directory. Codex pointed out that another completing
  claimant can remove the recreated directory before the retry, so it shrinks
  the window rather than closing it. I would have shipped a fix that looked
  airtight and was not.

- **The plan assumed the `all(...)` clause needed no change and said to verify
  rather than assume.** That was right: an empty `.claiming` satisfies the
  `<= {".gitkeep"}` subset test already, so forgiving the *name* while the clause
  still walks the *contents* is what keeps a claim in flight refusing.
  Mutation-checked by ignoring the contents too, which turns that test red.

- **The plan's verification section found something it did not predict.**
  Completing an item also leaves `graveyard.yaml` in the work root, which fails
  the same pristine check. Left alone: a graveyard holds real records of resolved
  work, so refusing is defensible and the message is accurate there. Recorded
  rather than folded in.

## Notes

- **The invariant moved during the combined review of this item and the next.**
  Both touch claiming, and each had appended a block to `_claiming_dirs`'
  docstring without reading the other's, leaving 38 lines of prose on a two-line
  helper. The directory-lifetime note and the warning against adding a cleanup
  now sit beside the `mkdir` in `start`, which is where someone would try to add
  one. That relocation is the combined review's finding, not either item's.
- **`.claiming` is forgiven by name, not by contents.** That is a hole in a
  safety check, deliberately sized: the check exists to refuse deleting someone's
  work, and a claim in flight is work. Criteria 3 and 4 and the mutation check
  are what keep it that size.
