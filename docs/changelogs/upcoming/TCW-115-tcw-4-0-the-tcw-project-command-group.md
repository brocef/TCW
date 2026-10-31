## Added

- `tcw project` command group (`tcw/project_cli.py`), registered after
  `work`, with the verbs `new`, `list`, `config`, `provision`, `path` and
  `info`. (TCW-115)
- `tcw project path [<id>]`: the folder of a project on this machine; exit 5
  when not here (naming `tcw project provision <id>` when the entry gives a
  repository), 1 for an unknown ID, 2 for an invalid one. (TCW-115)
- `tcw project info [--json]`: ID, folder, parents (with `inherit`), children
  (with `personal`), load order and its warning, settings with their origin,
  store folders or their reasons, overrides, and the same-path counts;
  `ProjectInfo`, `project_info`, `render_text`, `render_json`. (TCW-115)
- `tcw project provision <id>` and the projects pass, `tcw/provision.py`:
  `provision_projects`, rounds of `_round_ids`, checks `_dash_problem`,
  `_bound_problem` (Design 7.8), `_folder_state`/`_folder_problem`,
  `_group_round` (one clone per repository folder), `_changed_answer` (answers
  kept for the run), `same_folder`, `repository_top`, `RepositoryUnknown`.
  (TCW-115)
- `tcw/store/fs.py` `fetch_project` and `FetchRefused`: clone into
  `.tcw-staging-<hex>` beside the target (five names tried), check the clone
  without following a link out of it, recheck the target, and rename in
  through a held parent folder. (TCW-115)
- `FsProjectRegistry.placements()`, `entry_elsewhere()`, `occupied_ids()`, and
  `require_valid(fetching=True)`, which leaves out an entry folder that holds
  files and no project so provisioning can refuse that project alone.
  (TCW-115)
- `GraphProblems`, the `ValueError` that `require_valid` raises, carrying
  `files`, the file each problem is about; `tcw project provision` names the
  fetched project whose own folder holds it (`_holding`), or none. (TCW-115)
- `tcw project provision` refuses a target folder that cannot be listed,
  naming it and its manifest entry. (TCW-115)
- `tcw/store/project.py` `GIT_LOCATION_VARIABLES` and `git_environment()`.
  (TCW-115)
- `tcw/cli_suggest.py` `REMOVED_COMMANDS`; `tcw/config_cli.py`
  `origin_label` and `origin_json`. (TCW-115)

## Changed

- The suggester offers a synonym valid at the level typed before the same
  word elsewhere. (TCW-115)
- `tcw project config --origin` comments read `<project>, <layer> <file>`,
  `<project>, environment <NAME>` or `built-in`. (TCW-115)
- `run_provision`: the no-argument and `<id>` forms check the graph first; a
  failed store no longer stops the run; the stores pass's counts join the
  projects pass's last line; `<id>` with `--component` is a usage error.
  (TCW-115)
- `StoreNotProvisioned` names `tcw -C <root> project provision --component X`
  when the store is another project's, the work store of a project read for
  itself included: `WorkLocation.open` and `work_path` take `active_root`, and
  `project_facts` passes the command's registry's folder for a project read
  with `personal=False`. (TCW-115)
- Every `git` call TCW makes (`fs._git`, `_git_lines`) drops git's location
  variables. The store clone runs `git clone --quiet -- <url>` and
  `git checkout --quiet <ref> --`. (TCW-115)
- `ownership.not_here` names `tcw project provision <owner>` when a
  repository is known. (TCW-115)
- Every message, help text and comment naming a removed command names its
  replacement. (TCW-115)

## Removed

- `tcw init`, `tcw projects`, `tcw config` and `tcw provision`; each answers
  through `REMOVED_COMMANDS` with exit 2. (TCW-115)
- `PROJECT_TARGET` and its branches in `FsStoreProvisioner` and
  `_is_store_layout`. (TCW-115)

## Internal

- `tests/provision_support.py`: the stand-in `git` (refuses `clone`, `fetch`,
  `ls-remote` and `pull` unless a test allows `clone`), `make_remote`, and
  `project_files`. New `tests/test_project_provision.py`,
  `tests/test_fetch_project.py`, `tests/test_project_path.py`,
  `tests/test_project_info.py`, `tests/test_project_group.py`. (TCW-115)
- The test suite runs the new command names throughout. (TCW-115)
