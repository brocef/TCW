# Rework — Concurrency-safe filesystem work claims for shared local stores

Rejected at `verify` on 2026-08-11. Not by a human reading the diff — by CI,
which did not exist when this item was written and which failed on its first two
runs against exactly this item's acceptance criteria.

## Which criteria failed

- **Criterion 3** — "A claim loser receives the winner's owner and start time
  **without a Python or Git stack trace**." Two different stack traces observed,
  both from a claim loser.
- **Criterion 1** — "exactly one success and one typed `AlreadyClaimed`". The
  test written for it,
  `tests/test_external_work_store.py::test_two_store_claim_has_one_winner_and_visible_metadata`,
  is what fails.
- **Criterion 2** — "repeated stress races never …". Read literally, this was
  never demonstrated: the suite runs the race **once** per test session.

## Evidence

Two failures, same test, different symptoms, both on `ubuntu-latest` /
Python 3.14. Neither has ever reproduced on the maintainer's machine — a 2-core
runner interleaves these threads differently from a many-core laptop.

| Run | Symptom | Window |
| --- | --- | --- |
| `31539262284` job `93937682285` | `TypeError: replace: src should be string, bytes or os.PathLike, not NoneType` at `fs.py:2025` | `_find` → `None` at the claim |
| `31540849741` job `93942648425` | `FileNotFoundError: … /backlog/2026-08-08-claim-me/state.yaml` via `get()` → `_item_from_dir` → `_safe_yaml` | `_find` → stale dir, then read |

The first was patched under
`2026-08-11-fix-typeerror-when-a-work-claim-loses-the-race-at-find` (completed):
`start()` now normalizes a `None` from `_find` into the same
`FileNotFoundError` recovery that already existed. **That fix was correct and
should stay.** It was also incomplete, and the second failure appeared on the
very next CI run — which is why the remaining work is being returned here rather
than patched a third time.

## What this rework has to answer

The three known windows are symptoms of one unanswered design question, and
fixing them one at a time has already failed once:

1. `os.replace` loses the move — handled from the start.
2. `_find` returns `None` because the winner's folder is in `.claiming/` —
   handled now.
3. `_find` returns a directory that is gone by the time `state.yaml` is read —
   **open.**

Specifically:

- **Enumerate the windows rather than discover them.** Every read that does
  `_find` then touches the returned path is a candidate. `get()`
  (`fs.py:2321-2323`) is the one CI found; `query()` on the next line has the
  same shape across `_item_dirs()`, and roughly twenty other `_find` call sites
  exist.
- **Decide what a loser is told, once.** Making `get()` return `None` on a
  vanished directory is the obvious local fix, but then `start()` reports
  `no such work item` — a worse lie than the crash, and a criterion-3 failure
  in its own right.
- **`_safe_yaml` (`fs.py:2267-2273`) is a near miss.** Its docstring commits to
  tolerating a malformed state file "rather than crashing the board"; it catches
  `yaml.YAMLError` but not `FileNotFoundError`. Whether a *vanished* file belongs
  under that same tolerance is a judgment this rework should make explicitly —
  degrading to `{}` would report a moved item as still sitting in its old status,
  which may be worse than raising.
- **Make criterion 2 real.** A stress loop that runs the race enough times to
  catch a window, rather than one attempt per session. Note the difficulty:
  a single-shot race test passed 1202 of 1203 local runs *with a genuine bug
  present*, so a green suite is close to no evidence here.

## Constraint learned the hard way

**No arrangement of files reproduces these bugs.** Whatever makes `get()`
succeed also makes `_find` succeed; the defects live in the *gap between two
calls*. The deterministic test added for window 2
(`test_claim_lost_at_find_takes_the_recovery_path_not_a_typeerror`) works by
forcing `_find` to answer differently on its second call. Expect to need the
same technique per window, and expect state-based fixtures to fail short of the
defect — two such attempts were made and both raised `no such work item` well
before reaching the bug.

## Not in scope

`_effect_transition` (`fs.py:2726`) has the same `_find` → use-the-path shape on
`submit`/`complete`/`rework`, which this item's claiming protocol does not cover.
Tracked separately as
`2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`.
If this rework's answer generalizes, that item may close as a duplicate — worth
checking before starting it.

## Release impact

`v0.20.0` was cut, tagged, pushed, and then withdrawn (tag deleted from `origin`
and locally) because its test suite flakes. Nothing was ever uploaded to PyPI —
the release workflow failed at its test gate, before `publish`. The version
files still read `0.20.0` and the `v0.20.0.md` notes are already written, so when
this lands the release is re-tagged at the fixed commit, **not** re-cut with
`cut_version.py` (which would bump to `0.21.0`).

TCW's first PyPI publish is blocked on this item.
