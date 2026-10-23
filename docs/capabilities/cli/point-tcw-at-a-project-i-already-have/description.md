As a user whose machine lays out connected projects differently from the way
the committed manifests describe it, I tell TCW where a connected project
actually sits here, without editing any file that another machine reads. I set
`TCW_PROJECT_<ID>` — the project's ID, uppercased, with hyphens as
underscores — to the folder holding that project's `.tcw/` folder. For a
lasting answer on one machine, the personal manifest
`.tcw/tcw-manifest.local.yaml` does the same in a file (see [Record where other
projects are in a manifest](tcw://C/cli/record-where-other-projects-are-in-a-manifest)).

The variable decides over every manifest and over the search for the folder
(see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)). That ordering is what
makes it useful: the case I need it for is an entry that places the project in
the wrong folder, and a variable consulted only after the entry failed could
never correct it.

Naming a folder this machine does not have is not an error. The lookup carries
on to the manifests exactly as though the variable were unset, so I can
configure one set of variables once — for a cloud environment, a CI runner, a
workstation — and let sessions that hold different subsets of the repositories
each use the part that applies to them.

Naming something that is here and is wrong *is* an error. A folder that holds
no TCW project, or a project with a different ID, is reported and refused
rather than quietly ignored, so a mistyped variable tells me what it found
instead of doing nothing.

Every command that resolves connected projects honours the same variable,
because it is read when the connections are loaded rather than by any one
command. `tcw validate` notes on standard error each variable in effect and
where it points, so a connection that resolves only because of a variable is
never a mystery to the next person reading it. A committed manifest entry the
variable overrides is reported only when that entry is itself wrong, and then as
a warning rather than an error, since it does not decide on this machine; an
overridden entry that is correct is not reported at all.

**My statement reaches a component store too, not only a project.** When a
store's declared home repository is the repository of a project located here,
TCW resolves the store inside that project's folder rather than fetching a
second copy. So a workspace whose repositories are normally nested, and which
I have cloned side by side instead, reads the right board from these variables
alone — without a symlink, without editing a file another machine reads, and
without a machine-specific absolute path in
[`work.path`](tcw://C/work/configure-the-work-store-location).

On a disk that ignores letter case, the path I give may spell the folder in any
case: it is the same folder, from the primary checkout or from a linked git
worktree alike.
