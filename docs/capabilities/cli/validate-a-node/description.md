As a user, I run `tcw validate` to validate the active project and every
registered descendant project recursively, including each project's YAML,
`tcw://` links, and bounded component stores. Recursive diagnostics identify
their project. I use `--no-recurse` to validate only the active project, or pass
a path to narrow validation to one active-project file or directory. Graph
validation always runs even when content checks are narrowed. Missing or invalid
IDs, malformed registrations, missing targets, mismatched keys, nonreciprocal
edges, cycles, legacy inheritance maps, and unreachable inheritance targets
fail closed with migration guidance.

A parent/child connection is declared on both sides; an `upstream` connection is
declared only by the reader and needs no counterpart. An upstream is never
validated as part of the reader: only its own config is read, and problems in
its connections are its own. A project declared as its own upstream, or declared
upstream while also reachable as family, is a problem. A former child still
naming a parent that now reads it as an upstream is a warning, printed as
`warning: …`, so neither project is blocked mid-migration.

Validation also tells a store's three failure modes apart in different words: a
`<component>.path` that is simply wrong, a store declared in another repository
but not yet provisioned here (naming the declared remote and `tcw provision`),
and a malformed `repository` block (naming the offending configuration key). The
last is reported even when no local store can be opened to report it through, so
a typo is never hidden behind a dead path.

All three apply to each of the three components. A store that cannot be opened
is reported as one problem beside the others rather than ending the run, so one
unprovisioned tree does not hide the rest of a node's faults.

A taxonomy or capabilities file left over from before 2.5.0 (`config.yaml` or
`.config.yaml` at the root of the tree), which is no longer read, is reported
once for each tree that has one — including a tree kept outside
`docs/<component>` or in another repository, and a run whose component checks
were skipped because of a YAML problem. To find it, validation now opens a
tree it did not check before, and any failure to open that tree is reported:
a tree declared in another repository but not yet provisioned (as the work
store already was), a `<component>.path` that does not exist on this machine,
and an `extends` naming a project this checkout cannot reach. In a project
whose completion runs `tcw validate` first, any of these can refuse
`tcw work complete`.

**Two faults are counted as two.** A node whose `<component>.path` names a
directory holding no store, and which also declares a home repository it has
not obtained, has two problems, and I am told both — the path is reported on its
own line and counted separately, rather than disappearing behind the
declaration's message. The configured path is examined whether or not the store
went on to open, so I hear about a path I mistyped even when the declared store
provisions perfectly well and I would otherwise never learn I am reading a
second copy.

A configured path that simply **does not exist** stays silent when a home
repository is declared. That is the ordinary state of a checkout holding only
the code, which is the case the declaration exists for, and reporting it would
give every provisioned node a permanent problem.

In the work store it checks every item: an `item.yaml` that cannot be read is
an error naming the file and the key, and the other checks still run over the
items that can be read. A parent or blocker that names no item is a warning
(printed `warning: …`, so it does not fail the run); one in a project that
cannot be reached is printed `unresolved: …` and does not fail it either. An
item whose stage is not in the stage table, or is disabled in this project, is
reported. While an item is still being worked, its `capabilities.yaml` is
checked for paths that cannot be right. A work store shared with another
project in this repository, which would mix their items, is an error.

The summary counts only failures, so a run whose only output is warnings
passes.
