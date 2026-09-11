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
5. `FsWorkStore.start` unchanged **by the fix**: the diff at `9cd69e83` showed
   one hunk in `init` and one docstring. **No longer literally true of the
   branch**: the later combined review (`7965069b`) moved sixteen lines of
   comment into `start`, beside the `mkdir`. Comments only, no statement
   changed — but the criterion as written said the function is untouched, and it
   is not, so it is restated here rather than quietly reinterpreted.
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
- **A race window became newly reachable, on exactly the nodes where it
  matters.** `init` checks pristineness and then deletes; between the two, a
  concurrent `start` could put a claim into `.claiming`. Before this change such
  a node was refused unconditionally, because it already had the directory — so
  the window opens precisely on nodes where someone starts items, which is every
  node it could ever matter on. Found by verification, not by me. Accepted:
  relocating a store is a deliberate single-operator act, and `init --work-path`
  running concurrently with `work start` on the same node is not a workflow this
  tool supports. Recorded because the reasoning is what makes it acceptable, and
  a future reader should be able to disagree with it.

- **One new case became deletable, and its size is known.** A *symlink* named
  `.claiming` pointing at an empty directory previously made a store
  non-pristine and now does not, so the store is replaced. The adversarial
  review found it and measured the loss: `shutil.rmtree` unlinks a symlink
  without following it, so the symlink goes and its target survives. Accepted —
  the loss is an empty symlink, and symlink containment is out of scope for this
  item by the request's own words. Recorded so it is a decision rather than a
  surprise.

- **`.claiming` is forgiven by name, not by contents.** That is a hole in a
  safety check, deliberately sized: the check exists to refuse deleting someone's
  work, and a claim in flight is work. Criteria 3 and 4 and the mutation check
  are what keep it that size.

## Autonomous decisions

1. **Remove the directory, or leave it?** My instinct and the plan's starting
   point was to remove it. Codex: leave it, the removal races the next claim.
   Opus advisor: leave it, and the cleanup would need to sit at three exit sites
   so it would not even deliver the invariant. Left it. Both agreed and both
   supplied reasons I did not have.

2. **Would a single retry close the race?** My fallback design. Codex: no —
   another completing claimant can remove the recreated directory before the
   retry. Opus advisor did not address it. Took Codex. **This is the consult that
   paid for itself**: I would have shipped a fix that looked airtight.

3. **Is "absent or empty" a legitimate invariant or a rationalisation?** Both
   said legitimate, and both reached it the same way: every reader already goes
   through `Path.glob`, which is blind to the difference. Documented it.

4. **Is the item worth doing at all, given the intake calls it harmless?** The
   Opus advisor found the pristine check, which is what makes it worth doing.
   Without that consult I would have closed the item as a test annoyance, which
   is how the intake reads.

5. **Should the release note's cleanup advice ship as written?** No advisor was
   asked; the code reviewer caught it unprompted. It told users to delete any
   tag-like joined name, which would have removed a legitimate two-word tag in
   the companion item, and here claimed the refusal "only appears when your store
   really does hold work" while `graveyard.yaml` still refuses. Both corrected.

6. **Where does the combined review with the next item happen?** Decided myself:
   after both were implemented and before either was submitted. It produced a
   finding neither item would have — two docstring blocks written without reading
   each other.

### What I would have asked about if I could

- Whether `graveyard.yaml` should also be forgiven. It is real history, so
  refusing is defensible, but the message tells a user to "move existing work
  manually" and a graveyard file is not what anyone pictures. That is a product
  call about a message, not a defect.
- Whether the race window between check and delete is worth closing. I accepted
  it on the grounds that relocating a store is a deliberate single-operator act.
  Someone running TCW from CI might see that differently.
