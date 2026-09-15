# Treat a main-checkout copy of any node as its worktree copy when resolving the project graph

## What is wanted

In a linked git worktree of a repository that holds several TCW nodes, running `tcw`
from any node except the repository's root node should work against the worktree's
copy of the project graph, as it does from the primary checkout.

Today (GitHub #39) it refuses, reporting every other node in that repository as a
duplicate project id and a broken parent/child locator — every node except the one the
command ran from. Running from the worktree's root node works. The workaround is to
run `tcw` from the primary checkout and keep only code edits in the worktree.

The reporter traced it to `ProjectRegistry._locator_path` in `tcw/store/project.py`:
it aliases only the current node's main-checkout path back onto the worktree, so a
parent's child locator leads into the primary checkout and loads its nodes a second
time.

## Constraints

- **Genuine duplicate ids must still be reported.** The code's own comment says a
  wider alias "would mask genuine duplicate-ID errors"; the reporter argues that holds
  for arbitrary paths but not for a path whose counterpart under the current worktree
  holds a config. Duplicates across different repositories must still be caught.

## Notes

- Checked at triage on `main`: the narrow alias (`self._counterpart_path`) is unchanged.
- The reporter's suggested remediation is kept verbatim in `intake.md` for the spec.
- Reference material: asked; none provided.
- GitHub #39 stays open until the change ships.

## References

- `docs/work/completed/2026-07-29-resolve-relative-connected-projects-paths-against-the-main-worktree-root/` —
  the earlier fix that introduced worktree re-anchoring in the registry.
