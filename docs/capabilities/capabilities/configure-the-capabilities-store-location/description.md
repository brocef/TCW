As a project owner, I can keep a project's capabilities tree somewhere other than
`docs/capabilities` by setting `capabilities.path` in the project's
`.tcw/tcw-config.yaml`. Every `tcw capabilities` command, `tcw validate`,
`tcw capabilities drift`, and the web viewer follow it. Writes change files in
that folder and nothing else: no command stages or commits them, so committing
them in whichever repository holds the tree is mine to do.

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

Inheritance is unaffected: it comes from my project's parent links
(`parents:`), not from wherever the tree happens to sit, so inheriting a
parent's capabilities works the same from either location.

Nothing changes for a project that sets nothing. I can scaffold at a configured
relative path with `tcw project new --capabilities-path <path> capabilities`.
`tcw project new` refuses a `tcw://` address there; I write one into
`.tcw/tcw-config.yaml` by hand once the project exists.

Beside `capabilities.path` I can declare where the tree _comes from_, with a
`capabilities.repository` block, so a machine that has never seen it obtains it
with `tcw project provision --component capabilities` (see [declaring the home
repository](tcw://C/capabilities/declare-the-capabilities-stores-home-repository)). A tree
already present at `capabilities.path` keeps being used untouched.
