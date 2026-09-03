# Outcome — Connected-project entries declare where they come from

## What shipped

Eight planned tasks in six commits.

1. **`58fdedf`-equivalent — `tcw/store/checkouts.py`.** The `(url, ref)` →
   working-copy-directory computation moved out of `fs.py` so `project.py` can
   use it. **Not** into `base.py` as the plan said — see Corrections.
2. **Entry mapping form.** `ConnectedProject` and `parse_connected_entry` in
   `tcw/store/base.py`, beside the other pure config parsers; `_relation` in
   `tcw/store/project.py` produces it for both forms. The `repository` half is
   parsed by the existing `parse_repository_declaration`, so a malformed
   declaration reads identically wherever it appears.
3. **The node ladder.** `_target_path` splits into `_locator_path` (rules 1 and
   2 for worktrees, unchanged) and the ladder on top: locator with a sentinel
   wins, else the provisioned checkout with a sentinel, else the locator — so the
   unreachable record names the place the user wrote.
4. **Declared-but-unprovisioned messages.** `UnreachableProject.declaration`
   carries the declaration; `unreachable_project_note` and `tcw validate` name
   the remote and say `run tcw provision`.
5. **The reader.** `declared_connected_projects` reads entries straight from a
   config, as `declared_repository` does.
6. **The walk.** `_provision_nodes` in `tcw/cli.py`, plus `NODE_TARGET` so the
   existing provisioner can obtain a node (availability is a sentinel file, and a
   repository with none at the declared path is refused before anything lands).
7. **Trust decision** recorded at the queue: report every remote before
   contacting it, `--dry-run` covers the whole walk, no consent prompt — `tcw` is
   non-interactive and a prompt would hang every script.
8. **Documentation:** README, release notes, changelog, the `tcw-work` commands
   reference, `cli/provision-declared-stores` and
   `cli/host-multiple-projects-in-one-repo` bodies; the new capability
   `cli/declare-a-connected-projects-home-repository` (`cap-596612`) flipped to
   `Supported`.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
4 failed, 2266 passed in 351.50s (0:05:51)

FAILED tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path
FAILED tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel
FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure
FAILED tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure
```

The same four environmental failures established in the previous item: they
reproduce at the `v1.2.3` tag with none of this code present.

New: 6 tests in `tests/test_project_registry.py` (including a 5-case
parametrization over malformed entries) and 7 in
`tests/test_store_provisioning.py`, all against real local git repositories —
none reaches the network.

### Against the real repositories

The decisive check, run in `apps/server` of a `proposit-app` checkout with a
temporary configuration and no other repository on disk:

```
$ tcw provision --dry-run
  work: already available
  proposit-app: already available at /root/.cache/.../proposit-orchestration-73cbcd814e44
→ proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …-proposit-core-2923c94aec1a
  proposit-core: would obtain into …-proposit-core-2923c94aec1a
  proposit-core: any projects it declares cannot be listed until it is obtained

$ tcw provision
→ proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
  proposit-core: obtained at …

$ tcw taxonomy list | grep -v '(local)' | head -3
analysis  [V] (proposit-core)
argument  [V] (proposit-core)
  claim  [V] (proposit-core)
```

Two hops from one command: `apps/server` → the declaration on its sibling
`packages/shared` → the orchestration node → the declaration on *its*
`proposit-core` child → `proposit-core`. 85 federated taxonomy entries resolve
where the `extends project 'proposit-core' is not reachable` problem used to be.
The `proposit-app` configuration used for this was scratch and has been reverted;
committing it is the consumer-side work this item put out of scope.

Acceptance criteria 1-10 are covered by the new tests; 11 is the run above.

## Corrections

- **The shared computation went to `tcw/store/checkouts.py`, not `base.py`.** The
  plan named `base.py` "where the pure (url, ref) → directory name logic
  belongs". On reading it, that is wrong: `base.py` is the storage-neutral
  interface and a cache directory is precisely the filesystem particular it
  keeps out. A module beneath both adapters serves the same purpose without
  putting `pathlib` into the abstract layer.
- **The walk collects declarations from the whole present graph, not only the
  current node.** The plan said "read the current node's `connected-projects`".
  That fails the case the item exists for: in `proposit-app` the edge out to the
  orchestration repository belongs to `packages/shared`, so `tcw provision` in
  `apps/server` found nothing and reported "Nothing to provision". Found by
  running it against the real repository, not by a test. Fixed, and the guard
  that decides there is nothing to do now asks the same question the walk does.
- **A malformed node declaration had to be checked before the early return.**
  `parse_connected_entry` fails closed, so a bad declaration produced no entries
  — which read as "nothing declared" and exited 0. It now refuses, as a
  malformed component declaration already did.
- **Task 6 was a test, not a change.** The occupied-`checkout` guard already sits
  on the shared code path; the task added the assertion and nothing else.

## Notes

`--refresh` covers nodes because it flows through the same provisioner; there is
no node-specific branch to forget.

The `tcw validate` output in a partial checkout is noisier than before: the
orchestration node declares three children at paths inside a `proposit-app`
clone that a cache checkout does not contain, so each is reported unreachable.
Correct, non-fatal, and the consumer-side configuration is where it gets tidied.
