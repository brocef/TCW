As a user, I give every TCW project a canonical ID and explicitly declare its
direct parent and children under `projects:` in its `tcw-config.yaml`. Declared
projects may be nested, siblings, or anywhere else on the filesystem: a location
says where TCW can open a project on this machine, while the ID remains its
stable identity. Connections are declared on both sides and fail closed when a
declaration is *inconsistent* — an ID that disagrees with the project it names,
a cycle, configuration that cannot be read. A connection I simply cannot follow
from this machine is a different thing and is treated as one: the project drops
out of the graph, my other commands keep working, and `tcw validate` reports each
project it could not reach as `unresolved` every run. A project some other
declaration resolved is not reported, since both sides name every connection and
one of those two is routinely a path only the other machine has. Whether two
projects name each other is decided between the two projects that are actually
here — two configs naming each other at paths belonging to different machines
are correct, not broken. A command that needs the absent project tells me which
one and where I declared it, rather than claiming I never declared it. An entry
may also carry a `repository` block beside its location, saying where that
project comes from for a machine that does not have it — see [Declare a
connected project's home
repository](tcw://C/cli/declare-a-connected-projects-home-repository). A bare
location string keeps meaning exactly what it always did. From an enclosing
project I address descendant work as `<project-id>/<folder>`, and TCW derives
deeper ancestry from the declared connections rather than from where things sit
on disk: no folder is scanned to discover a project and no relation is inferred
from nesting or git layout. Inside a linked git worktree TCW does read git
metadata, for one narrow purpose — working out where a relative location was
written from, so it still points where it was meant to (see [Run TCW from inside
a git worktree](tcw://C/cli/run-from-a-git-worktree)). That never adds, removes,
or re-parents a project. `tcw projects list` shows the result — see [List
connected projects](tcw://C/cli/list-connected-projects).

Several declared projects may place independent work stores in one
orchestrating repository. Their canonical project IDs, not the containing folder
names, remain the namespaces; TCW rejects two projects that resolve to the same
physical work-store folder.
