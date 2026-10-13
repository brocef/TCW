As a user whose machine lays out connected projects differently from the way its
configuration describes it, I tell TCW where a connected project actually sits
here, without editing any file that another machine reads. I set
`TCW_PROJECT_<ID>` — the project's id, uppercased, with hyphens as underscores —
to the directory holding that project's `tcw-config.yaml`.

This is the complement of declaring a connected project's home repository. That
one says where a project *comes from* when this machine does not have it; this
one says where it *is* when the configuration's location is wrong here. Both
exist because a location is a fact about one machine written into a file every
machine shares.

My statement wins over both the declared location and the `repository`
declaration. That ordering is what makes it useful: the case I need it for is a
location that resolves to the wrong place, not one that resolves to nothing, and
an override consulted only after the location failed could never correct it.

Naming a project this machine does not happen to have is not an error. The
variable falls through to the `repository` declaration exactly as though it were
unset, so I can configure one set of variables once — for a cloud environment, a
CI runner, a workstation — and let sessions that hold different subsets of the
repositories each use the part that applies to them. Neither session has to know
which case it is in.

Naming something that is here and is wrong *is* an error. A directory that holds
no `tcw-config.yaml`, or holds a project with a different id, is reported and
refused rather than quietly ignored, so a mistyped variable tells me what it
found instead of doing nothing.

Every command that resolves connected projects honours the same variable,
because it is read when the connections are loaded rather than by any one
command. `tcw provision`
therefore does not fetch a project an override resolves, and `tcw validate`
notes on standard error each variable in effect and where it points — so a
connection that resolves only because of an override is never a mystery to the next person
reading it.

**My statement reaches a component store too, not only a project.** When a
store's declared home repository is one already located here through a
connected project,
TCW resolves the store inside that copy rather than fetching a second one. So a
workspace whose repositories are normally nested, and which I have cloned side
by side instead, reads the right board from these variables alone — without a
symlink, without editing a file another machine reads, and without a
machine-specific absolute path in
[`work.path`](tcw://C/work/configure-the-work-store-location).

On a disk that ignores letter case, the path I give may spell the folder in any
case: it is the same folder, from the primary checkout or from a linked git
worktree alike.
