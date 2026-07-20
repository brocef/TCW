Work completed successfully.

## Changes

- `tcw work list -i|--incl-desc|--include-descendants` now builds an aggregate
  ownership forest across the anchor and registered descendant nodes. Visible
  initiative tasks are indented beneath their local or ancestor epic, retain
  project-qualified slugs, and are emitted once.
- Local nested-parent rendering, board ordering, node headers, status/all/tag
  filters, and registered-graph boundaries remain intact.
- Added both requested aliases without changing the existing long flag.
- Confirmed tag registration already existed as `tcw work tags add <tag>...` and
  documented the complete tag vocabulary lifecycle instead of adding a duplicate
  command.
- Updated planning guidance to choose/register/apply useful tags and backlog
  audit guidance to recommend tag additions/removals, applying them only after
  the audit's existing user-approval gate.
- Updated the driving skill, README, both affected capability descriptions,
  release notes, and developer changelog.
- Dogfooded the workflow by registering `cli` and `docs` and applying both tags
  to this work item.

## Verification

- `python -m pytest tests/test_work.py -q` — 106 passed.
- `python -m pytest -q` — 653 passed after rerunning outside the socket-restricted
  sandbox; the first sandbox run reached 517 passes but server tests could not
  bind loopback sockets.
- `python -m pytest tests/test_plugin_manifests.py -q` — 4 passed.
- `tcw capabilities check` — OK.
- `tcw validate` — OK.
- `git diff --check` — clean.
- Manual `tcw work list -i` smoke test — successful on this repository.

## Deviations and decisions

- No new tag-registration CLI was added because `tcw work tags add` already
  provides that exact public operation with store abstraction and tests.
- Aggregate node headers are preserved. A descendant task rendered beneath an
  ancestor epic is not repeated under its later node header, so that node group
  may contain only its header when all visible items are owned elsewhere.

## Documentation Sync

All triggered entries were updated: `README.md`, upcoming release notes,
upcoming developer changelog, and `skills/tcw-work/SKILL.md`.

## Release

The user explicitly approved a patch version after verification and TCW
completion. The release has not yet been cut at this checkpoint.
