## Added

- The filesystem work backend for TCW 3.0 (TCW-70), wired into `tcw work`.
  - `tcw/work/fs_backend.py`: `FsWorkBackend`, implementing TCW-69's
    `WorkBackend` over item folders that never move. Each item's properties
    live in `<item>/item.yaml`; comments are `comments/<UTC timestamp>.md`;
    `read_all` returns the readable items and the unreadable ones apart.
    Nothing is staged or committed.
  - `tcw/work/open.py`: `open_backend`, `open_project` (another project,
    by id, through the registry) and `delegate`, with the conditions on the
    target project: declared, not upstream, present, with a work store, and
    with no uncommitted changes in it, read with `--no-optional-locks`.
  - `tcw/work/record.py`: the item record shared by `show --json`,
    `list --json` and the `generate:` payload.
  - `tcw/findings.py`: `Finding`, the shape `tcw validate` prints.
  - New commands: `tcw work advance [--to] [--force --reason] [--dry-run]`,
    `discard --reason`, `comment` (text on stdin), `rename <slug>
    <new-words>`, `path <slug> [<stage>] [--next|--handoff]`,
    `new --project`, `new --stage inbox`, `edit --blocks`.
- `tcw work list` filters: `--stage`, `--tag`, `--parent`, `--assignee`,
  `--all`, `--json`.

## Changed

- `tcw work` is `tcw/work/cli.py`, rewritten on the 3.0 model. Every
  `TcwError` exits with its own code (1 error, 2 usage, 3 refused, 4 not
  found, 5 unreachable, 6 moved with a problem).
- `tcw validate`: the work checks run over `item.yaml` files — unreadable
  items, references to items that do not exist (a warning), references into
  projects that cannot be reached (`unresolved:`), stages not in the table or
  disabled, mid-work `capabilities.yaml` problems, and a work store shared by
  two projects. The summary counts only failures.
- `tcw capabilities drift` reads finished items' `capabilities.yaml` through
  `drift_problems`; it no longer reads `Planning doc`.
- `tcw://W/…` references resolve through the backend, by folder; a finished
  item resolves like any other.
- `tcw init` and `tcw work init` make one empty work folder with a
  `.gitkeep`, and no status folders or ignore rules. Moving a store refuses
  when the old one holds an item folder.
- `tcw work tags add` and `rm` write `tcw-config.yaml` without staging it,
  and work outside a git repository.
- `tcw work stage prompt` composes from `work.stages` and adds the stage
  header line itself. The packaged `spec` and `plan` prompts use
  `{{tcw:request}}` in place of `{{tcw:body}}`.
- The `generate:` payload is the 3.0 item record.
- `RESERVED_PROJECT_IDS` is `t`, `c`, `w` and `local`: the 2.x status names
  are valid project ids again.
- `STORE_CLASSES["work"]` is `WorkLocation`, which finds the work folder and
  nothing more.

## Removed

- Commands: `tcw work start`, `submit`, `rework`, `complete`, `drop`,
  `delete`, `inbox`, `tracker`, `tombstone`, `reconcile`, `delegate`,
  `escalate`, `scaffold`, `stage gate` and `stage validate`; the flags
  `list --status` and `--include-descendants`, `new --initiative` and
  `--epic`, `edit --type` and `--initiative`, and `lifecycle --transition`.
- The 2.x work store: `FsWorkStore`, status folders, `state.yaml`,
  `graveyard.yaml`, `renames.yaml`, `dod.yaml`, `tracker.yaml`, the store
  lock, per-command commits, worktree and merge helpers, publishing, and
  retention.
- `tcw/tracker/`, `tcw/harness.py`, `tcw/work/recursion.py`,
  `projection.py` and `templates.py`, and the 2.x half of `tcw/store/base.py`
  (statuses, transitions, lifecycle policy, tracker configuration,
  `WorkItem`, `WorkStore`).
- Every `tcw serve` work route except `GET /api/work` and
  `GET /api/work/tags`, which return empty lists until TCW-77.

## Internal

- The Jira HTTP client moved to `tcw/work/jira/client.py`, with its tests.
- `tests/doc_allowance.py` lists the commands, flags and keys the README,
  guides and skills may still name until TCW-74 and TCW-75 rewrite them;
  `tests/test_doc_allowance.py` checks each entry really is gone.
- `tests/not_ported.py` skips 2.x tests whose subject a later 3.0 slice
  rewrites; tests of deleted code were removed.
- New guards: no module names a 2.x store file or removed command, and no
  git command that writes is run outside `tcw provision` (and, until
  TCW-73, the taxonomy and capabilities stores' staging).
