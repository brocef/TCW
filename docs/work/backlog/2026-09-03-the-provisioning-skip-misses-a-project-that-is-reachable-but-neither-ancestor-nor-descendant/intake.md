Found verifying the hierarchical (workstation) layout of the Proposit workspace,
2026-09-03 — the layout where every repository is already on disk and nothing
should be fetched at all.

Standing in `proposit-app/apps/server` with the whole workspace present:

    $ tcw provision --dry-run
      proposit-app: already available
    → proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
      proposit-core: would obtain into …
      proposit-app-repo: already available

`proposit-core` is at `<workspace>/proposit-core`, present, and in the graph —
`registry.get("proposit-core")` resolves it. It is a *sibling of an ancestor*: a
child of the orchestration node, which is this node's grandparent.

The skip added by
[tcw provision fetches a project the checkout already has](tcw://W/2026-09-03-tcw-provision-fetches-a-project-the-checkout-already-has)
builds its set from `registry.current`, `ancestors()` and `descendants()`. That
covers the case it was written for and misses every project reachable by any
other shape of route. The question it means to ask is "is this project in the
graph", and the registry answers exactly that with `get()`.

The consequence is the same as the defect it was meant to fix, one relation
further out: a workstation holding the entire workspace would clone a repository
it already has, on every `tcw provision`.
