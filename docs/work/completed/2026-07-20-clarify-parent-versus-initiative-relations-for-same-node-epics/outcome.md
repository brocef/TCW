Work completed successfully.

## Changes

- Updated the `tcw-work` router and quick reference to distinguish coupled
  nested decomposition (`--parent`) from independently scheduled epic tasks
  (`--initiative`).
- Rewrote epic planning guidance to choose the relation by scheduling behavior,
  explicitly documenting same-node initiative children and cross-node
  delegation as two realizations of the same epic relation.
- Updated decomposition guidance to warn that independently transitioning a
  nested child de-nests it and to route independent same-node tasks through
  `--initiative` so `reconcile` includes them.
- Preserved all CLI and store behavior. The optional `edit --parent` enhancement
  from GitHub issue #6 remains out of scope.

## Verification

- `git diff --check` passed.
- `tcw validate` passed.
- Targeted searches found none of the superseded same-node-versus-cross-node
  routing phrases in the changed guidance.
- Manual diff review confirmed the router and both references use the same
  scheduling-based distinction.

## Documentation Sync

- `skills/tcw-work/SKILL.md`: updated because it is the affected agent-facing
  component surface.
- `README.md`: not triggered; public CLI behavior is unchanged.
- `docs/release-notes/upcoming.md`: not triggered; user-facing behavior is
  unchanged.
- `docs/changelogs/upcoming.md`: not triggered; there is no code change.
