# `extends` composes `docs/<component>` instead of resolving the sibling's store

A node that extends another should read the other node's *configured* taxonomy or
capabilities store, the same way every other read of a store resolves it. Today
it reads a composed path and is wrong whenever the sibling keeps its tree
somewhere else.

Found by the repo-wide sibling sweep the `spec` stage requires, while specifying
[Unreachable connected projects degrade](tcw://W/2026-09-03-unreachable-connected-projects-degrade-instead-of-failing-every-command).
Not reported by a user.

What should be true when this is done:

- `extends` resolves the extended node's component store through the same
  resolution the store itself uses, so a node configuring `taxonomy.path` or
  `capabilities.path` can be extended from.
- A sibling whose tree is declared but not provisioned here is reported as
  unprovisioned, naming the remote, rather than as having no tree at all.
- A sibling that genuinely has no such component still says so.

Out of scope: anything about which projects are reachable — that is the item
this was found from.

## Notes

Asked for reference material; none provided beyond the session itself. The
defect and the code that causes it are recorded in `intake.md`.

No real configuration hits this today: every `proposit-*` node keeps its trees at
the default path. It is a latent defect found by a sweep, and it is filed and
sized accordingly.
