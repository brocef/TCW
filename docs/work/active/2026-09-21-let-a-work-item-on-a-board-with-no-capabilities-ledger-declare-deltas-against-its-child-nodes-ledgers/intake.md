# Let a work item on a board with no capabilities ledger declare deltas against its child nodes' ledgers

A repository-root node can keep a work board but no capabilities ledger, while its
child nodes each keep one. Cross-package work belongs on that root board, because
delegate and reconcile reach only one level (see GitHub #30). But an item there that
changes capabilities in its children's ledgers has no supported way to declare
those changes. Its `capabilities.yaml` has no ledger to resolve against. So the
completion gate can check neither `new:` nor `changed:`, and the capabilities
skill's "record it in capabilities.yaml" advice has nowhere to point.

## What happened

In proposit-app, the repo-root node `proposit-app-repo` has a board but no
capabilities component. There, `tcw capabilities path` prints "no tcw capabilities
node here — run `tcw init` in the project folder." Its children, `proposit-shared`
(packages/shared), `proposit-server` (apps/server) and `proposit-mobile`
(apps/mobile), each have a ledger and are declared under
`connected-projects.children`. One item on the root board added a new entry to
proposit-shared's master ledger and `Supported` overrides in both apps. The reporter
added the entry by running `tcw capabilities add` in the child by hand, and wrote no
`capabilities.yaml`, because it could not resolve.

## What is wanted (reporter's suggestions)

Some supported form, for example:
- node-qualified paths in `capabilities.yaml` (`proposit-shared/authoring/x`) that
  the gate resolves through `connected-projects.children`; or
- the gate handing each path to the child node that owns it.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app on tcw CLI 2.5.0.
The requester asked for it to be tracked at high priority.

## References

- `2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`
  (GitHub #30): why cross-package work sits on the root board in the first place.
- `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`: the same gate's
  ledger-discovery test (`<node root>/docs/capabilities`), which this item changes too.
- `2026-09-09-resolve-capabilities-yaml-sidecar-paths-while-an-item-is-still-being-worked`
  (GitHub #27): how node-qualified paths in `capabilities.yaml` resolve today.
