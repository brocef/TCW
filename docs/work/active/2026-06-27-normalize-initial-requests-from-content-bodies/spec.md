# Spec — Normalize initial requests from content bodies

## Capability changes

- No user-facing capability change. This is a repository data migration for TCW
  work artifacts.

## Behavior

- For every work item folder under `docs/work/`, copy `content.md` to
  `initial-request.md`.
- Overwrite existing `initial-request.md` files so this repo consistently treats
  the old body content as the request artifact.
- Leave `content.md` in place.

## Acceptance criteria

- Every `initial-request.md` matches the sibling `content.md`.
- `tcw work list` still shows request-stage letters for the migrated items.
- The worktree is clean after commit and completion.
