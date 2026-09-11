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

- **The plan called Task 3 redundant, and the outcome repeated it. Both were
  wrong.** Verification found the case that makes it load-bearing: a slug
  containing `/`. A slash is not a glob metacharacter, so `glob.escape` leaves it
  untouched, and the lookup happily matches a claim nested one level down. The
  caller-composed destination would then have been `active/a/b`; the derived one
  is `active/b`. **For a slash-bearing slug the derivation is the only thing
  bounding where the item is published**, which is precisely the second half of
  the original request — "a path-shaped value reaching the store API is not
  bounded the way a `_find` result would be". I implemented that half while
  describing it as defence in depth, and only the verifier noticed it was doing
  real work.

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

## Autonomous decisions

1. **Is `_safe_store_id` the fix, as the request says?** Both advisors: no, it
   rejects traversal and not pattern syntax. I had already run it against `a*b`,
   `a?b` and `a[0-9]b` and watched all three pass. Rejected the request's own
   proposed mechanism, and said so in the spec rather than quietly not using it.

2. **Escape, or replace the glob with a scan?** Codex and the Opus advisor both
   said escape. A scan would have broken the invariant the companion item had
   just documented, because `iterdir` raises where `glob` returns nothing. Two
   adjacent items in one run, and the second's obvious design would have undone
   the first's.

3. **Do the recovery semantics need deciding first, as the request insists?** No.
   Both advisors traced it to the same place: a claim directory is created once,
   named for a literal slug, so nothing that matches today stops matching. A
   stated constraint that dissolved on inspection.

4. **Is the item worth doing, at priority 20?** Both said raise it. I raised it to
   55 on a severity claim that was wrong, then lowered it to 35 when verification
   proved the destructive path needs a direct store-API caller. **The advisors
   were right that 20 was too low and I was wrong about how much too low.**

5. **Fix the absolute-slug crash the sweep found?** No advisor asked. Decided
   myself to file it: the spec had made that validator an explicit non-goal with
   a stated reason, and reversing that mid-implementation without re-speccing is
   how scope drifts.

6. **Where does the review stop?** Three rounds of verification, each finding
   something real, and I did not need to put a stopping point to the user as the
   heading item required — every finding was either fixed or filed in one pass,
   and the last round found only things I had written rather than things I had
   built.

### What I would have asked about if I could

- Whether the store API is a supported surface. The whole severity question turns
  on it. If scripts against `FsWorkStore` are expected, 35 is too low; if it is
  internal, 35 is generous.
- Whether `--take-over` being unreachable from the CLI should have blocked this
  item rather than being filed beside it. I filed it because it is pre-existing
  and orthogonal, but it does mean a user cannot exercise the branch this item
  spent its time making safe.
