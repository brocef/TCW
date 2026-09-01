# Re-anchor a relative work.path at the node's counterpart inside the main worktree

## Origin

GitHub issue [#26](https://github.com/brocef/TCW/issues/26), filed 2026-09-01
by @brocef, reporting against tcw 1.2.0 on macOS.

> ### Summary
>
> `FsWorkStore._local_root` (and the identical tree-store copy) re-anchors a relative `work.path` at the **main worktree root** when it runs inside a linked git worktree. That is correct only when the tcw node *is* the repository root. For a node nested inside the repo, the node's own sub-path is dropped, and the relative path is then applied from the wrong directory — so the store cannot be found at all.
>
> The practical effect: a monorepo whose packages are each a tcw node with an external `work.path` cannot express that path relatively. It has to hardcode an absolute, machine-specific path in a file that is checked into git.
>
> ### Steps to reproduce
>
> Repository `proposit-app`, checked out at `/proposit-app`, with a tcw node at `apps/server` whose work store lives outside the repo at `/docs/proposit-server/work`.
>
> 1. In `/proposit-app/apps/server/tcw-config.yaml`, set the work path relative:
>
>    ```yaml
>    work:
>      path: ../../../docs/proposit-server/work
>    ```
>
> 2. From `/proposit-app/apps/server`, run `tcw work path`. This works — it prints `/docs/proposit-server/work`.
>
> 3. Create a linked worktree of the same repo, e.g. `git worktree add /worktrees/auth-screens`, and run the same command from `/worktrees/auth-screens/apps/server`.
>
> ### Expected vs. actual
>
> - Expected: `/docs/proposit-server/work` — the same store, in both the primary checkout and the worktree.
> - Actual:
>
>   ```
>   tcw work: no tcw work node here — run `tcw init` in the project folder.
>   ```
>
> The two resolutions, taken from `FsWorkStore._local_root` directly:
>
> ```
> primary checkout
>   node_root = /proposit-app/apps/server
>   base      = node_root                                    (anchors is None)
>   result    = /proposit-app/apps/server/../../../docs/proposit-server/work
>             = /docs/proposit-server/work                                    OK
>
> linked worktree
>   node_root = /worktrees/auth-screens/apps/server
>   base      = /proposit-app                          (anchors[1], the main worktree root)
>   result    = /proposit-app/../../../docs/proposit-server/work
>             = /Users/brian/Projects/docs/proposit-server/work                     WRONG
> ```
>
> `base` loses the `apps/server` segment, so the `../../../` in the config is applied from two levels too high.
>
> ### Remediation
>
> Re-anchor at the node's counterpart inside the main worktree rather than at the main worktree root itself. In both copies of `_local_root` (`tcw/store/fs.py`, roughly lines 1113 and 3021):
>
> ```python
> anchors = worktree_anchors(node_root)
> if not value.is_absolute() and anchors is not None:
>     top, main = anchors
>     base = main / node_root.resolve().relative_to(top)   # was: base = main
> ```
>
> That is a no-op for the case the current code already handles — a node at the repository root, where `node_root == top` and `relative_to` yields `.` — and it fixes every nested node.
>
> Worth a test with a node in a repo subdirectory: the existing worktree coverage appears to only exercise a node sitting at the repo root, which is why this passes today.
>
> ### Workaround
>
> Keep `work.path` absolute. The cost is that a checked-in `tcw-config.yaml` carries a path specific to one machine, which is what prompted this report.

## References

- `tcw/store/fs.py:2792` — the single `_local_root` re-anchoring site in this
  checkout (`base = anchors[1]`). The report names two copies at ~1113 and
  ~3021; the second was consolidated away before this tree, so confirm the
  count at spec time rather than assuming two.
- `tcw/store/project.py:56` — `worktree_anchors`, which returns
  `(current worktree top, main worktree root)` and is what the fix reads both
  halves of instead of only the second.
