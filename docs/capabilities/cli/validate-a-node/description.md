As a user, I run `tcw validate` to validate the active project and every
registered descendant project recursively, including each project's YAML,
`tcw://` links, and bounded component stores. Recursive diagnostics identify
their project. I use `--no-recurse` to validate only the active project, or pass
a path to narrow validation to one active-project file or directory. Graph
validation always runs even when content checks are narrowed. Missing or invalid
IDs, malformed registrations, missing targets, mismatched keys, nonreciprocal
edges, cycles, legacy inheritance maps, and unreachable inheritance targets
fail closed with migration guidance.

Validation also tells a store's three failure modes apart in different words: a
`<component>.path` that is simply wrong, a store declared in another repository
but not yet provisioned here (naming the declared remote and `tcw provision`),
and a malformed `repository` block (naming the offending configuration key). The
last is reported even when no local store can be opened to report it through, so
a typo is never hidden behind a dead path.

All three apply to each of the three components. A store that cannot be opened
is reported as one problem beside the others rather than ending the run, so one
unprovisioned tree does not hide the rest of a node's faults.

A reference to a work item this project once held and has since completed or
discarded is **not** a problem. Finishing work is normal, and reporting every
reference to finished work as a mistake buries the real ones. A reference to a
slug the project never held is still reported, in the same words as before —
that distinction is the point.

**A reference to a resolved item gives the same answer in every checkout.** It no
longer matters whether the machine running validation is the one that resolved
the item, because the record the answer comes from is tracked. That is what makes
validation usable as a gate on finishing work.

Note the limit, which is narrower than "reads only what is committed": validation
walks the working tree, not the index, so a file that is on disk but untracked —
including the documents inside a resolved item's own folder — is still scanned.
A mistyped reference *inside* a completed item's documents is therefore still
reported only on a machine that still has them.
