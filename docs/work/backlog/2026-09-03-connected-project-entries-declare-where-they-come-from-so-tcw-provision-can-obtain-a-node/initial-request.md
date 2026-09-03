# Connected-project entries declare where they come from, so `tcw provision` can obtain a node

A node should be able to say which repository a *connected project* comes from,
the same way a component store already says which repository it comes from, and
`tcw provision` should be able to obtain it.

The request arrived as an observation about the existing mechanism:

> I'm imagining that the repository reference style for #2 could be used for
> taxonomy and capabilities too. Then an agent/startup script could pull those
> referenced repos as needed to read the artifacts.

Half of that already exists — `taxonomy.repository` and `capabilities.repository`
are supported today. It does not answer the case that prompted it. In
`proposit-app` the taxonomy and capabilities stores are already in the checkout;
what is missing is the *node* they extend. `extends` names a project id and
resolves it through `connected-projects`, so no amount of store declaration
reaches it.

Every one of that project's nodes extends a node in a different repository:
`proposit-shared` extends `proposit-core`, and `proposit-server` and
`proposit-mobile` each extend both `proposit-shared` and `proposit-core`. A
session that clones only the app repository cannot resolve `proposit-core` at
all.

What should be true when this is done:

- A `connected-projects` entry may carry a `repository` declaration beside its
  locator, naming where that node comes from.
- The locator still wins when the node is present. A declaration answers only for
  a machine that does not have it — the same rule component stores already
  follow, so one configuration serves both machines.
- `tcw provision` obtains declared nodes, and follows the graph: a node obtained
  because it was declared may itself declare others.
- Declarations follow the graph rather than being centralized. The app repository
  declares only its own edge to the orchestration node; the orchestration node's
  own configuration declares where `proposit-core` comes from. The app repository
  never has to know that `proposit-core` exists.
- Existing configuration keeps working untouched: a bare locator string stays a
  locator.

Out of scope: the graph tolerating an absent node, which is the blocking item.
This one puts a node there; it does not make its absence survivable.

Also out of scope: consumer-side configuration in `proposit-app` and
`proposit-orchestration`.

## Notes

Asked for reference material; none provided beyond the session itself. The
validation run recorded in `intake.md` was performed against real checkouts of
`proposit-app`, `proposit-orchestration` and `proposit-core`, over a prototype of
the blocking item.

One question was raised in session and deliberately left for the spec: whether
`tcw provision` obtains declared nodes eagerly, or a node is fetched lazily when
something needs it. The requester's concern is that a session would otherwise
clone two repositories before a taxonomy resolves.
