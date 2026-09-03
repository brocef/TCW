Raw request, from a working session on 2026-09-03.

> I'm imagining that the repository reference style for #2 could be used for
> taxonomy and capabilities too. Then an agent/startup script could pull those
> referenced repos as needed to read the artifacts.

The instinct is right; the level is one up. `taxonomy.repository` and
`capabilities.repository` already exist — `resolve_store` is component-generic
and the README documents "the same block, per component". That does not help the
case in front of us: `proposit-app`'s taxonomy and capabilities stores are
already in-repo. What is missing is not a store but the *node* they extend.
`extends` resolves a project id through `connected-projects`, and a store path
cannot answer that.

Every proposit node's taxonomy extends a node in another repository:

| node              | `docs/taxonomy/config.yaml` extends |
| ----------------- | ----------------------------------- |
| `proposit-shared` | `proposit-core`                     |
| `proposit-server` | `proposit-shared`, `proposit-core`  |
| `proposit-mobile` | `proposit-shared`, `proposit-core`  |

So a cloud session cannot resolve `proposit-core` at all, and degradation alone
(the blocking item) makes that survivable rather than fixed.

The shape agreed in session: a `connected-projects` entry may carry a
`repository` block beside its locator, with the same ladder a store uses — the
local path wins when it is here, the declaration answers when it is not — and
`tcw provision` obtains declared nodes, transitively.

    connected-projects:
      parent:
        proposit-app:
          path: ../../..
          repository:
            url: https://github.com/Proposit-App/proposit-orchestration.git
            ref: main

A bare string stays a locator, so this is backward compatible. Declarations
follow the graph: `proposit-app` declares only its edge to orchestration, and
orchestration's own config declares `proposit-core`'s url on its child entry —
the app repository never has to know that `proposit-core` exists.

Validated in-session against real checkouts. With the parent pointed at a
provisioned orchestration clone and orchestration's `proposit-core` child pointed
at a real core clone, over the degradation prototype:

    $ tcw work nodes
    node:   proposit-server
    parent: proposit-app
    $ tcw validate
    ... extends project 'proposit-shared' is not reachable ...   # the only one left

`proposit-core` resolves. One checkout serves every node naming the same
`(url, ref)`, since that is the provisioning cache key.

Open question raised and not settled: whether `tcw provision` obtains nodes
eagerly or a node is fetched lazily when something needs it. A cloud session
would otherwise clone orchestration *and* core before taxonomy resolves.
