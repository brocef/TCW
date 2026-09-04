# Outcome — A failed removal commit reports success and leaves an unfinishable tree

## What shipped

Four defects, all in the same span between the `rmtree` and the commit that
records it, plus a fifth the tests for them surfaced.

1. **Whether the folder went is asked of the store.** `_auto_delete` caught
   `TransitionCommitError` in `except _ERRORS` and returned `removed=False`,
   although `delete_resolved` raises it *after* the `rmtree` — so the completion
   printed `→ docs/work/completed/<slug>` for a folder that no longer existed.
   The `PublicationError` branch added earlier was the same question asked once;
   it is gone, and every failure now answers with `st.get(slug) is None`. That
   is the honest source: the exception type says what failed, only the store
   says what happened.

2. **`FsWorkStore.pending_removal(slug)`** — the sibling of `pending_deletion`,
   for the other side of the boundary. `tcw work delete` short-circuited on the
   tombstone's `location`, which is written *before* the removal is committed,
   so the recovery verb printed "already removed" and exited 0 while `git status`
   still showed an unstaged deletion — the one state it exists to finish. The
   predicate is "the item is gone, a record exists, and either it carries no
   location or HEAD still holds the item": exact, because a successful removal
   commit is precisely what stops HEAD holding it.

3. **Resuming a removal may commit its own graveyard write.** Found by the test
   for (2), not by the review. The first attempt writes the tombstone and then
   fails to commit, so `_require_writable_graveyard` refused the retry over dirt
   the first attempt had created — leaving the state unfinishable through the
   command that exists to finish it. The guard's subject is a hand edit being
   swept into a transition commit; when resuming, the sweep is the point, and
   the graveyard lock is held for the whole span so nothing is mid-write.

4. **A tombstone no longer names a commit that never held the item.**
   `_retained_location` fell back to `rev-parse HEAD` when `committed is None` —
   which is exactly the case `_require_retrievable` cannot refuse, because there
   is no folder left to refuse over. Recording HEAD there named a commit that
   demonstrably does not contain the item, the one thing `Tombstone`'s docstring
   says a handle must never do. It records `""`, and the CLI says "no commit
   held its documents" instead of naming one.

5. **`describe_location` takes the slug, and the check is real.** It probed
   `ls-tree <location> -- <self.root.name>` — `work`, against a repository where
   the store sits at `docs/work` — and `git ls-tree <sha> -- <anything>` exits 0
   with empty output regardless. So the only case it could detect was a missing
   commit *object*; a commit this clone has and which never held the item always
   passed. `_commit_holds` asks for the item under either resolved status, and
   the two failures are now told apart: a commit this clone does not have, and
   one it has that does not contain the item.

6. **The item's own resolution survives an empty graveyard.** `delete_resolved`
   read the resolution only from the graveyard, defaulting to empty — on a board
   adopting retention before backfilling, which is the migration the README
   describes. The *date* is deliberately left alone: `WorkItem` carries no
   resolved timestamp, and `_write_tombstone`'s default is the same honest
   "known resolved by today" the backfill command already uses.

## Tests

Six new tests in `tests/test_retention.py`, all confirmed to fail beforehand.
They share a `commit-msg` hook that rejects the removal commit and nothing else —
a stand-in for every commit failure (an `index.lock`, a missing identity, a
signing failure), which is what makes the state reachable at all.

- the completion is reported without a path to the removed folder;
- `tcw work delete` finishes the uncommitted removal and leaves `git status`
  over the store clean;
- a genuinely finished removal still reports "already removed" and exits 0 —
  the idempotency the pending check must not cost;
- no commit holding the item records no commit;
- a commit this clone has that does not hold the item is reported unresolvable,
  where the previous check reported it as present;
- the item's resolution survives a graveyard with no record of it.

```
$ python -m pytest -q -p no:randomly tests/
4 failed, 2350 passed in 353.02s (0:05:53)
```

The four environmental failures (three `chmod` tests that cannot fail as root,
one wheel build this container refuses).

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. Each finding
was reproduced by the review with a script, and re-reproduced here as a test
before any code changed.

1. **Whether to distinguish failures by exception type or by asking the store.**
   Asking the store. Adding `TransitionCommitError` beside `PublicationError`
   would have fixed the reported case and left the next one — `_write_tombstone`
   raising between the `rmtree` and the commit — with the same wrong answer. The
   store is the only thing that knows, and the question is one line.
2. **What to record when no commit holds the item.** Nothing, rather than
   refusing. Refusing would break the supported case of a `pre` binding that
   relocates the item, and `Tombstone.location` is documented as optional and
   opaque precisely so it can be absent. A record that says "this slug existed
   and nothing was retained" is true; one naming HEAD is not.
3. **Whether the resume may sweep the graveyard.** Yes, scoped to
   `pending_removal`. The alternative — asking the user to commit TCW's own
   half-written file before TCW will finish its own removal — is the
   unfinishable state under a politer message.

## Notes

Defect 3 is the one the review did not find, and it was reachable only by writing
the test for defect 2: the recovery path had never been exercised after a *commit*
failure, only after a `pre` failure, where the graveyard is clean because nothing
was written yet.
