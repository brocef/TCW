# Outcome — An unreachable project is reported as never declared by nodes, escalate and delegate

## What shipped

### The relation survives the project being absent

`registered_parent` and `registered_children` read `registry.parent()` and
`registry.children()`, which answer with `Project`s — so they can only answer for
a project this checkout actually has. Every declared-but-unreachable relation
therefore looked exactly like "never declared", which is the one thing
`UnreachableProject` exists to prevent, and which three separate pieces of this
work's own prose promise does not happen.

1. **`ProjectRegistry.declared_parent_id()` and `declared_child_ids()`** join the
   storage-neutral interface. An id is known from the declaration alone, so it is
   answerable whether or not the project can be reached — which is exactly the
   property `parent()`/`children()` lack. The defaults are the reachable answers,
   correct for a store that always sees the whole graph.
2. **`unreachable_parent()` and `unreachable_children()`** in the FS adapter,
   built from those ids and `unreachable_project()`.
3. **Three commands stop erasing the relation.** `tcw work nodes` prints
   `<id>  (not in this checkout)` on the parent line and in the children list,
   rather than `(none — root)` and `(none — leaf)`. `tcw work escalate` names the
   project and its remedy — via the existing `unreachable_project_note`, so it
   says `run tcw provision` where a repository is declared — instead of "this is
   the root". `tcw work delegate` says the child is declared and not here instead
   of "no child node", which used to send the reader to add a declaration already
   in their config.

### The locator that nothing reported

A reciprocal locator that points at a path this machine does not have, for a
project the graph reached by the other route, fell through everything:
`_points_elsewhere` returns False on an absent target (deliberately — an absent
target cannot answer the question), and `unreachable()` filters the entry out
because the project *is* in `_by_id`.

`FsProjectRegistry.misdirected()` is that set, and `tcw validate` prints it,
never counted and never fatal. **It is deliberately not a problem.** Nothing on
disk separates a typo from a locator that is simply right for another machine,
and in a workspace whose repositories sit differently on different disks the
second is routine — it is the failure the fail-open was introduced to fix. So the
message states both facts and draws no conclusion: declared at *this* path, which
is not here; found at *that* one.

## Tests

Eight new tests, all confirmed to fail beforehand.

`tests/test_project_registry.py`: a declared parent and a declared child that are
absent are still reported by the declared-id queries while `parent()`/`children()`
answer nothing; the misdirected locator is reported *and* `check()` is asserted
empty, because "not a problem" is half of what the fix is; and a correct pair is
asserted never misdirected, which is the guarantee a looser predicate would break.

`tests/test_multiproject.py`: `tcw work nodes` names an absent parent and an
absent child, `escalate` and `delegate` name the project — each asserting the old
wording is *absent* as well as the new one present, since all four cases already
produced output and what was wrong was what it said.

```
$ python -m pytest -q -p no:randomly tests/
(see the closeout; four environmental failures, everything else green)
```

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted.

1. **Whether the misdirected locator should be a problem.** No, and this is the
   decision with the most consequence. Making it one would restore the exact
   failure the unreachable fail-open was written to fix — a monorepo nested
   inside an orchestrator on one disk and cloned beside it on another has this
   shape on every machine but the author's. Reporting without judging is the only
   option that helps a typo without breaking a legitimate layout.
2. **Where the declared-id queries belong.** On `ProjectRegistry`, with
   reachable-answer defaults, rather than only on the FS registry. The question
   is not filesystem-shaped: a tracker knows which projects it was told about and
   cannot open. Giving the ABC a default means an adapter that always sees
   everything inherits the right answer and cannot get it wrong.
3. **Whether `tcw work nodes` should mark an absent relation the same way it
   marks a board-less one.** Different wording, deliberately: `(no work store)`
   and `(work store not provisioned here)` are about the *board*, and
   `(not in this checkout)` is about the *project*. Reusing a marker would make
   three distinguishable states read as two.

## Notes

The review found this by reading the comments this work wrote and checking them
against the code — `child_nodes`' "What none of them may do is imply the absent
node was never declared", `escalate`'s "telling a user the node is the root when
it plainly has a parent", and README's promise. All three were true of the
message they were written next to, and false of the three commands that reach the
same state by a different route.
