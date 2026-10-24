As a user, I give every TCW project a canonical ID and name its parents under
`parents:` in its `.tcw/tcw-config.yaml`, by ID only and in order; a project
may have several parents (see [Name a project's
parents](tcw://C/cli/name-a-projects-parents)). A parent may list its children
under `children:` (see [List a project's
children](tcw://C/cli/list-a-projects-children)). Where each one is on this machine is not written there: it is in a
manifest (see [Record where other projects are in a
manifest](tcw://C/cli/record-where-other-projects-are-in-a-manifest)), or TCW
finds the folder from the ID (see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)). Declared projects may be
nested, siblings, or anywhere else on the filesystem: the location says where
TCW can open a project on this machine, while the ID remains its stable
identity. Connections fail closed when a declaration is _inconsistent_ — an
entry placing a folder that holds another project, one ID found in two
folders, a loop of parents, a listed child that does not name its parent back,
configuration that cannot be read. A connected project that is simply not on this machine is a different
thing and is treated as one: the project drops out of the graph, my other
commands keep working, and `tcw validate` reports it as `unresolved` every run.
A command that needs the absent project tells me where its manifest entry
places it, and how to fetch it (`tcw project provision <id>`) when the entry
names its repository, rather than claiming I never declared it. The TCW 3 `projects:` key is refused, with
a message saying to name parents under `parents:` and children under
`children:`. From an enclosing project I address another project's work by its
full identifier, `<project-id>.work/<folder>`, and TCW derives deeper ancestry
from the declared connections rather than from
where things sit on disk: no relation is inferred from nesting or git layout,
and the search for a folder never looks inside a project. Inside a linked git
worktree TCW reads git metadata for one narrow purpose — working out where a
relative path was written from, so it still points where it was meant to (see
[Run TCW from inside a git worktree](tcw://C/cli/run-from-a-git-worktree)).
That never adds, removes, or re-parents a project. `tcw project list` shows the
result — see [List connected projects](tcw://C/cli/list-connected-projects);
`tcw project path <id>` prints where any one of them is on this machine (see
[Find where a project is on this
machine](tcw://C/cli/find-where-a-project-is-on-this-machine)), and
`tcw project info` shows how the active one is assembled (see [See how a
project is assembled](tcw://C/cli/see-how-a-project-is-assembled)).

Several declared projects may place independent work stores in one
orchestrating repository. Their canonical project IDs, not the containing folder
names, remain the namespaces; TCW rejects two projects that resolve to the same
physical work-store folder.

A manifest inside a project of a shared repository may name where other
projects are cloned. When `tcw project provision` fetches a project that such a
manifest places, and the manifest is not the active project's own, the clone
may go only into a folder directly inside the one that holds the whole
repository, so beside the repository and never beside the package inside it (see [Fetch a
project that is not on this
machine](tcw://C/cli/fetch-a-project-that-is-not-on-this-machine)).
