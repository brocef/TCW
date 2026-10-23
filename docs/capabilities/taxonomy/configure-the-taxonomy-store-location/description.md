As a project owner, I can keep a project's taxonomy tree somewhere other than
`docs/taxonomy` by setting `taxonomy.path` in `tcw-config.yaml`, using an
absolute path or one relative to the owning project's primary checkout. Every
`tcw taxonomy` command, `tcw validate`, and the web viewer follow it. Writes
change files in that folder and nothing else: no command stages or commits them,
so committing them in whichever repository holds the tree is mine to do.

This is the same thing `work.path` has always done for work items, arriving late
for the trees — see [the work-store equivalent](tcw://C/work/configure-the-work-store-location).
Nothing changes for a project that sets nothing: the tree resolves to
`docs/taxonomy` exactly as before, whether or not that folder exists.

I can scaffold the layout at a configured location with
`tcw init --taxonomy-path <path> taxonomy`.

The location is a plain path relative to the project, or a folder address:
`tcw://<project>.path/<folder>` names a folder in that project's root, and
`tcw://<project>.<namespace>.path/<folder>` one inside that project's own
store, wherever its checkout sits on this machine. It is resolved from the
project whose configuration holds it. An absolute path or one starting with
`~` is refused in the shared `.tcw/tcw-config.yaml`; a folder that sits
elsewhere on one machine is placed by an entry in
`.tcw/tcw-manifest.local.yaml`.
