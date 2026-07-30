# Fix non-git write paths: work new and init fail outside a git repository

## Origin

Found by the repo-wide sweep in
`2026-07-29-resolve-relative-connected-projects-paths-against-the-main-worktree-root`
(see its `spec.md`, Non-goals, and its `plan.md`, Notes). Out of scope there —
that item's Goal 4 was only that it must not make the git requirement *worse*.

## Product changes

TCW's **reads** already work without git. In a tree with no repository anywhere,
`tcw work list`, `tcw validate` and `tcw work nodes` all exit 0 — measured at
`d795ac9` and again after the worktree fix, byte-identical output both times.

TCW's **writes** do not, and they fail in two different, both-unhelpful ways:

- `tcw work new` dies with an unhandled `CalledProcessError` from `git_stage`
  (`tcw/store/fs.py:640` → `:262`) — a traceback, not a message.
- `tcw init` refuses outright (`tcw/cli.py:30`): "not inside a git repository.
  Run `git init` first."

So a user can read a TCW node that is not in a repository but cannot create one
or add to it. Either git is a requirement — in which case the reads should say
so consistently and `work new` should refuse with a message rather than a
traceback — or it is not, in which case auto-commit should degrade to a no-op
when there is no repository. Pick one and make the whole surface agree.

## Technical changes

Decide the contract first; the code change follows from it. The narrow reading
is that git-backed auto-commit is an *enhancement*, not a precondition, and
`git_stage` / `git_commit_result` should no-op when `git_root` is None — the
same way they already tolerate other git failures. `tcw init`'s refusal would
then become conditional too.

## Meta changes

Nothing user-facing until the contract is chosen. Whatever lands, the
non-git-graph assertions in `tests/test_environment_hardness.py`
(`TestWorktreeNode.test_non_git_graph_is_unaffected`) pin today's read
behavior and should keep passing.
