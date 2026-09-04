Two design questions raised by the adversarial review of the provisioning work,
2026-09-03, and deliberately not settled inside the items that surfaced them.
Both are about what the command *should* do, not whether it does what it says.

1. **`--component` does not scope node provisioning.** `_provision_nodes` runs
   outside the component loop and `NODE_TARGET` is deliberately absent from
   `PROVISION_COMPONENTS`, so `tcw provision --component taxonomy` still contacts
   every declared connected-project remote. Given that `_provision_nodes`'s own
   docstring calls this "the one place a URL the user did not write can be
   contacted", not being able to scope it deserves a decision rather than being a
   side effect. Options: leave it and keep documenting it; add a `--no-nodes`;
   admit nodes into `--component`'s vocabulary as a non-component target.

2. **`repository.checkout` is unbounded in a transitively discovered config.**
   `parse_repository_declaration` bounds `path` against escape — no absolute, no
   `..` — because it is joined onto a directory TCW created. `checkout` is
   deliberately not bounded, which was right when a declaration could only come
   from the user's own config. Transitive node provisioning means a repository
   obtained at hop *n* can name `checkout: ../../<anything>`, resolved against
   the source node's root, and get a clone planted there. Existing mitigations
   are real but partial: the destination is printed before contact, `_obtain`
   refuses a directory that exists, and `_require_declared_checkout` refuses a
   refresh into a foreign repository. Options: bound `checkout` the way `path` is
   for declarations discovered beyond the first hop; require a flag to honor a
   transitive `checkout`; leave it and state the trust boundary.

Neither is a defect against the documented behaviour. Both are the kind of thing
that is much cheaper to decide now than after someone depends on it.
