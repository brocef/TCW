As a user, I assign every TCW project a canonical ID and explicitly register
its direct parent and children in `tcw-config.yaml`. Registered projects may be
nested, siblings, or anywhere else on the filesystem: locators describe where
the filesystem adapter can open them, while IDs remain their stable identity.
Connections are reciprocal and fail closed when either side is missing or
inconsistent. From an enclosing project I address descendant work as
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
