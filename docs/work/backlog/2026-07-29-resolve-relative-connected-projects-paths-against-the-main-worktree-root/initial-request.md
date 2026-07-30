# Resolve relative connected-projects paths against the main worktree root

## Origin

GitHub issue [#9](https://github.com/brocef/TCW/issues/9), filed 2026-07-29 by
@brocef. Accepted during the first `tcw-triage-issues` sweep.

Reported against `tcw 0.16.0` on macOS 26.5.2, pyenv shim over an editable
checkout.

> ### Steps to reproduce
>
> A multi-node graph: a workspace root (`example-app`) with child project nodes
> beside it (`example-server`, `example-shared`, `example-mobile`). Each
> child's `tcw-config.yaml` points back at the root with a **relative** path:
>
> ```yaml
> # example-server/tcw-config.yaml
> id: example-server
> connected-projects:
>     parent:
>         example-app: ..
> ```
>
> 1. `cd example-server`
> 2. `git worktree add .worktrees/my-feature my-feature-branch`
> 3. `cd .worktrees/my-feature`
> 4. Run **any** `tcw` command.
>
> ### Expected vs. actual
>
> - **Expected:** tcw resolves the same project graph it does from the primary
>   checkout. A git worktree is the same project on a different branch, and the
>   node's `docs/work/**` is right there in the worktree.
> - **Actual:** every command fails, including read-only ones:
>
>     ```
>     $ tcw work list
>     tcw: /Users/.../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
>     ```
>
> ### Cause
>
> The relative `connected-projects` path is resolved against the directory of
> the `tcw-config.yaml` that declares it. In a worktree that directory is
> `<repo>/.worktrees/<name>/`, so `..` resolves to `<repo>/.worktrees/` instead
> of the workspace root — one level short, and at a path that will never contain
> a config.
>
> It generalises: any relative connected-project path is off by however deep the
> worktree is nested.
>
> ### Why it matters
>
> Git worktrees are the natural way to run several branches of one repo in
> parallel, and TCW's own guidance leans that way — `tcw work start --worktree`
> exists, and `tcw work complete` has `merge_worktree` / `--already-integrated`
> handling for exactly that flow. But once you are *inside* a worktree, the CLI
> that manages the item can't run there.
>
> Read-only commands failing is the sharper edge — `tcw work list` and
> `tcw work show` have no reason to care where the checkout lives.
>
> ### Remediation
>
> Resolve relative `connected-projects` paths against the **main worktree root**
> rather than the config file's directory when the two differ. Git makes this a
> one-liner:
>
> ```bash
> git rev-parse --path-format=absolute --git-common-dir   # <main-worktree>/.git
> git worktree list --porcelain | head -1                 # the primary checkout
> ```
>
> `--git-common-dir` points at the primary checkout's `.git` from anywhere in
> the tree, including a worktree; its parent is the node root the relative path
> was authored against. When not in a worktree the two coincide, so the change
> is a no-op for existing setups.
>
> An explicit escape hatch would also work — a `${TCW_NODE_ROOT}`-style token,
> or accepting absolute paths — but inferring it from git needs no config
> migration.
>
> Axis: **work** (with capabilities and validate hitting the same resolution
> path).

## Notes

The reporter proposes a remediation, but the `request` stage should treat it as
a proposal rather than a decision — in particular, whether resolving against the
git common dir is right for a node that is not a git repository at all, which
the issue does not address.

This is TCW's own repo, so reporter and maintainer are the same person. The
quoted text is the report as filed, except that the reporter's private project
names were replaced with `example-*` placeholders; nothing else was rewritten.
