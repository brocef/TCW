# Resolve a work store inside a project the registry already located

## Origin

GitHub issue [#31](https://github.com/brocef/TCW/issues/31), filed 2026-09-10
by @brocef.

> ### Environment
>
> - tcw version: `tcw 2.0.0`
> - OS / platform: Linux (Claude Code remote container)
> - Install method: editable install from a local checkout
>
> ### Motivation
>
> A node's work store and a node's *location* are resolved by two mechanisms that
> never talk to each other, and only one of them honours `TCW_PROJECT_*`.
>
> `connected-projects` resolution has an override rung: `TCW_PROJECT_<ID>` says
> where a project sits on this machine, which is exactly the per-machine fact no
> checked-in config can carry (`tcw/store/project.py::override_variable`).
>
> Work-store resolution has no such rung. The ladder in `tcw/store/fs.py` (the one
> ending in `StoreNotProvisioned`, ~L3000-3040) is:
>
> 1. the configured `<component>.path`, relative to the node root
> 2. `provisioned_store_root(node_root, declaration)` — a declared `checkout:`, or
>    an XDG cache directory (`tcw/store/checkouts.py::checkout_root`)
> 3. fail
>
> Neither rung 1 nor rung 2 asks the project registry anything. So when rung 1's
> relative path does not resolve — because the workspace is laid out differently
> from what the path assumes — TCW clones a second copy of a repository it has
> already located, by env var, a few milliseconds earlier.
>
> **The two mechanisms disagree inside a single command's output.** This is
> `tcw provision` in the workspace below:
>
> ```
> → work: https://github.com/Proposit-App/proposit-orchestration.git at main, store at docs/proposit-core/work → /root/.cache/tcw/stores/github.com-proposit-app-proposit-orchestration-73cbcd814e44/docs/proposit-core/work
>   work: obtained at /root/.cache/tcw/stores/github.com-proposit-app-proposit-orchestration-73cbcd814e44/docs/proposit-core/work
>   proposit-app: already available
>   proposit-core: already available
>   proposit-app-repo: already available
> ```
>
> `proposit-app` is "already available" — the env var found it at
> `/home/user/proposit-orchestration`. The line above it clones that same
> repository anyway, because the store went down a different ladder.
>
> ### Steps to reproduce
>
> A workspace whose repositories are normally nested — `proposit-core` and
> `proposit-app` inside `proposit-orchestration` — cloned **flat** instead, which
> is what a cloud session does:
>
> ```
> /home/user/proposit-orchestration      # holds every node's board under docs/
> /home/user/proposit-core
> /home/user/proposit-app
> ```
>
> `proposit-core/tcw-config.yaml`, unchanged and correct for the nested layout:
>
> ```yaml
> connected-projects:
>     parent:
>         proposit-app:
>             path: ..
>             repository:
>                 url: https://github.com/Proposit-App/proposit-orchestration.git
>                 ref: main
> work:
>     path: ../docs/proposit-core/work
>     repository:
>         url: https://github.com/Proposit-App/proposit-orchestration.git
>         ref: main
>         path: docs/proposit-core/work
> ```
>
> With the environment giving every node's real location:
>
> ```sh
> export TCW_PROJECT_PROPOSIT_APP=/home/user/proposit-orchestration
> export TCW_PROJECT_PROPOSIT_CORE=/home/user/proposit-core
> export TCW_PROJECT_PROPOSIT_APP_REPO=/home/user/proposit-app
>
> cd /home/user/proposit-core && tcw work list
> ```
>
> ### Expected vs. actual
>
> - Expected: the board at `/home/user/proposit-orchestration/docs/proposit-core/work`.
>   Everything needed to derive it is already known — `work.repository.url` names
>   the orchestration repository, the parent declaration names the same URL, and
>   `TCW_PROJECT_PROPOSIT_APP` says that project is at
>   `/home/user/proposit-orchestration`. Joining that locator with the
>   declaration's `path` gives the store exactly.
>
> - Actual:
>
>   ```
>   tcw work: /home/user/proposit-core/tcw-config.yaml: the work store is declared in https://github.com/Proposit-App/proposit-orchestration.git but has not been provisioned here; run `tcw provision` to obtain it
>   ```
>
>   `tcw validate` in the same shell reports all three overrides taking effect, so
>   the information is present and unused.
>
> ### Why the two workarounds are both wrong
>
> **A symlink** (`ln -s /home/user/proposit-orchestration/docs /home/user/docs`)
> makes rung 1 resolve. It is invisible to every reader of the config, has to be
> recreated per session, and is not something a checked-in workspace can ship.
>
> **`tcw provision`** is worse, and quietly so. It succeeds, but the store it
> provisions is a *fresh clone at the declared `ref`*, so:
>
> - board reads come from `main` rather than from the branch the workspace is
>   actually on;
> - rung 1 still fails, so the cache clone wins every subsequent command;
> - `publishes` is true for a store reached through its declaration, and
>   `publish_transitions()` defaults to `True` — so a `tcw work start` would be
>   committed and **pushed to `main`**, not landed on the working branch.
>
> I removed the cache clone rather than keep it, specifically so a missing symlink
> fails loudly instead of silently reading and writing a detached copy.
>
> ### Description
>
> Add a rung between 1 and 2: before falling back to a provisioned checkout, ask
> the project registry whether any reachable project comes from the repository the
> declaration names, and if one does, resolve the store inside it.
>
> The registry already holds both halves. `ConnectedProject.repository` carries the
> declaration a component store takes — the docstring even says it is "exactly the
> declaration a component store takes, because 'where does this come from' is the
> same question either way" — and the resolved `Project.locator` says where that
> project landed on this machine, env override included. The join is:
>
> ```
> <locator of the project whose repository.url matches <component>.repository.url>
>   / <component>.repository.path
> ```
>
> For the workspace above that yields
> `/home/user/proposit-orchestration/docs/proposit-core/work` for `proposit-core`,
> and the same walk resolves the three `proposit-app` package nodes, which reach
> the orchestration project through their own repo-root node's parent edge.
>
> Two properties worth preserving in whatever shape this takes:
>
> - **Local before remote, as everywhere else in TCW.** The new rung sits above
>   the cache, so a repository present on disk is never re-cloned. This is the
>   same "the locator answers when it can, and the declaration answers only when
>   it cannot" ladder `ConnectedProject` already documents.
> - **A store found this way should not publish.** It is on the user's own disk
>   and they push it themselves, which is the reasoning `publishes` already gives
>   for excluding a store found at a local `path`.
>
> Matching on URL needs a little normalization to be useful — `.git` suffix,
> `git@host:owner/repo` versus `https://host/owner/repo` — and a `ref` mismatch
> against a checkout on some other branch is worth thinking about, though I would
> argue a local checkout the user is standing in should win regardless of the
> declared ref, the same way rung 1 does today.
>
> ### Benefits
>
> - A workspace can be checked out in any layout without editing a checked-in
>   config, creating symlinks, or hardcoding a machine-specific absolute path.
>   That last one is what #26 was filed to escape; this closes the remaining gap
>   for a workspace whose *sibling arrangement*, rather than its worktree, differs.
> - Cloud sessions, CI, and containers get correct boards from environment
>   variables alone, which is the mechanism already designated for exactly this
>   kind of per-machine fact.
> - It removes a silent-wrong-answer path. Today the recommended remedy for the
>   error message produces a store that reads the wrong ref and pushes
>   transitions to it.
> - No disk or network spent re-cloning a repository the session already has,
>   and one less copy to drift.

## References

- GitHub issue [#26](https://github.com/brocef/TCW/issues/26) — named in the
  report as the change that let a machine-specific project location come from
  the environment; this item is the gap it left for work stores.
- `2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared` —
  the other open backlog item against the same `resolve_store` ladder in
  `tcw/store/fs.py`. Both change how a failed rung 1 is handled, so whichever
  lands second has to read the other.
