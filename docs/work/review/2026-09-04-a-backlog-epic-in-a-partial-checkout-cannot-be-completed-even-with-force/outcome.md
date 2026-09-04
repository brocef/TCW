# Outcome — A backlog epic in a partial checkout cannot be completed even with force

## What shipped

1. **`WorkStore.epic_children_all_resolved`** — the structural half of
   `epic_completable`, split out because the two answers have different jobs.
   Whether an epic may close straight from `backlog` is a question about the
   epic: is it an epic, and is every initiative child this store can see
   resolved. Whether that answer is *trustworthy from here* is a **gate**
   question, and the gate for it already existed, under `if not force:`, where
   `--force` can reach it and the refusal names the missing projects.

   Folding the second into the first made a backlog epic in a partial checkout
   unreachable by every route: `from_backlog_epic` went False, so
   `IllegalTransition` fired *before* the force check, and it blamed the status
   transition — `cannot complete from backlog as 'done'` — for a condition that
   has nothing to do with the status. The sibling gate ten lines below
   advertises `--force`; from this state it could not be reached.

   `epic_completable` itself is unchanged for its own caller. It drives a "ready
   to complete" signal, and a hint that says ready must not invite an action the
   gate refuses — so it keeps both halves.

2. **`incomplete_graph_note` lists each project once.** `_unreachable_edge`
   dedupes on the whole `UnreachableProject` (id, declaring config, declaration),
   which is right for the record and wrong for a sentence: a project two present
   configs both name rendered as `missing connected project(s): proj-c, proj-c`.
   A set of ids, not a sorted list of them.

3. **A registry that cannot be opened is no longer reported as a complete
   graph.** `except Exception: return ""` told every caller the graph was whole
   in the one state where that is least likely to be true — failing the
   completion gate *open*, which is the direction the gate exists to prevent. It
   now returns a note saying the graph could not be read, and why.

## Tests

Four new tests in `tests/test_epic_completable.py`, all confirmed to fail
beforehand:

- a backlog epic in a partial checkout is refused, the message names the missing
  project, and does *not* say `cannot complete from backlog` — asserting the
  wrong message is absent is the point, since the previous behaviour also
  refused;
- the same epic completes under `--force`, asserted to still be in `backlog`
  first, because the fixture that made the original bug invisible was one that
  had started the epic;
- a project declared by two present configs appears once in the note;
- a registry whose `open` raises produces a non-empty note.

```
$ python -m pytest -q -p no:randomly tests/
5 failed, 2353 passed in 352.58s (0:05:52)
```

Four environmental. The fifth,
`test_generate_hook.py::test_a_grandchild_does_not_survive_the_timeout`, is
timing-sensitive: it passes on its own and appeared in two of this branch's five
full runs, on unrelated commits.

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. The review
reproduced the defect and named its mechanism precisely.

1. **Whether to move the partial-graph check out of `epic_completable` or to
   reorder `complete`.** Split the predicate. Reordering — computing
   `from_backlog_epic` after the force check — would have worked for this route
   and left `epic_completable` answering a gate question to a caller that only
   wants a hint. Two predicates with distinct jobs is what the defect was about.
2. **Whether `epic_completable` should keep the partial-graph refusal.** Yes.
   Its caller renders "ready to complete"; saying ready where the gate refuses is
   the failure mode in the other direction.

## Notes

The test that covered this area,
`test_an_epic_is_not_completed_over_slices_this_checkout_cannot_see`, calls
`st.start(epic.slug)` before completing — moving the epic to `active`, where
`(active, completed)` is a legal transition outright, so `from_backlog_epic` is
never consulted and `--force` appears to work. The fixture made the bug
impossible to observe. The new tests assert the epic's status is `backlog`
before acting, so the same drift cannot recur silently.
