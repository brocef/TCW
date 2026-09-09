# Descend through a storeless routing node in delegate and reconcile

## Origin

GitHub issue [#30](https://github.com/brocef/TCW/issues/30), filed 2026-09-09
by @brocef.

> ### Environment
>
> - tcw version: 1.3.0
> - OS / platform: macOS (Darwin 25.6.0)
> - Install method: editable checkout
>
> ### Summary
>
> `references/cross-node-deltas.md` in the `tcw-work` skill states that a storeless
> node in the middle of the graph is a routing node that coordination passes
> through:
>
> > A node in the chain need not keep a board of its own. A repository root that
> > groups the packages owning the boards is a routing node: an epic resolves
> > through it, its slices below it are found, and `tcw work escalate` reaches the
> > nearest ancestor that does keep one.
>
> `escalate` behaves that way, because it uses `nearest_work_ancestor`. `delegate`
> and `reconcile` do not. Both walk `child_nodes`, which is one level deep and
> **filters out** a storeless child rather than descending through it, so the
> grandchildren that own the boards become unreachable.
>
> `tcw/store/fs.py:234`:
>
> ```python
> def child_nodes(root: Path) -> list[Path]:
>     """Direct registered children that contain a work store."""
>     ...
>     if _has_work_store(Path(project.locator))
> ```
>
> `tcw/work/recursion.py:73` (`_tasks_for`, used by `reconcile`) and
> `tcw/work/recursion.py:291` (`delegate`) both build from that list.
>
> ### Steps to reproduce
>
> Graph, all reciprocal and all present in one checkout:
>
> ```
> root            (has a work store)
> └── mid         (NO work store — a repository root grouping packages)
>     ├── a       (has a work store)
>     ├── b       (has a work store)
>     └── c       (has a work store)
> ```
>
> 1. At `root`: `tcw work new --epic "Some cross-package initiative"`
> 2. At `root`: `tcw work delegate a "A slice" --initiative <epic-slug>`
> 3. At `root`: `tcw work reconcile <epic-slug>`
>
> ### Expected vs. actual
>
> - Expected, per the skill reference: step 2 delegates into `a`'s inbox through
>   the routing node, and step 3 finds slices on `a`, `b` and `c`.
> - Actual: step 2 fails with `no child node 'a'. children: mid` — except `mid` is
>   itself unusable as a target because it has no store. Step 3 reports
>   `_No tasks reference this initiative yet._` regardless of how many slices exist
>   below `mid`.
>
> Enumerating the walk directly shows the shape:
>
> ```python
> from pathlib import Path
> from tcw.store.fs import child_nodes
> child_nodes(Path("root"))   # -> [.../other-child-with-a-store]  (mid dropped, a/b/c unreachable)
> child_nodes(Path("mid"))    # -> [a, b, c]
> ```
>
> The practical consequence is that an epic spanning `a`, `b` and `c` has nowhere
> to live. `root` can neither delegate to them nor roll them up, and `mid` cannot
> host the epic because hosting one requires a board. Giving `mid` a board works
> but is not free: it also changes where `escalate` from `a`, `b` or `c` lands,
> because `nearest_work_ancestor` would then stop at `mid` instead of reaching
> `root`.
>
> ### Remediation
>
> Either make the code match the documentation or make the documentation match the
> code.
>
> If the documented behaviour is the intent, `child_nodes` needs a companion that
> descends through a storeless child instead of dropping it, and `delegate` and
> `_tasks_for` should use that. `delegate`'s error message would also want to name
> reachable grandchildren rather than only direct children.
>
> If one-level-deep is the intent, `cross-node-deltas.md` should say that a
> routing node only routes `escalate`, and that an epic must live on a node whose
> children directly own the boards.
>
> Related: the same graph is affected by #28, since ordering between slices in
> different nodes can only be recorded as an `external:` blocker that never
> auto-resolves.
