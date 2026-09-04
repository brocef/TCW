# Outcome — A partial graph lets the epic completion gate and the node check fail open

## What shipped

1. **`WorkStore.incomplete_graph_note()`** — the question "can this store see the
   whole project graph?", asked on the storage-neutral interface and defaulting
   to `""`. The FS adapter already had the answer as a private helper on
   `FsWorkStore`; the completion gate lives in `WorkStore`, so the answer had to
   become something the base class could ask for. The docstring argues why the
   question is not filesystem-specific: any adapter with a partial view — a
   tracker without access to a project, a checkout without a repository — owes
   its callers the same sentence, because a relation it cannot follow resolves
   to *nothing* and nothing reads as "there is no such relation".

2. **The completion gate refuses on a partial graph.** `complete` asked
   `initiative_children` and read an empty list as "no open children". Since
   unreachable nodes stopped being fatal, that list is short rather than
   complete, and an epic in a node whose slices live in an absent child
   completed over them. It now raises, names the missing projects, and offers
   `--force` — the same shape the `start` gate already used for the same hazard,
   which is the gate *without* the destructive consequence.

3. **`epic_completable` returns False on a partial graph.** Same reasoning, one
   line: the honest answer is "not knowable from this checkout", and of the two
   available answers that is the one that does not invite a destructive action.

4. **A directory that is not a tcw node fails `require_valid()` again.**
   `_read_config` reclassified a missing config as an unreachable edge, and
   `_unreachable_edge` returns early when there is no project id — which is
   exactly the case for the root's own config, because `_load_graph` visits it
   with `declared_id=None`. Nothing was recorded, so `check()` came back empty
   and every helper built on `require_valid()` answered "no parent, no children,
   valid" for any directory on the disk. The fail-open is argued for *targets*
   ("this checkout does not have that project") and says nothing about the node
   the command was run in; the root's own config is now separated out and stays
   a problem.

## Tests

```
$ python -m pytest -q -p no:randomly tests/
6 failed, 2329 passed in 349.45s (0:05:49)
```

Four of the six are environmental and unrelated: three `chmod`-based tests that
cannot fail as root (`test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`,
two in `test_store_editor.py`), and `test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel`,
which cannot build a wheel in this container (`AttributeError: install_layout`
from the distribution's patched setuptools under `--no-build-isolation`). The
other two were this item's own tests failing against a partially reverted tree
and pass now.

New tests: `tests/test_epic_completable.py` gains a completion attempt over a
partial graph (refused, naming the missing project) and an `epic_completable`
case where every *visible* child is resolved and the answer is still False;
`tests/test_project_registry.py` gains a directory with no `tcw-config.yaml`,
asserting `check()` reports it and `require_valid()` raises.

## Autonomous decisions

Codex is unavailable in this container, so the second advisor was not available
for this run and the only external consult was a single Opus subagent — used on
the delete-safety item, not this one. Recorded here because the skill's two-
advisor rule was not met and a reader of this trail should not assume it was.

1. **Whether the gate should refuse or warn.** Decided alone; the finding
   settles it. The gate's entire purpose is to refuse closing an epic over open
   children, and a warning that scrolls past is indistinguishable from silence
   for the one consequence that strands work. `--force` keeps the escape hatch
   the rest of the gate already has.
2. **Where the note belongs.** Decided alone. Putting it on `WorkStore` rather
   than passing a string into `complete` is what makes it impossible for a
   second adapter to acquire a partial view and forget to say so.

## Notes

The two findings are the same mistake in two places: a fail-open written for one
audience (a target project this checkout does not have) applied to another (the
node you are standing in, and a gate whose empty answer is destructive). Both
were introduced by making unreachable projects non-fatal, which was the right
change; neither was visible without asking what each caller does with an empty
answer.
