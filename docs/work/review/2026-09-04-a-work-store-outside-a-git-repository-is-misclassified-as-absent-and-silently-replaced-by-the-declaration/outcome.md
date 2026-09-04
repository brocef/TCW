# Outcome — A work store outside a git repository is misclassified as absent and silently replaced by the declaration

## What shipped

`FsWorkStore._open_at` raises **`StoreDeclarationError`** for a `work.path` that
names a directory which exists, is a directory, and has the complete work-store
layout, but sits outside any Git repository.

Two decisions, and the second is the one that keeps the fix from being worse than
the defect.

1. **Not `StoreLocationUnusable`.** That class is scoped by its own docstring to
   "absent, not a directory, or lacking the component's layout", and this
   condition is none of those: the store is *there*, and what is wrong is that
   its commits have no home. That is "present and wrong", the side of the line
   the ladder must surface — its docstring says a declaration is a fallback and
   never an override, and a store the machine has is not a machine that lacks it.
   Falling through meant a declared `work.repository` silently answered instead,
   so every `tcw work` command read and wrote a store the user had not
   configured, their items invisible and nothing said anywhere; before
   provisioning, the error named `tcw provision` and never mentioned `work.path`.

2. **Not a plain `ValueError`.** `find_node` re-raises only
   `StoreNotProvisioned` and `StoreDeclarationError` and flattens every other
   `ValueError` to None, so a bare one makes `tcw work list` answer
   `no tcw work node here — run tcw init` for a node that plainly is one — worse
   than the silent substitution it replaces. Verified end to end:

   ```
   $ tcw work list
   tcw: …/tcw-config.yaml: work.path is not inside a Git repository: …   (exit 1)
   $ tcw validate
   work check: …: work.path is not inside a Git repository: …            (exit 1)
   ```

`StoreDeclarationError`'s docstring widens to what it always meant: any
configured location the adapter can see is there and cannot use, not only a
wrongly declared home repository. `_has_work_store` catches `ValueError`, of
which this is one, so a topology listing still answers False for another node
rather than failing.

## Tests

`tests/test_store_provisioning.py::test_an_unusable_local_layout_falls_through_to_the_provisioned_store`
is **inverted** rather than deleted, and renamed
`test_a_local_store_outside_git_is_reported_not_silently_replaced`. It asserts
the exception class, the message naming `work.path`, and that `tcw provision` is
*not* suggested — the wording the fall-through used to produce. Its neighbour,
`test_a_location_that_holds_no_store_still_falls_through_to_the_declaration`, is
untouched: it is the other half of the pair, and a fix that stopped rule 1
falling through at all would break every declaration.

```
$ python -m pytest -q -p no:randomly tests/
5 failed, 2364 passed in 359.08s (0:05:59)
```

Four environmental; the fifth is the timing-sensitive
`test_a_grandchild_does_not_survive_the_timeout`, which passes alone.

## Autonomous decisions

Codex is not installed in this container, so only one advisor was available; it
was consulted, because an existing test encoded the opposite decision and that
had to be understood before overruling it.

1. **Whether to surface or keep falling through.** Consulted. The advisor
   recommended surfacing, and established two facts I did not have. First, the
   opposing test was **incidental**: `git log -S` finds it only in the squashed
   commit at the root of the repository's history, with no spec, plan or outcome
   arguing for it, and at that time rules 1 and 2 caught bare `ValueError`, so
   its assertion held for every failure reason — its docstring describes the
   behaviour rather than choosing it. Second, the current classification was
   equally incidental: `StoreLocationUnusable` was introduced by a sweep that
   converted all four raises in `_open_at` at once, and that item's own outcome
   says "nothing else changed about what they check" — so the sweep contradicted
   the principle it was justifying. A third finding sealed it: `tcw init`
   already refuses to create this configuration, so the state is unreachable
   through supported commands and nothing legitimate depends on the fallback.
2. **Which exception class.** Taken from the advisor, who reproduced both. This
   is the part I had wrong: my working change raised a plain `ValueError`, which
   `find_node` swallows into "run `tcw init`". Wrong in a way that would have
   read as a fix.
3. **Whether to pursue the read-only variant.** Not here. See the deferred
   follow-up.

## Notes

The advisor's counter-argument is real and is recorded rather than dismissed:
TCW's published contract is that it "has always needed Git to write and never
needed it to read", and under this change a store outside a repository cannot be
*read* either. The contract-faithful answer is to drop the open-time check and
let the existing write gate refuse mutations — which is how the non-external
default `docs/work` already behaves in a non-git directory, making the current
code inconsistent with itself. It is not a one-liner: `_open_at` falls back to
`store_git_root=node_root`, so removing the check would let `require_repository`
inspect the *node's* repository, pass, and hand a path outside it to `git_stage`
— the half-written-then-traceback failure v1.0.1 exists to eliminate. Doing it
safely means `store_git_root: Path | None`, which is its own change.
