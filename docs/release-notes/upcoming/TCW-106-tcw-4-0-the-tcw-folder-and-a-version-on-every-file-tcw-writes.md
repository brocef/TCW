## TCW's files move into a `.tcw/` folder

A project's configuration now lives in a `.tcw/` folder at the project's root:
`.tcw/tcw-config.yaml` for the team, and `.tcw/tcw-config.local.yaml` for your
own settings. `tcw init` creates the folder, and inside a git repository it
keeps your personal file out of version control with a rule in
`.tcw/.gitignore`, instead of a line in the root `.gitignore`.

Paths in the configuration mean what they meant before: they are read from the
project's root, not from inside `.tcw/`. A `file: docs/lifecycle/spec.md`
binding still names `docs/lifecycle/spec.md` in your project, and a script a
binding runs still sees the project root as `TCW_CONFIG_DIR`. Running a command
from any subfolder, `.tcw/` itself included, acts on the project as before.

## Every file says which version of TCW wrote it

The first line of `.tcw/tcw-config.yaml` is now `tcw-version: 4.0.0`, the
version of TCW whose file format the file follows. TCW writes it when it creates
the file, and no ordinary edit changes it. Your personal file needs the same
line; if it is missing, TCW tells you exactly what to add.

Before reading a file, TCW checks that line, so it never misreads a file it does
not understand. A file with no version, or one from TCW 3, is refused with a
message pointing to `tcw migrate`; a file written by a newer TCW than yours is
refused with a message asking you to upgrade. `tcw validate` reports the same
problems, and also warns when an old `tcw-config.yaml` is still sitting at the
root of a project that has moved to the `.tcw/` folder.

## TCW 3 projects need converting

A project still laid out for TCW 3, with `tcw-config.yaml` at its root and no
`.tcw/` folder, is refused by every command with a message naming
`tcw migrate`, and nothing is written to it. A connected project still in the
TCW 3 layout is reported the same way and is not read. `tcw --version` and
`--help` work anywhere.

## One spelling for every setting name

Every setting name is now lowercase letters and digits joined by single
hyphens, like project IDs. A binding's `when: {not_tags: [...]}` becomes
`when: {not-tags: [...]}`; the old spelling is refused with a message saying
what to write. `tcw work lifecycle --json` prints `not-tags` too.
