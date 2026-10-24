As a user working in a checkout that holds only some of my connected projects'
repositories, I declare where a _connected project_ comes from, beside the
path that says where it sits on my own machine. Both are in the project's
manifest entry, `.tcw/tcw-manifest.yaml`: the entry's `path`, and its
`repository`, written `<url>#<branch>` (the branch optional), with a
`subfolder` when the project is a folder inside that repository. So one
manifest serves a machine that has the repository and one that does not.

A project that is already here always wins: the repository is consulted only
when the project is not on this machine, so nothing about a machine that has
the project changes, and nothing is contacted on its behalf. A project found
here by any rule, a manifest entry, a `TCW_PROJECT_<ID>` variable or the search
for its folder, is never fetched, whatever a manifest says about its
repository. Where the project is absent, TCW says it is not on this machine,
where the entry places it, the repository, and the command that fetches it,
`tcw project provision <id>`, rather than reporting that the project was never
declared.

`tcw project provision` is what reads the repository: it clones the project
into the folder its deciding manifest entry gives, the entry the lookup for its
folder uses. With no argument it fetches every project of this project's family
that is missing, and with `<id>` that project and the projects it inherits
from; see [Fetch a project that is not on this
machine](tcw://C/cli/fetch-a-project-that-is-not-on-this-machine), which also
says how far a manifest that is not this project's own may place a clone. The
same command obtains the component stores a project declares (see [Provision
declared stores](tcw://C/cli/provision-declared-stores)). A store whose
repository is a project already here is still read inside that project's
folder, matched against the manifest entries that give that repository.

Declaring a connected project's home repository does not make any command
reach the network; only `tcw project provision`, when I run it, does.

Every connected project is placed the same way, whether it is a parent, a
child, or a project further up or down the family.
