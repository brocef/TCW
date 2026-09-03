# Outcome — Unreachable connected projects degrade instead of failing every command

## What shipped

Seven planned tasks, landed as six commits — task 6 merged into task 2, see
Corrections.

1. **`6d74a6a` — separate unreachable projects from graph problems.**
   `UnreachableProject` and `ProjectRegistry.unreachable()` on the
   storage-neutral interface (`tcw/store/base.py`), a second accumulator and
   `_unreachable_edge` / `unreachable_project` on `FsProjectRegistry`. Nothing
   recorded one yet, so behavior was unchanged.
2. **`d4799bf` — reclassify the absent target, and report it.** `_read_config`'s
   `not path.is_file()` branch records an unreachable edge instead of a problem;
   every other branch stays an error. `_visit` and `_read_config` now carry the
   declaring config path, so the record names *where* the declaration is rather
   than only what it pointed at. `tcw validate` prints every unreachable edge,
   uncounted and non-fatal.
3. **`28ba848` — reciprocity.** `_points_elsewhere` replaces two direct path
   comparisons: an absent counterpart cannot answer the question and no longer
   answers it wrongly.
4. **`182ea17` — name the absent project.** One renderer,
   `unreachable_project_note`, used by `extends`, `qualified_work_ref_problem`
   and `FsCapabilitiesStore.extends_add` (a fourth site the spec had not found —
   see Corrections).
5. **`8739700` — the partial-graph note.** The `start` gate reported an
   unresolvable epic as an inactive one; it now says it cannot resolve it and
   names the missing projects. The three graph-enumerating helpers and
   `validate`'s duplicate-work-root scan carry the decision they now imply,
   recorded in comments as the plan required.
6. **`1389a5a` — documentation.** README, release notes, changelog, the
   `cli/host-multiple-projects-in-one-repo` capability body, and two `tcw-work`
   skill references.

## Tests

Full suite, on the final tree:

```
$ python -m pytest -q tests/ -p no:randomly
4 failed, 2245 passed in 353.36s (0:05:53)

FAILED tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path
FAILED tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel
FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure
FAILED tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure
```

**All four fail identically at `b04c7e7` (the v1.2.3 tag), before any change in
this item** — verified by checking out the tag and running just those tests:
`5 failed in 3.78s` (the fifth,
`test_generate_hook.py::test_a_grandchild_does_not_survive_the_timeout`, is
timing-sensitive and passed on the final run). They are environmental: this
session runs as root, so the `PermissionError` assertions cannot fire, and the
wheel test needs a build this container does not do.

New tests: 8 in `tests/test_project_registry.py`, 2 in `tests/test_validate.py`,
1 in `tests/test_qualified_ref.py`, 3 in `tests/test_capabilities_federation.py`,
1 in `tests/test_recursion.py`, 1 in `tests/test_validate_target.py`.

### Acceptance criteria, against the real checkout

Run in `apps/server` of the `proposit-app` clone in this session, which has no
orchestration repository:

1. **`tcw work list` no longer reports a graph problem.** It now reports
   `no tcw work node here` — which is criterion 1 met (the graph stopped
   failing) and the *store* problem this item does not fix. `work.path` names a
   directory only the author's machine has and there is no `repository`
   declaration yet; that is the blocked follow-up item.
2. **`tcw work nodes`** — same store-level answer, same reason.
3. **`tcw validate`** exits 0 and prints
   `.../apps/server/tcw-config.yaml: connected project 'proposit-app' is declared but not reachable in this checkout (/home/user)`.
   With the in-repo `proposit-shared` edge declared temporarily, the seven
   `extends project 'proposit-shared' is not reachable` problems drop to **zero**
   and only `proposit-core` remains — criterion 3, and the exact result the spec
   predicted.
4-6. Reciprocity and fail-closed cases: `tests/test_project_registry.py`.
7-8. `tcw validate` exits 0 for an absent parent alone and non-zero with a real
   error beside it (`tests/test_validate.py`); `check()` and `unreachable()` are
   separate APIs.
9. No command reports "no tcw node here" for a present config with an absent
   connected project — the message above is a *store* message, not a node one.

## Corrections

- **Plan task 6 merged into task 2.** Splitting them would have shipped a commit
  where `check()` no longer carried the absent-target problem and `tcw validate`
  did not yet report it — an intermediate state that silently drops information
  from a user-facing command. The plan's own rule is that a task leaving the tree
  in a worse state is not a task boundary.
- **`check()` returns errors only**, not "every problem, errors first" as task 1
  wrote. Returning unreachable edges from it would have kept `tcw validate`'s
  early return fatal, defeating the item. `unreachable()` is the second channel
  and satisfies criterion 8.
- **A fourth message site.** The spec named three;
  `FsCapabilitiesStore.extends_add` is a fourth, and the one a user in a cloud
  checkout hits first when running `tcw capabilities extends <sibling>`. Fixed in
  the same commit.
- **`registered_project_id` needed no change.** The spec listed it as a message
  site, but it resolves a *path* to an id, and an unreachable node has no path on
  this machine for anyone to pass it. Left alone.
- **No `tcw validate --json`.** Criterion 8 offered "`--json` (or `check()`)";
  `tcw validate` has no JSON output at all, so the separation is the API one.
  Adding a JSON surface to `validate` is out of scope and would be its own item.

## Notes

The one criterion this item cannot close on its own is the store: `work.path`
still names an absent directory, and `tcw work list` in a cloud checkout still
refuses. That is the blocked follow-up item, and it is the reason this one was
scheduled first rather than the reason it is incomplete.
