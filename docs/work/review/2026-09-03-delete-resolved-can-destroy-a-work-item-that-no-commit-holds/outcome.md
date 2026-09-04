# Outcome — `delete_resolved` can destroy a work item that no commit holds

## What shipped

`delete_resolved` was rewritten around one guard that holds on every entry point,
replacing three partial ones that each covered a different cause of the same
condition.

- **`_require_retrievable`** refuses the removal unless the item's path is
  committed *and* `git status --porcelain --ignored` over it is empty. The
  predicate is **cleanliness, not existence** — see Autonomous decisions.
- **`_committed_item_path`** asks git where it holds the item, rather than
  deriving the path from an item that may already be gone. That is also what
  fixes the moved-away case: the removal is committed at the path git knows.
- **`_retained_location`** keeps a recorded commit that still holds the item
  rather than overwriting it with a HEAD that does not.
- The whole span takes `_graveyard_lock` and calls `_require_writable_graveyard`,
  as a resolving transition does. The lock is documented as non-reentrant with
  its three top-level acquirers named.
- `_require_repository` is called, and a repository with no commit refuses rather
  than recording an empty location.
- `describe_location` asks the same question on the read side, and no longer
  leaks git's own error to stderr ahead of the friendly one.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2322 passed in 350.29s (0:05:50)
```

The five environmental failures established earlier in this branch.

Five new tests in `tests/test_retention.py`, one per reproduced destroy path:
a default node whose ignore rules mean no commit holds the item; an item with a
`pre` binding's receipt in it; a node with `auto-commit-transitions: false`
(whose message names auto-commit as the likely cause); a re-run keeping the
commit that holds the item; and a moved-away item whose removal is now in the
commit, asserted by `git status --porcelain -- docs/work` being empty afterwards.

## Autonomous decisions

Codex is not installed in this container, so the advisor pair was one Opus
subagent rather than two. Recorded because the skill's adjudication rule assumes
two, and one advisor is a weaker check than the process asks for.

1. **What should the guard test?** I proposed "ask git whether the recorded
   commit contains the item's path", reasoning that the interlock, the
   auto-commit case and the ignored-files case are three explanations for one
   condition. The advisor agreed with the shape and rejected the predicate: they
   are three explanations for *two* conditions, and `cat-file -e` answers only
   "git has this path", not "git has these bytes". It enumerated five cases that
   pass an existence check and still lose content — an untracked attachment
   inside the item, a receipt written by a `pre` binding after the resolving
   commit, a stale copy at the same path, a detached HEAD, and empty
   directories. **Adopted its version:** `git status --porcelain --ignored` over
   the path, paired with an existence probe because `status` over a pathspec git
   knows nothing about is also empty. My framing was wrong and the correction is
   the substance of this item.
2. **Which commit to record.** I asked whether HEAD-at-delete-time is even the
   right commit. The advisor: yes, *provided it is verified*, because commit 2 is
   made on top of HEAD, so "HEAD contains the item" is exactly the invariant the
   two-commit design rests on — and the resolving SHA is not available to record
   anyway, since `_write_tombstone` runs before `_commit_transition`. **Adopted.**
   It also found the re-run downgrade, which I had not seen and no test covered.
3. **Refuse outright when `auto-commit-transitions` is false?** The advisor said
   no special case is needed: the retrievability check answers it in both
   directions, and refusing would make `retain: false` unusable for someone who
   commits by hand. **Adopted**, with its suggestion to name auto-commit in the
   message when it is off.
4. **Is `_graveyard_lock` safe to take here?** My least confident question. The
   advisor read the implementation: `flock` on a freshly opened descriptor, so it
   is **not reentrant**, and a future refactor moving the delete inside
   `_effect_transition_locked` would self-deadlock and report it as another
   process's fault. Safe today because no path nests. **Adopted**, and the
   non-reentrancy is now documented at the lock with its acquirers named.
5. **One advisor claim I checked and rejected.** It said the existing
   `test_delete_resolved_is_re_runnable_after_an_interrupted_removal` is itself a
   data-loss demonstration, because its node is built with `retain: True` and so
   keeps the shipped ignore rules. It does not: `init` skips the rules for any
   status named in `retain`, whichever value it carries, so that fixture's item
   is tracked and committed. The test is sound and was left alone. The concern
   was right in general, which is why the first new test builds a node that
   declares nothing.

## Notes

`_require_deletable` is deliberately kept even though `_require_retrievable`
subsumes it. It refuses before anything moves and names the one cause it knows,
which is a better diagnostic than a generic "no commit holds this"; it is no
longer the safety property, and its docstring says so.

One thing no local check can promise, now stated in the docstring: a commit that
is never pushed, or that a squash- or rebase-merge makes unreachable, takes the
content with it. That is a property of the workflow around the store.
