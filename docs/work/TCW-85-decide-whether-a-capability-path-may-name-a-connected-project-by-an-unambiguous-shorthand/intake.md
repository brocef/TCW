# Decide whether a capability path may name a connected project by an unambiguous shorthand

GitHub #27 asked, separately from its main report, whether `shared/authoring/x`
should resolve when `shared` is an unambiguous suffix of exactly one connected
project id (`proposit-shared`). Today it resolves nowhere, and — with this node's
own ledger — is read as a local path that does not exist.

Deferred from 2026-09-09-resolve-capabilities-yaml-sidecar-paths-while-an-item-is-still-being-worked,
which now reports such a path while work is in hand. Both advisors judged the
shorthand a separate decision: it would change how paths resolve for every
command (`show`, `set`, the completion gate), and needs collision and precedence
rules. Rejecting it permanently is also a valid outcome.

## References

- tcw/work/recursion.py `route_capability_path`
- GitHub #27
