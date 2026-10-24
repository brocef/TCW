# Implement round 3 — TCW-115

## Why this round exists

TCW-115 was reviewed and accepted on its own branch (review round 2). Since
then TCW-113 ("--scope, --project, and a project's whole family") has landed
on `v4`, and the dispatching session rebased `impl-115` onto it. With both
items together the full suite had two failures, and review round 1 had
carried one concern about TCW-113's code forward. This round makes the two
items agree. It was worked on the branch `impl-115` in the worktree
`.claude/worktrees/impl-115`, with that worktree's own virtual environment
(`.venv/bin/pytest`). No `tcw` command was run by hand, no lifecycle command
was run, and no ticket was moved or written to: the dispatching session makes
every move. It gives no verdict.

## The rebase conflicts, checked

The dispatching session resolved three conflicts; each was read again here
and left as it was.

- `tests/test_migration_guide.py`: `REMOVED_AFTER_3_0` keeps TCW-113's
  `tcw capabilities list --local` row and every one of TCW-115's moved
  commands. Both sets are commands the 3.0 guide names and 4.0 lacks, so
  both belong.
- `tcw/capabilities/cli.py` and `tcw/taxonomy/cli.py`: TCW-113's `_missing()`
  helper is kept, because `covered_for` takes it as the error for a project
  with no store, and its text names TCW-115's `tcw project new <axis> --id
  <id>`, which is what TCW-115 Design 1.2 asks of that message.

## The failures, and what was done

1. **`tests/test_families.py::test_shared_names_its_parent_and_children`**
   ran `tcw projects list`, which TCW-115 renamed. It now runs
   `tcw project list`. Every file a `TCW-113:` commit touched was searched
   for the four removed command names (`tcw init`, `tcw provision`,
   `tcw projects`, `tcw config show`) in code, tests, the web client
   (`web/client/src`), skills, the capability and taxonomy records and the
   guides. Nothing else was found: the remaining matches are the migration
   guide's own list of removed commands, and older items' upcoming changelog
   entries, which describe what those items did when they were written.

2. **`tests/test_project_provision.py::test_ac38_another_projects_store`**
   expected `tcw taxonomy list` in `app` (which inherits `core`'s taxonomy,
   whose store is declared in a repository and not fetched) to exit 7. With
   TCW-113 it warns and exits 0. See decision 1. The test now checks that
   the default scope exits 0 and that `--scope up` exits 7, and that both
   messages contain `tcw -C <core's folder> project provision --component
   taxonomy`. The check in `core` itself (no `-C`) is unchanged.

3. **A child's work store not on this machine** (review round 1's carried
   concern). TCW-113's `tcw/work/scoped.py` opens each other project's work
   store with `open_backend(root, personal=False, registry=...)`, and the
   work store's location was resolved with no active project's folder, so
   the message said `run tcw project provision --component work`. Run in
   the active project, that fetches the active project's own store, which
   is what TCW-115 Design 7.2 rules out. Confirmed with a new test before
   the change: `tcw work list --scope down` in `shared`, with `server`'s
   work store declared in a repository and absent, warned exactly that.

   The fix: `WorkLocation.open` (`tcw/store/fs.py`) and `work_path`
   (`tcw/work/open.py`) take `active_root`, which they pass to
   `resolve_store` as the tree stores already do. `project_facts` passes the
   command's registry's folder (`registry.project_root`, the active
   project's folder, since the registry is always opened there) when a
   project is read for itself (`personal=False`). Every caller that reads
   another project's work store goes through `project_facts`, so
   `work list`, `work show`, `children`, `blocks` and reference checks get
   the `-C` form without each being changed. The warning now says
   `run tcw -C <server's folder> project provision --component work`.

## Decisions

1. **The default scope degrades; a scope that needs the view stops.**
   *Decided by the implementing agent.* TCW-115's AC 38 says `tcw taxonomy
   list` in `app` "exits 7 (TCW-112 Design 1.3's third message)". It was
   written when `list` always needed the project's view. TCW-113 Design 4.9
   later made `own` the default scope and made `own` read the project's own
   declarations without its view (warning, exit 0), as TCW-112's `--local`
   did, while `up`, `down` and `all` stop with exit 7. The two specs
   conflict only on the exit code of the default command. TCW-115 landed
   later, so it gives way: AC 38's purpose is that the message for another
   project's store names the command run in that project's folder, and that
   purpose holds under both outcomes, since the warning carries the same
   message. The test now proves it under both: the default scope (exit 0)
   and `--scope up` (exit 7).

2. **The active folder comes from the registry, not from each caller.**
   Every `personal=False` caller already passes the command's registry, and
   `Locator.root` is that registry's `project_root`, so `project_facts` reads
   it there instead of a new argument being added to `open_backend`,
   `item_folders` and every scoped reader. A project read for itself with no
   registry keeps the old message; no caller does that today.

## Tests and mutation checks

New: `tests/work/test_scope_work.py::test_a_descendants_work_store_not_provisioned_here_is_fetched_in_its_folder`.
Changed: `tests/test_families.py::test_shared_names_its_parent_and_children`
(the command name) and `tests/test_project_provision.py::test_ac38_another_projects_store`
(decision 1).

Mutation checks, each restored afterwards:

- `project_facts` made to pass no active folder (`None if True or ...`): the
  new test goes red, its assertion showing the warning with
  `run tcw project provision --component work` and no `-C`.
- `resolve_store`'s `-C` branch disabled (`if False:`): both the new test and
  AC 38's test go red, for the missing `-C` form.

Run in the foreground from the worktree's root with
`.venv/bin/pytest -q -p no:cacheprovider`, one folder at a time:

- `tests/test_families.py tests/test_project_provision.py tests/test_scope_trees.py tests/test_scope_reader.py tests/test_scope_members.py tests/test_store_provisioning.py tests/test_tree_parent_missing.py tests/test_upstream_projects.py tests/test_tree_inheritance.py`: 425 passed, 37 skipped.
- `tests/test_capabilities.py tests/test_cli_handler.py tests/test_config_edit_writers.py tests/test_environment_hardness.py tests/test_inherited_config.py tests/test_owning_project.py tests/test_ownership.py tests/test_store_addresses.py tests/test_migration_guide.py tests/test_parent_links_cli.py tests/test_tree_full_identifiers.py`: 658 passed, 17 skipped.
- `tests/work`: 1725 passed, 2 skipped.
- `tests/serve`: 447 passed.

## Documentation

The upcoming changelog entry's `StoreNotProvisioned` line now says the `-C`
form also covers the work store of a project read for itself, and names
`active_root` on `WorkLocation.open` and `work_path`. The release note
describes no behaviour this round changes, so it is unchanged.

## The suite

The full suite is run by the dispatching session, as CI runs it.

The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, run by
the dispatching session on the branch at `403f0319` (2026-10-24), rebased onto
`v4` with TCW-113's implement round 2, in two halves by folder: `2175 passed,
2 skipped` and `5108 passed, 111 skipped`. `pnpm test` `229 passed`;
`tsc --noEmit`, `pnpm lint` and `pnpm check:build` clean.
