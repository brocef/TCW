# Spec — Deterministic version-cut script

## Goal

`python scripts/cut_version.py <patch|minor|major|X.Y.Z>` performs the whole
version-cut mechanically, so future cuts don't need an agent to hand-edit files.

## Behavior

1. Resolve repo root from the script location (cwd-independent).
2. Read the current version from all 5 version files; **abort on drift**
   (they must already agree — `test_plugin_manifests.py` invariant).
3. Compute the next version: `patch|minor|major` increment, or an explicit
   `X.Y.Z`. Abort if it equals the current version.
4. Rewrite the version in all 5 files (exactly one substitution each; abort if
   a file doesn't match exactly once). `.agents/plugins/marketplace.json` is
   never touched (it carries no version).
5. `git mv docs/{changelogs,release-notes}/upcoming.md → v{version}.md`, then
   write fresh `upcoming.md` files (header templates preserved).
6. Stage the version files + fresh `upcoming.md`, `git commit -m
   "chore(release): cut v{version}"`, `git tag v{version}`.
7. Print a push reminder. **Does not push** — publishing stays a human step.

## Design

- Pure, importable functions — `current_version(root)`, `next_version(cur,
  bump)`, `bump_files(root, old, new)`, `rotate_upcoming(root, version)` —
  plus `main(argv, root=None)` for the git side-effects (`root` injectable for
  tests).
- Self-checking by construction: one version string written to all 5 files, so
  agreement is guaranteed; the `n != 1` substitution guard catches format drift.

## Out of scope

Writing changelog/release-note *entries* (those land in `upcoming.md` during
doc-sync, before a cut) and pushing.

## Litmus / capabilities

No store-interface or `tcw` CLI change; no product delta → no capabilities gate.
