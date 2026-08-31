As a project owner, I can keep a project's taxonomy tree somewhere other than
`docs/taxonomy` by setting `taxonomy.path` in `tcw-config.yaml`, using an
absolute path or one relative to the owning project's primary checkout. Every
`tcw taxonomy` command, `tcw validate`, and the web viewer follow it, and writes
commit in the Git repository that actually contains the tree rather than the
project's own.

This is the same thing `work.path` has always done for work items, arriving late
for the trees — see [the work-store equivalent](tcw://C/work/configure-the-work-store-location).
Nothing changes for a project that sets nothing: the tree resolves to
`docs/taxonomy` exactly as before, whether or not that folder exists.

I can scaffold the layout at a configured location with
`tcw init --taxonomy-path <path> taxonomy`.
