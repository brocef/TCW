Found by a third adversarial review, 2026-09-04, after the round that was meant
to fix exactly this area. All reproduced.

1. **`_auto_delete`'s `pre`-failure branch still hard-codes `removed=False`.**
   The previous round's stated principle was "whether the folder went is a
   question for the store, not for the exception type" — and it was applied only
   to the `except _ERRORS` branch. The `pre`-failure branch above it asserts
   `removed = False` without asking, and the `pre` binding is the *one thing in
   this function* that can have moved the item. So the identical symptom the
   previous fix describes closing is still reachable:

   ```
   tcw work: auto-delete pre hook … failed (exit 3); …-a-thing was resolved and
       committed but not removed. Fix the binding and run `tcw work delete …`.
   completed 2026-01-01-a-thing (done) → docs/work/completed/2026-01-01-a-thing
   item gone: True | pending_removal: True
   ```

   The failure message is wrong for the same reason: it says "not removed" for an
   item that is gone. And `_auto_delete`'s docstring — "A `pre` failure leaves the
   item exactly where it is" — is contradicted by `pending_removal`'s docstring a
   few lines away, which names "a `pre` binding that moves the item and then
   fails" as the exact state the machinery exists for.

2. **`MultipleMatch` is not a `ValueError`, so `tcw work delete` crashes where
   every other subcommand reports.** `class MultipleMatch(Exception)`, so
   `main()`'s global `except ValueError` does not catch it, and `_delete` reads
   the store outside `_ERRORS`. A duplicate slug under two status folders — a bad
   merge — gives a raw traceback from `tcw work delete` where `tcw work show`
   exits 1 with a clean message.

   The worse instance is `return 1, st.get(slug) is None` *inside* the `except`
   handler: a raise there escapes `_auto_delete` mid-`_complete`, skipping the
   completion report, the `post` result and `remove_worktree` — precisely the
   orphaned-worktree regression the comment beside it says it fixed by making
   this "never an early return".

3. **The `resuming` graveyard skip fires on a first attempt with a clean
   graveyard.** `pending_removal()` is true whenever the item is absent and its
   tombstone has no location — which is the state the *first* attempt is in as
   soon as a `pre` binding relocates the item, a case `delete_resolved`'s own
   docstring says it supports. The justifying comment ("the graveyard is dirty
   *because of the very state being finished*") is false there, and the guard's
   stated purpose is defeated in a documented, non-exotic flow:

   ```
   pending_removal: True
   graveyard clean? (CLEAN)              ← the premise of the skip does not hold
   now dirty: M docs/work/graveyard.yaml ← an unrelated edit, or another agent
   HEAD subject: tcw work: delete 2026-01-01-a-thing (retained in )
   SWEPT IN: True
   ```

   Nothing is lost — the write is read-modify-write — and the two
   data-destroying guards (unparseable, non-mapping) stay reachable, because
   `tombstone()` answers None for both shapes so `pending_removal` is false.
   Narrowing the skip to "the graveyard is dirty *and* the dirt is this slug's
   own entry" restores it.

4. **`_retained_location` returning `""` produces `(retained in )` in the commit
   message.** Reachable whenever a commit between the resolving commit and the
   removal drops the item path from HEAD — which is the case `return ""` was
   added for. The CLI line printed alongside says the opposite in words, so the
   git history is the only place the contradiction survives.

The reviewer separately established that `return ""` cannot *downgrade* a good
pointer: both entry points guarantee `committed is not None` whenever the
tombstone already carries a location.
