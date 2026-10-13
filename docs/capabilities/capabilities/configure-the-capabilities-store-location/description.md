As a project owner, I can keep a project's capabilities tree somewhere other than
`docs/capabilities` by setting `capabilities.path` in `tcw-config.yaml`, using an
absolute path or one relative to the owning project's primary checkout. Every
`tcw capabilities` command, `tcw validate`, `tcw capabilities drift`, and the
web viewer follow it. Writes change files in that folder and nothing else: no
command stages or commits them, so committing them in whichever repository holds
the tree is mine to do.

Inheritance is unaffected: `extends` still resolves against my project, not
against wherever the tree happens to sit, so federating another project's
capabilities works the same from either location.

Nothing changes for a project that sets nothing. I can scaffold at a configured
location with `tcw init --capabilities-path <path> capabilities`.
