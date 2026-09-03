As a user, I assign every TCW project a canonical ID and explicitly register
its direct parent and children in `tcw-config.yaml`. Registered projects may be
nested, siblings, or anywhere else on the filesystem: locators describe where
the filesystem adapter can open them, while IDs remain their stable identity.
Connections are reciprocal and fail closed when a declaration is *inconsistent*
— an ID that disagrees with the project it names, a cycle, unparseable
configuration. A connection I simply cannot follow from this machine is a
different thing and is treated as one: the project drops out of the graph, my
other commands keep working, and `tcw validate` names each project it could not
reach every run so a mistyped locator is still findable — a project some other
declaration resolved is not listed, since both sides name every connection and
one of those two is routinely a path only the other machine has. Reciprocity is decided
between the two projects that are actually here — two configs naming each other
at paths belonging to different machines are correct, not broken. A command that
needs the absent project tells me which one and where I declared it, rather than
claiming I never registered it. An entry may also carry a `repository` block beside its locator, saying where
that project comes from for a machine that does not have it — see [Declare a
connected project's home
repository](tcw://C/cli/declare-a-connected-projects-home-repository). A bare
locator string keeps meaning exactly what it always did. From an enclosing
project I address descendant work as
`<project-id>/<slug>` and TCW derives deeper ancestry from the registered graph
rather than from where things sit on disk: no directory is scanned to discover a
project and no relation is inferred from nesting or git layout. Inside a linked
git worktree TCW does read git metadata, for one narrow purpose — working out
where a relative locator was written from, so it still points where it was meant
to (see [Run TCW from inside a git worktree](tcw://C/cli/run-from-a-git-worktree)).
That never adds, removes, or re-parents a project.

Several registered projects may place independent work stores in one
orchestrator repository. Their canonical project IDs, not the containing folder
names, remain the namespaces; TCW rejects two projects that resolve to the same
physical work-store root.
