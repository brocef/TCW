# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw capabilities rm <path>`** (`tcw/capabilities/cli.py`). Drives the
  existing `CapabilitiesStore.remove`, which no command reached before. Prints
  `Removed capability <path>`; stages the deletion and does not commit, like
  `tcw taxonomy rm`. `rm` joins `SUBCOMMANDS`, so it is not rewritten to `show`.
- **`removed:` in a work item's `capabilities.yaml`.** `declared_capabilities`
  (`tcw/store/base.py`) returns a third list, `removed`, read with the same rules
  as `new:`/`changed:`. `capability_gate` (`tcw/work/recursion.py`) refuses a
  `removed:` path that still resolves (`declared (removed) but still resolves`)
  or is ambiguous, and no longer skips a sidecar holding only `removed:`. The
  epic rollup prints `removed <path>` rows.

## Changed

- **`FsCapabilitiesStore.remove` refuses instead of cascading.** It ran `git rm
  -rf` on the capability's folder, so a capability nested under the path was
  deleted with it, and a `Superseded by`, `Blocked by`, `Roles` or `When`
  reference to the target was left dangling. It now refuses both, naming the
  nested paths or each `<folder> (<field>)` referrer (local capabilities and
  override folders; tokens that do not resolve are ignored), and writes nothing.
  The inherited refusal also names `tcw capabilities reset`. The contract is
  documented on the abstract `CapabilitiesStore.remove`.
- `FsCapabilitiesStore.reset`'s refusal for a standalone local capability names
  `tcw capabilities rm` instead of the non-existent `remove` command; so do
  `skills/tcw-capabilities/SKILL.md`, `docs/guide/taxonomy-and-capabilities.md`
  and the `capabilities/reset-an-override` ledger entry.
