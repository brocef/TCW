## Added

- `tcw/store/manifest.py`: `ManifestEntry` and `parse_manifest`, which reads
  `.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml` (`tcw-version`,
  `projects:` mapping an ID to a relative path, or to `path`, `repository`
  written `<url>#<branch>`, and `subfolder`). Any problem means the manifest
  gives no entries; an absolute or `~` path is refused in the shared file.
  (TCW-107)
- `tcw/project_files.py`: `MANIFEST`, `LOCAL_MANIFEST`, `SKIP_VARIABLE` and
  `personal_files_skipped()`; `PROJECT_ID_PATTERN`, `RESERVED_PROJECT_IDS` and
  `validate_project_id` moved here from `tcw/store/project.py`. (TCW-107)
- `FsProjectRegistry.project_folder(project_id, named_by)`: a project's folder
  from its ID, through `TCW_PROJECT_<ID>`, the manifests of the naming project
  and its family (ancestors nearest first, descendants breadth first, personal
  before shared), then the folders next to the naming project and those
  enclosing it. Each answer is kept for the command; one ID found in two
  folders is a duplicate. `found(project_id)` says how. `manifest_files()` and
  `manifest_findings()` for `tcw validate`. (TCW-107)
- `tcw.errors.ProjectGraphError` and its subclass `UnknownProject`;
  `Unreachable` takes `project` and `repository`. (TCW-107)
- `tcw projects list --json`: `found` on each row. (TCW-107)
- `tcw validate`: every entry of the current project's two manifests is
  checked; a committed entry overridden on this machine, when wrong, is a
  warning; a
  tracked `.tcw/tcw-manifest.local.yaml` is a warning. (TCW-107)
- `tcw.store.project.personal_file(root, name)`: in a linked worktree with no
  personal file of its own, the main checkout's; `Origin.root` in
  `tcw/config.py` so a borrowed file is read as the worktree's. (TCW-107)
- `tcw.store.project.begin_command`, `end_command`, `forget_registries`:
  one `FsProjectRegistry` per project root while a command runs, dropped after
  `_atomic_write_all` writes a `tcw-config.yaml` or a manifest. Called from
  `tcw.config.begin_command` and `end_command`. (TCW-107)

## Changed

- `projects:` entries name IDs only: `parse_connected_entry` accepts an empty
  entry, `{}` or a mapping holding only `jira`, and refuses a string, `path`
  or `repository` with the manifest entry to write. `ConnectedProject` keeps
  `id` and `jira`; `UnreachableProject` drops `declaration` and gains
  `message`, `decided_by` and `repository`. (TCW-107)
- The graph walk goes parent, children, then upstreams, and every edge goes
  through the lookup. (TCW-107)
- A project not on this machine is reported as `project '<id>' is not on this
  machine: <manifest> places it at <path>`, with `, from <repository>; fetch
  it with 'tcw project provision <id>'` when the entry gives one, or that no
  manifest lists it and where to add it: in `tcw validate`,
  `unreachable_project_note`, `open_project` and delegation's refusal.
  (TCW-107)
- `checkout_of` matches a store's repository against manifest entries, in the
  lookup's order, removing the entry's `subfolder` from the found folder.
  (TCW-107)
- `tcw provision` fetches component stores only; its help says so. (TCW-107)
- `tcw init` adds `/tcw-manifest.local.yaml` to `.tcw/.gitignore` too;
  `ignore_personal_file` is `ignore_personal_files`. (TCW-107)
- In a linked worktree, the search for a project's folder lists the folders
  next to the main checkout and those enclosing it. (TCW-107)
- On macOS only, the search for a project's folder never tests `Desktop`,
  `Documents` or `Downloads` directly in the home folder as a folder next to
  a project, unless the project is already inside one. (TCW-107)
- A manifest entry whose `repository` URL or branch begins with `-` is
  refused as a manifest problem, so it can never reach git as an option.
  (TCW-107)

## Removed

- `tcw.cli._declared_projects_in_graph` and `_provision_projects`;
  `tcw.store.fs.declared_connected_projects`. (TCW-107)
- The 3.x location ladder `_target_path`, `_points_elsewhere`, the "does not
  point back" problems, and `FsProjectRegistry.misdirected` with its
  `tcw validate` warning. (TCW-107)

## Internal

- `tests/projectfiles.py`: `manifest_file`, `write_manifest`,
  `write_connected_config` and `write_connected_config_file`, which move a 3.x
  location under `projects:` into the root's manifest; the test fixtures use
  them. `tests/conftest.py` overrides `tmp_path` with a folder alone in its
  parent, so the search never finds another test's projects. (TCW-107)
