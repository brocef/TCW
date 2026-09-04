# Outcome — The half-deleted state is unfinishable, and an auto-delete failure swallows the completion

## What shipped

1. **`tcw work delete` finishes the state it exists for.** The gate was
   `st.get(bare) is None → "no such work item"`, which is true of *every* item
   in the half-deleted state — folder moved away by a `pre` binding that then
   failed, no `location` recorded — so `delete_resolved`'s documented "safe to
   re-run" was unreachable through the CLI and the tree kept an unstaged
   deletion. It now falls through to the tombstone: no record is still a typo, a
   record carrying a location reports the removal already finished and exits 0
   (this command finishes removals; one already finished is the state it was
   asked to reach), and a record without one is finished through the same
   `_auto_delete` path.

2. **`_complete` no longer returns from the auto-delete branch.** The completion
   and its commit have landed by that point, and three things were still owed:
   the `post` result, the report line, and the worktree cleanup — which matters
   most, because `merge_worktree` ran further up, so returning orphaned the
   worktree and its branch with nothing left that would remove them. The
   auto-delete's exit code is now carried to the end and folded into the return.

3. **`_auto_delete` returns `(exit code, removed)`.** A `PublicationError` after
   the removal committed is a real failure *and* an item that is genuinely gone;
   the caller needs both answers, and reading the exit code as "still here" made
   it print a path to a folder that no longer exists. `PublicationError` is now
   caught separately from the rest of `_ERRORS` for exactly that reason. The
   exit stays non-zero: a remote still holding a deleted item is the divergence
   publication exists to prevent, and this matches `_post_result`'s established
   shape — non-zero, but say plainly what landed.

4. **`tcw work show --json` on a removed slug exits 1 with an empty stdout.**
   The tombstone branch sat ahead of the `--json` branch, so a caller piping to
   `jq` got the human block under a success code — worse than the clean exit 1
   it got before retention existed. The stderr message names the case
   (`<slug> was resolved (done, …) and removed; there is no item document to
   project`) so a person reading a failed pipeline learns what `jq` could not be
   told.

## Tests

Five new tests in `tests/test_retention.py`, each confirmed to fail against the
previous code before being kept:

- the half-deleted state constructed exactly as the finding describes (a `pre`
  binding that moves the item *and* exits non-zero), asserting `get()` is None,
  the tombstone has no location, and `tcw work delete` then finishes it and
  leaves `git status` over the store clean;
- `tcw work delete` on an already-finished removal reporting so and exiting 0;
- the completion line printed on stdout when the auto-delete's `pre` fails;
- the worktree removed in that same case;
- a publication failure on the removal's own push, asserting the folder is gone,
  the completion is reported, and no path into `docs/work/completed` is printed.

```
$ python -m pytest -q -p no:randomly tests/test_retention.py
39 passed
$ python -m pytest -q -p no:randomly tests/*work*.py tests/*retention*.py tests/*hook*.py tests/*lifecycle*.py
622 passed
```

## Autonomous decisions

Codex is not installed in this container, so the skill's two-advisor rule could
not be met; one Opus advisor was consulted, on the one checkpoint that was a
design choice rather than a defect.

1. **What `tcw work show --json` should do for a tombstone.** Consulted. The
   options were: exit 1 with empty stdout (restores pre-feature behaviour, loses
   the distinction the tombstone exists to make for scripts); project the
   tombstone under `schema: 1`; or bump the schema. The advisor recommended the
   first and produced the argument I did not have: `WORK_ITEM_SCHEMA` is closed
   twice over (`additionalProperties: False`, `required` computed as every
   property), `hook_payload` already cites that closedness as its reason for
   putting `body_truncated` in the envelope rather than beside `body`, and
   `README` states that `--json` returns the same document as `tcw serve` — so a
   second shape is a contract change in three places. It also named the strongest
   objection: after this fix *nothing* lets a script ask the question, since
   `tcw work tombstone` has only `add`. Taken, with its mitigations — the stderr
   line names the case, and the missing capability is filed as
   `2026-09-04-nothing-lets-a-script-ask-about-a-tombstone`, including the design
   trap the advisor spotted (`location` is documented opaque and never parsed, so
   a JSON form must either embed a rendered string or hand a machine a handle it
   may not read).
2. **Whether a publication failure should still exit non-zero.** Decided alone.
   The finding calls exit 1 "success turned into failure", but the push genuinely
   did not happen, and `_post_result` already establishes the convention: exit
   non-zero, and say what landed. What was actually wrong was the silence and the
   skipped cleanup, and that is what changed.

## Notes

Findings 2 and 3 are the same line. An early return from a branch that runs
*after* the operation has been committed is how a failure in a later step came to
look like a failure of the whole thing — and how the worktree, merged seconds
earlier, ended up with nothing left to remove it.
