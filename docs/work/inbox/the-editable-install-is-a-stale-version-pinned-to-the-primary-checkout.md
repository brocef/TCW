# The editable install is stale, and silently shadows every worktree

`pip list` reports `tcw 0.10.3` installed from `/Users/brian/Projects/TCW`, while
the project is at `2.0.3` (`pyproject.toml`, `tcw/__init__.py`). Two consequences,
and the second one cost real time.

**The `tcw` on PATH is not the tree you are working in.** The editable install
registers an import hook pinned to the primary checkout, so inside a git worktree
the console script runs the *other* checkout's source. The agent guide documents
this for running the CLI by hand. What it does not say is that it reaches tests:
`tests/test_documented_cli_surface.py` shelled out to `tcw` to discover the command
surface, so in a worktree it measured whether the **installed** CLI matched **these**
docs. Any command added in a worktree read as "no such verb" however correct it was.

Fixed in passing on 2026-09-13 by having that test invoke its own repository via
`sys.path.insert(0, REPO)` in a subprocess, which does win over the install's
finder. Filed because the same trap applies to anything else that shells out to
`tcw`, and because a stale *version* in the hook is the condition the guide warns
"shadows the right one".

**Suggested actions**, none of which this note takes:

1. Decide whether the machine's install should be re-pointed and refreshed. Doing so
   affects every session sharing it, which is why this session did not.
2. Grep for other places tests or scripts invoke `tcw` as a subprocess rather than
   importing it, and give them the same treatment.
3. Consider whether the guide's "Working in a `--worktree` branch" section should say
   that tests are affected too, not only manual CLI runs.

Storage-abstracted: nothing here touches the model. It is packaging and test
plumbing.
