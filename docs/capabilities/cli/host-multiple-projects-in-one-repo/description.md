As a user, I give every TCW project a canonical ID and explicitly declare its
direct parent and children under `projects:` in its `.tcw/tcw-config.yaml`,
by ID only. Where each one is on this machine is not written there: it is in a
manifest (see [Record where other projects are in a
manifest](tcw://C/cli/record-where-other-projects-are-in-a-manifest)), or TCW
finds the folder from the ID (see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)). Declared projects may be
nested, siblings, or anywhere else on the filesystem: the location says where
TCW can open a project on this machine, while the ID remains its stable
identity. Connections are declared on both sides and fail closed when a
declaration is *inconsistent* — an entry placing a folder that holds another
project, one ID found in two folders, a cycle, configuration that cannot be
read. A connected project that is simply not on this machine is a different
thing and is treated as one: the project drops out of the graph, my other
commands keep working, and `tcw validate` reports it as `unresolved` every run.
A command that needs the absent project tells me where its manifest entry
places it, and how to fetch it when the entry names its repository, rather
than claiming I never declared it. A `projects:` entry that still holds a
location, as in TCW 3, is refused with the manifest entry to write instead.
From an enclosing project I address descendant work as `<project-id>/<folder>`,
and TCW derives deeper ancestry from the declared connections rather than from
where things sit on disk: no relation is inferred from nesting or git layout,
and the search for a folder never looks inside a project. Inside a linked git
worktree TCW reads git metadata for one narrow purpose — working out where a
relative path was written from, so it still points where it was meant to (see
[Run TCW from inside a git worktree](tcw://C/cli/run-from-a-git-worktree)).
That never adds, removes, or re-parents a project. `tcw projects list` shows the
result — see [List connected projects](tcw://C/cli/list-connected-projects).

Several declared projects may place independent work stores in one
orchestrating repository. Their canonical project IDs, not the containing folder
names, remain the namespaces; TCW rejects two projects that resolve to the same
physical work-store folder.
