# Fail fast with clear errors on non-Git writes

## Origin

Found by the repo-wide sweep in
`2026-07-29-resolve-relative-connected-projects-paths-against-the-main-worktree-root`
(see its `spec.md`, Non-goals, and its `plan.md`, Notes). Out of scope there —
that item's Goal 4 was only that it must not make the git requirement *worse*.

## Product changes

TCW's **reads** already work without git. In a tree with no repository anywhere,
`tcw work list`, `tcw validate` and `tcw work nodes` all exit 0 — measured at
`d795ac9` and again after the worktree fix, byte-identical output both times.

TCW's documented and tested contract requires Git for **writes**, but the
failure behavior is inconsistent:

- `tcw work new` dies with an unhandled `CalledProcessError` from `git_stage`
  (`tcw/store/fs.py:640` → `:262`) — a traceback, not a message.
- `tcw init` refuses outright (`tcw/cli.py:30`): "not inside a git repository.
  Run `git init` first."

Read-only commands remain supported outside Git. Write commands must fail before
creating or modifying TCW files and explain that a repository is required.

## Technical changes

Preserve the Git-required write contract pinned by README and tests. Enumerate
all filesystem-backed write entry points during specification, then centralize
an early repository precondition where possible. Acceptance requires:

- `tcw init` and `tcw work new` refuse before any partial files are written;
- their CLI diagnostics are concise and consistent, with no Python traceback;
- read-only commands continue to work outside Git;
- tests cover both clean refusal and absence of filesystem mutations.

This item owns the generic `subprocess.CalledProcessError` handling contract at
the top-level CLI boundary: unexpected Git subprocess failures render a concise
message and exit nonzero. The handler must remain generic rather than embedding
work-command-specific policy. The symlink-containment item may benefit from that
boundary but does not block on it.

## Meta changes

This is user-facing error behavior. Update `docs/changelogs/upcoming.md`,
`docs/release-notes/upcoming.md`, and the driving `tcw-work` skill. The
non-git-graph assertions in `tests/test_environment_hardness.py`
(`TestWorktreeNode.test_non_git_graph_is_unaffected`) pin today's read
behavior and should keep passing.
