# Treat a main-checkout copy of any node as its worktree copy when resolving the project graph

## Origin

GitHub issue [#39](https://github.com/brocef/TCW/issues/39), filed 2026-09-15 by @brocef:
**Linked worktree of a multi-node repository reports every sibling node as a duplicate project id**

> ### Environment
>
> - tcw version: tcw 2.2.0
> - OS / platform: macOS (Darwin 25.6.0)
> - Install method: editable checkout of the TCW repository
>
> ### Layout
>
> Two repositories. The inner one holds several tcw nodes, and its root node's parent lives in the outer repository:
>
> ```
> workspace/                  # repository 1, node `workspace`
>   tcw-config.yaml           #   children: { app-repo: app }
>   app/                      # repository 2, node `app-repo`
>     tcw-config.yaml         #   parent: { workspace: .. }
>                             #   children: { pkg-a: pkg-a, pkg-b: pkg-b }
>     pkg-a/tcw-config.yaml   #   node `pkg-a`, parent: { app-repo: .. }
>     pkg-b/tcw-config.yaml   #   node `pkg-b`, parent: { app-repo: .. }
> ```
>
> ### Steps to reproduce
>
> 1. `git -C workspace/app worktree add ../app-wt -b feature` (any location works; the linked worktree is what matters)
> 2. `cd workspace/app-wt/pkg-a && tcw work list` (or `tcw validate`)
>
> ### Expected vs. actual
>
> - Expected: the command runs against the worktree's copy of the graph, as it does from `workspace/app/pkg-a` in the primary checkout.
> - Actual: it refuses, naming every node in the inner repository **except the one the command ran from**:
>
> ```
> tcw: workspace/app/tcw-config.yaml: duplicate project id 'app-repo' also used by workspace/app-wt/tcw-config.yaml;
> workspace/app/pkg-b/tcw-config.yaml: duplicate project id 'pkg-b' also used by workspace/app-wt/pkg-b/tcw-config.yaml;
> workspace/tcw-config.yaml: child locator for 'app-repo' does not point back to workspace/app-wt;
> workspace/app-wt/pkg-a/tcw-config.yaml: parent locator for 'app-repo' does not point back to workspace/app
> ```
>
> Running from the worktree's **root** node (`workspace/app-wt`) works. In the real layout this came from (a root node plus three package nodes), the node the command ran from was left out of the list every time, and every other node in that repository was reported.
>
> ### Cause
>
> `ProjectRegistry._locator_path` in `tcw/store/project.py`:
>
> - Rule 1 correctly re-anchors `app-wt/tcw-config.yaml`'s escaping parent locator (`..`) to `workspace/`.
> - `workspace/tcw-config.yaml`'s child locator `app` then resolves to the **primary** checkout's `workspace/app`.
> - Rule 2 aliases only `self._counterpart_path`, the main-worktree spelling of the *current* node (`workspace/app/pkg-a`). So `workspace/app` is loaded as a second `app-repo`, and its children `workspace/app/pkg-a` and `workspace/app/pkg-b` follow. `pkg-a` is aliased back to the worktree; `pkg-b` is not.
>
> The comment there says a wider alias "would mask genuine duplicate-ID errors". That holds for arbitrary paths. But a path under the main worktree root whose relative counterpart under the current worktree top holds a config is the same node on another branch, not a genuine duplicate.
>
> ### Remediation
>
> In Rule 2, alias any resolved path `p` with `p.is_relative_to(main)` onto `top / p.relative_to(main)` when that counterpart config exists, rather than only the current node's counterpart. The main-worktree copy of any node in the checked-out repository then collapses onto its worktree copy, and genuine duplicates across different repositories are still reported.
>
> Workaround until then: run `tcw` from the primary checkout (or from the worktree's repository-root node) and keep code edits in the worktree.
