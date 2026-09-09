# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- **`TCW_PROJECT_<ID>` overrides a connected project's locator for this machine.**
  The name maps from the project id by uppercasing and replacing `-` with `_`;
  the mapping is injective because `PROJECT_ID_PATTERN` admits neither an
  underscore nor an uppercase letter. Consulted in `FsProjectRegistry._target_path`
  as rule 0, **above** the declared locator and the `repository` declaration —
  the motivating case is a locator that resolves to the wrong existing node,
  which no rung below rule 1 can reach. A relative value resolves against the
  process's working directory, not the declaring config.
  - Absent path → falls through to the declaration; not a problem.
  - Directory present without `tcw-config.yaml` → `check()` problem naming the
    variable and the path; does not fall through, and is not additionally
    reported as unreachable.
  - Node present with a different id → the existing `_read_config` mismatch
    check reports it, naming both ids.
- **`ProjectOverride` and `ProjectRegistry.overrides()`** in `tcw/store/base.py`.
  Concrete default returning `[]`, so no existing adapter changed. The value
  stays opaque like `Project.locator`; `source` names whatever supplied it.
- **`tcw validate` reports active overrides**, one line each, on stderr, before
  the graph-problem block — that block returns, so a line after it is absent from
  the run where a wrong override is being diagnosed. Never counted, never fatal.

### Internal

- `_provision_nodes` needed no change: it decides whether to fetch by asking the
  registry where a project is, so rule 0 applies to provisioning for free. Now
  pinned by tests rather than assumed.
- Suite-wide autouse fixture in `tests/conftest.py` clears `TCW_PROJECT_*`.
  Without it a single exported variable fails a large fraction of
  `tests/test_project_registry.py`, and "with no variable set nothing changes" is
  not assertable.
