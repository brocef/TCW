## Inbox manifest

- `2026-09-29-store-git-root-compared-by-text-with-node-paths.md`

## Inbox body

# Paths from git compared by text with paths from a project's locator

Found verifying `2026-09-29-accept-a-project-override-spelled-in-other-letter-case-from-a-linked-worktree`.

`FsWorkStore.store_git_root` comes from `git rev-parse --show-toplevel`, in
git's letter case; `self.root` comes from the node path, which for a project
reached through a `TCW_PROJECT_<ID>` override keeps the override's spelling.
About a dozen places compare the two by text with `relative_to` — among them
`tcw/work/cli.py` (~1651, ~3592), `tcw/work/recursion.py` (~463), and
`tcw/store/fs.py` (~1086 `resolved_ignore_rules`, ~4430, ~4756, ~5448, ~5509,
~5675, ~5746, ~5767, ~5836, ~7452). On a disk that ignores letter case they
could raise "is not in the subpath of" for such a project.

Not confirmed: `start` with and without `--worktree` worked through an
upper-case override. Worth a probe of each site; where one fails, the fix is
`tcw.store.project._below`, as that item used.
