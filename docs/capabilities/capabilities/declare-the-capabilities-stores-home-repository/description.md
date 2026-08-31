As a project owner whose capabilities tree lives in a repository other than the
code repository, I can record that repository under `capabilities.repository` —
its URL, optionally a ref, the tree's path within it, and optionally where a
working copy should live on this machine — and obtain it with `tcw provision`.

The declaration is a fallback, never an override, and provisioning stays
explicit: no other command reaches the network, and the remote is printed before
it is contacted. Running `tcw provision` again reports the tree as already
available and contacts nothing.

**The same weaker promise applies as for the taxonomy tree** — see
[the taxonomy equivalent](tcw://C/taxonomy/declare-the-taxonomy-stores-home-repository).
A capabilities tree has no required layout, so a declared repository is checked
only for a directory at the declared path, not for the contents of one.
