As a user working in a checkout that holds only some of my connected projects'
repositories, I declare where a _connected project_ comes from, beside the
path that says where it sits on my own machine. Both are in the project's
manifest entry, `.tcw/tcw-manifest.yaml`: the entry's `path`, and its
`repository`, written `<url>#<branch>` (the branch optional), with a
`subfolder` when the project is a folder inside that repository. So one
manifest serves a machine that has the repository and one that does not.

A project that is already here always wins: the repository is consulted only
when the entry's folder holds nothing, so nothing about a machine that has the
project changes, and nothing is contacted on its behalf. Where the project is
absent, TCW says it is not on this machine, where the entry places it, the
repository, and the command that fetches it (a `project provision` command,
which TCW-115 adds),
rather than reporting that the project was never declared.

`tcw provision` does not fetch connected projects; it fetches the component
stores a project declares (see [Provision declared
stores](tcw://C/cli/provision-declared-stores)). A store whose repository is a
project already here is still read inside that project's folder, matched
against the manifest entries that give that repository.

Declaring a connected project's home repository does not make any command
reach the network.

Every connected project is placed the same way, whether it is a parent, a
child, or a project further up or down the family.
