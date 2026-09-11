# Outcome — The claiming lookup globs with an unescaped slug

Two lines of production code. Four tests. The item was filed as hardening and
turned out to be data loss reachable by a typo.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `32099f84` | Four cases in `tests/test_external_work_store.py`, two red |
| 2 | `49fa547d` | `glob.escape(slug)`, suffix concatenated after |
| 3 | `7051b8ad` | Take-over publishes the claim it found, not the slug asked for |
| 4 | `7965069b` | The combined review of both claiming items |
| — | `60ce5e9b` | Release note with recovery instructions, and changelog |

## Acceptance criteria

All seven met.

1. A wildcard slug with `--take-over` now raises `no recoverable interrupted
   claim`, the victim's claim stays in `.claiming`, `active/` stays empty, and
   the victim's `state.yaml` keeps its owner. Before: the claim was consumed and
   `active/2026-01-01-axxxb-th*g` appeared under the attacker's name.
2. The same slug without `--take-over` raises promptly and no longer says
   "interrupted claim". Before: about 0.6 s, then that message.
3. A claim for an item whose slug literally contains `*` is still found with
   that exact slug, **and `--take-over` still publishes it**. The second half was
   dropped between spec and plan and reported met on the narrowed wording; the
   adversarial review caught that. Now tested end to end, with a sibling item
   beside it so a git pathspec that swept siblings in would be caught. It does
   not: the sibling is untouched and the claim directory is emptied.
4. `--take-over` on a genuine interrupted claim still works.
5. `_claiming_dirs` still returns `[]` with no `.claiming` directory.
6. The longer-slug/shorter-slug test at `tests/test_external_work_store.py:377`
   still passes.
7. Suite green.

Driven end to end through the CLI, not only the store API: `tcw work start
'…th*g' --take-over --owner attacker` exits 1 with `no recoverable interrupted
claim`, and the real claim is still on disk.

## What the request got wrong

Both of its substantive claims.

- **"A correctness and hardening item, not a live exposure."** The request
  reasons that `tcw serve` is localhost and single-user so no untrusted caller
  reaches the store API. But a shell passes an unquoted `*` through unchanged
  when it matches no file, so an operator typo reaches this from the command
  line. Reproduced: the real item is moved to a folder named with the wildcard,
  its owner rewritten, and the command then fails in `git add` — **after** the
  move. The user sees a git error and the item is gone from the board under a
  name nothing can address.

- **"`_safe_store_id` is the existing mechanism for exactly this question, and
  the claiming paths do not use it."** It is not. It rejects traversal, not
  pattern syntax: `a*b`, `a?b` and `a[0-9]b` all pass through it unchanged, and
  it permits `/` besides. Routing the slug through it — the request's proposed
  fix — would have left every case that causes the defect exactly as it was, and
  would have looked like a fix.

- **"The recovery semantics need deciding before the validation is tightened,
  not after."** They did not need deciding. A claim directory is created in one
  place, as `f"{slug}-{uuid4().hex}"`, and only after `_find` matched that exact
  name — so every one on disk is named for a literal slug and an escaped pattern
  built from the same string still finds it. Nothing that matches today stops
  matching. The constraint was real to state and dissolved on inspection.

## What the plan got wrong

- **One defect found by the sweep is filed rather than fixed.** A slug beginning
  with `/` reaches `Path.glob` as a non-relative pattern and raises
  `NotImplementedError` — a crash rather than a refusal. It predates this change
  (an unescaped absolute pattern fails the same way) and the CLI resolves the
  slug before it gets there, so it needs the store API. Not fixed here because
  this spec made routing the slug through `_safe_store_id` an explicit non-goal,
  and quietly reversing that mid-implementation is how scope drifts. Filed.

- **The plan predicted the red test would fail on its aftermath assertions.** It
  does not reach them: the command dies in `git add` on a pathspec containing the
  wildcard, so the test fails on an unexpected `CalledProcessError`. That is a
  better failure — it is the symptom a user sees — but the plan's prediction was
  wrong and the reason is worth keeping: the destructive move happens *before*
  anything complains.

- **An acceptance criterion was narrowed between spec and plan, and I did not
  notice.** The spec required that a slug literally containing `*` is still found
  *and still recovered*; the plan's task 1 case 3 kept only the first half, and
  the test called `_claiming_dirs` directly. The outcome then reported the
  criterion met against the plan's wording rather than the spec's. That is how a
  criterion quietly stops testing the thing it was written for, and nothing
  mechanical catches it — the wording still matches something that passes.

- **The plan called Task 3 redundant.** It is, behind the escape. It is kept
  because the invariant should be local: the path published is now derived from
  the path found, so a later change to the lookup cannot silently reintroduce a
  mismatch.

## Notes

- **The glob sweep the plan asked for is clean.** `_claiming_dirs` was the only
  glob in `tcw/` built from caller-supplied input. **The first write-up of this
  said "the two others"; there are nine call sites in total**, and the other
  eight take literal patterns. The conclusion holds and the count did not —
  corrected after review, because a sweep is only worth anything if its scope is
  stated accurately.
- **Priority raised from 20 to 55 at the spec stage.** The low priority came
  directly from the misdescribed severity — the same failure mode as the item
  before this one, whose intake also understated what was wrong.
- **The companion item's release note overstated its own reach**, and the
  adversarial review caught that too. It said the refusal "now only appears when
  your store really does hold work". `graveyard.yaml` sits in the work root the
  moment anything is completed or discarded, so a store carrying it is still
  refused with the same message. The note now says so and names the file. The
  contradiction was with a finding recorded in that item's own outcome, which is
  the worse kind: the fact was known and the user-facing text disagreed with it.

- **This fix does not repair a node it already happened on.** The release note
  says how to recognize one and put it back: a folder in `docs/work/active/`
  whose name contains a metacharacter is the missing item.
- **The combined review of this item and the previous one produced a finding
  neither would have.** Both appended to the same docstring without reading the
  other's, leaving 38 lines on a two-line helper. The notes now sit where the
  mistakes would be made.
