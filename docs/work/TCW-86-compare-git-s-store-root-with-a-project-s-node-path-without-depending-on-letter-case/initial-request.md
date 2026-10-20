# Compare git's store root with a project's node path without depending on letter case

## What is wanted

Every place that compares the store's git root with a project's node path by
their text should compare them in a way that does not depend on letter case.

`FsWorkStore.store_git_root` comes from `git rev-parse --show-toplevel`, spelled
the way git spells it. `self.root` comes from the node path, which for a project
reached through a `TCW_PROJECT_<ID>` override keeps the override's spelling. On a
disk that ignores letter case (the macOS default) the two can name the same
folder with different text, and `relative_to` then raises "is not in the subpath
of".

**Decided with the maintainer at triage:** convert **every** such site to the
case-insensitive comparison, whether or not a probe shows it failing today. The
probes are still worth running to show which sites were live defects, but a
clean probe is not a reason to leave a site as it is.

## Constraints

- The fix is the existing helper `tcw.store.project._below`, which
  `2026-09-29-accept-a-project-override-spelled-in-other-letter-case-from-a-linked-worktree`
  used for the same problem.

## Notes

- Sites named by the entry (line numbers approximate, as of 2026-09-29):
  `tcw/work/cli.py` (~1651, ~3592), `tcw/work/recursion.py` (~463),
  `tcw/store/fs.py` (~1086 `resolved_ignore_rules`, ~4430, ~4756, ~5448, ~5509,
  ~5675, ~5746, ~5767, ~5836, ~7452). Spec should search for the complete list
  rather than trust this one.
- Not reproduced when filed: `start`, with and without `--worktree`, worked
  through an upper-case override.
- Reference material: asked; none provided beyond the entry.
