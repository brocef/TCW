# An `external:` blocker never clears, even when its target is completed

## Origin

Hit while driving a multi-node epic to completion in `proposit-orchestration`
(root node plus four child nodes) on 2026-08-25, running the installed plugin at
**1.0.2**. The code below is quoted from the repo at **1.0.3**, where it is
unchanged.

## Problem

`tcw work start` refuses an item whose only blocker is an `external:` reference to
an item that is **`completed`**. The blocker can never be satisfied by finishing
the work it names; the only ways forward are `--force` or editing the blocker away.

Observed sequence:

```
$ tcw work complete proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-…
completed proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-… (done)

$ tcw work start 2026-08-22-capability-and-parity-audit-after-the-tamagui-conversion
tcw work: blocked by: external: proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-…
          (use --force to override)
```

`store/base.py::unresolved_blockers` (1883–1907) reports every external entry as
unresolved, without looking at it:

```python
for b in item.blocked_by:
    if "external" in b:
        out.append(f"external: {b['external']}")     # ← unconditional
    elif "slug" in b:
        ... # resolves the item and honours RESOLVED_STATUSES
```

The docstring says so outright — *"An entry is unresolved if it is external, or a
slug whose item is not resolved"* — so this reads as deliberate: the store cannot
resolve a reference into another node, so it assumes the worst.

`work/recursion.py::_ready` (138) makes the same assumption independently:

```python
blocked = any(b.get("slug") in unresolved or "external" in b for b in item.blocked_by)
```

## Why it is worth changing

**The rollup already resolves cross-node references, so the two disagree about the
same fact in the same output.** `tcw work reconcile` printed the blocker's target
as `completed`, in a table it built by walking the connected nodes — and the row
directly above it showed the dependent item as `backlog | blocked-by: external: …`:

```
| . | …capability-and-parity-audit… | backlog | external: proposit-mobile/…convert-the-mobile-shell… |
| proposit-mobile | …convert-the-mobile-shell… | completed | - |
```

So the machinery to answer the question exists and is being used a few lines away;
`unresolved_blockers` just does not use it. If the reconcile walk can see that the
target is resolved, the blocker check should be able to.

**The workaround teaches the wrong thing.** `--force` is the obvious escape, and it
records "started despite an unmet dependency" when the dependency was in fact met.
I used `tcw work edit --unblocked-by "external: …"` instead so that the history
says the blocker was satisfied rather than overridden — but that permanently
deletes the edge, so the item no longer records what it waited on. Neither option
leaves an accurate record, which is the thing a work tracker is for.

This bites hardest exactly where cross-node blockers are most useful: a multi-node
epic whose slices hand off between nodes in a fixed order. Every hand-off needs a
manual intervention.

## Shape

The narrow fix is to resolve the external reference the way `reconcile` does before
declaring it unresolved, and fall back to "blocked" only when the reference cannot
be resolved from where the command runs — which is the honest version of the
current assumption, and keeps the behaviour unchanged for a genuinely
unreachable node.

Both call sites need it: `store/base.py::unresolved_blockers` gates
`start`/`complete`, and `work/recursion.py::_ready` computes the rollup's **Next**
line, which today can name an item that `start` will then refuse.

Worth deciding explicitly: whether an unreachable external reference should block
(today's behaviour, safe but sticky) or warn and proceed. A third option is to let
it block but say *why* — "cannot resolve `proposit-mobile/…` from this node" is a
much better message than "blocked by", because it tells the reader the problem is
their vantage point rather than their sequencing.

## Repro

Two registered nodes, A and B.

1. In B: `tcw work new "thing"`.
2. In A: `tcw work new "dependent" --blocked-by "external: B/<thing-slug>"`.
3. In B: `tcw work start <thing-slug>` then
   `tcw work complete <thing-slug> --resolution done --confirm`.
4. In A: `tcw work start <dependent-slug>` → refuses, naming the completed item.

Step 4 is the bug; steps 1–3 are the ordinary hand-off it is meant to support.
