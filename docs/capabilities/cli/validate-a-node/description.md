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
`work.path` that is simply wrong, a store declared in another repository but not
yet provisioned here (naming the declared remote and `tcw provision`), and a
malformed `repository` block (naming the offending configuration key). The last
is reported even when no local store can be opened to report it through, so a
typo is never hidden behind a dead path.
