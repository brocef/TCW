As a project owner whose capabilities tree lives in a repository other than the
code repository, I can record that repository under `capabilities.repository` —
its URL, optionally a ref, the tree's path within it, and optionally where a
working copy should live on this machine — and obtain it with `tcw project provision`.

The declaration is a fallback, never an override, and provisioning stays
explicit: no other command reaches the network, and the remote is printed before
it is contacted. Running `tcw project provision` again reports the tree as already
available and contacts nothing. Where the tree is absent, every command names
the one that fetches it: `tcw project provision --component capabilities`, or,
for another project's tree, `tcw -C <folder> project provision --component capabilities`
with that project's folder.

With no argument, `tcw project provision` obtains every declared store that is
missing and then fetches the projects of the family that are not here;
`tcw project provision --component capabilities` obtains this store alone and fetches no
project (see [Provision declared
stores](tcw://C/cli/provision-declared-stores)). The declaration's `ref` may
name a branch, a tag or a commit; one that names none of these fails, with
git's reason.

**The same weaker promise applies as for the taxonomy tree** — see
[the taxonomy equivalent](tcw://C/taxonomy/declare-the-taxonomy-stores-home-repository).
A capabilities tree has no required layout, so a declared repository is checked
only for a directory at the declared path, not for the contents of one.
