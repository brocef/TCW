As a project owner, I can keep a project's taxonomy tree somewhere other than
`docs/taxonomy` by setting `taxonomy.path` in the project's
`.tcw/tcw-config.yaml`. Every `tcw taxonomy` command, `tcw validate`, and the
web viewer follow it. Writes change files in that folder and nothing else: no
command stages or commits them, so committing them in whichever repository holds
the tree is mine to do.

The location is a path relative to the project's folder (the one holding
`.tcw/`), read the way `work.path` is, inside a linked git worktree too, or a
folder address: `tcw://<project>.path/<folder>` names a folder in that
project's folder, and `tcw://<project>.<namespace>.path/<folder>` one inside
that project's own store for that namespace, wherever its checkout sits on
this machine. An address is resolved from the project whose configuration
holds it, and a chain of addresses that leads back to a store already on it is
refused as a loop. An absolute path, or one starting with `~`, is refused in
that shared file; the refusal says that a folder that sits elsewhere on this
machine is placed by an entry in `.tcw/tcw-manifest.local.yaml`. `tcw validate`
fails when the tree is the same folder as another store, of this project or of
any project it can locate, or when one lies inside the other.

This is the same thing `work.path` does for work items — see
[the work-store equivalent](tcw://C/work/configure-the-work-store-location).
Nothing changes for a project that sets nothing: the tree resolves to
`docs/taxonomy` exactly as before, whether or not that folder exists.

I can scaffold the layout at a relative path with
`tcw init --taxonomy-path <path> taxonomy`. `tcw init` refuses a `tcw://`
address there; I write one into `.tcw/tcw-config.yaml` by hand once the project
exists.
