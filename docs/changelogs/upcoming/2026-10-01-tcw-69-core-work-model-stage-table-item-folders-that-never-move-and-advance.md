## Internal

- Added TCW 3.0's work model as a library, not yet wired into any command
  (TCW-69). TCW-70 connects it to `tcw work` with the filesystem backend.
  - `tcw/work/model.py`: the `Slug` identity (`project/folder`), the `Item`
    property set and `Changes` partial updates with shared validation, and the
    stage table `STAGES`, the only place a stage is named. Navigation
    (`next_stage`, `is_skip`, `records_gate_stage`, `gates_for`) reads the
    table's columns.
  - `tcw/work/layout.py`: item folders that never move, one folder per stage,
    numbered rounds whose front matter carries `verdict` and `judges`,
    timestamped handoffs, and `current_verdict` (`none`, `invalid`, `stale`,
    `accepted`, `rejected`). Computes paths and creates nothing.
  - `tcw/work/backend.py`: the eleven-operation `WorkBackend` protocol and
    `Query`.
  - `tcw/work/advance.py`: `advance` and `discard`, the single move
    operation, with skip and reason rules, built-in gates then `pre` hooks
    for the target only, a trace note passed to `set_stage`, and `post`
    hooks.
  - `tcw/work/gates.py`: the records gate over `<item>/capabilities.yaml`
    (no `added:` alias), its mid-work form, the completion gate, drift by
    newest declaration, and `ledger_reader`, the filesystem `RecordsReader`.
  - `tcw/work/config.py`: `parse_work_config` for the 3.0 `work:` shape
    (`stages`, `hooks`, `backend`, `jira`), refusing the removed 2.x keys
    with a pointer to the migration guide.
  - `tcw/work/references.py`: reference and stage-ahead checks for
    `tcw validate`.
  - `tcw/exit.py` and `tcw/errors.py`: the exit codes and the exception
    classes that carry them.
- Tests for all of the above live in `tests/work/`, against an in-memory
  backend (`tests/work/memory_backend.py`), with structural guards that no
  module but the table spells a stage name and that none starts a process or
  writes to git.

## Changed

- `route_capability_path` and `Route` moved from `tcw/work/recursion.py` to
  `tcw/work/gates.py`; `recursion.py` imports them back, so behavior is
  unchanged.
