As a user, I run `tcw init --id <project-id> [taxonomy|capabilities|work]` to
make the current folder a TCW project: it creates `.tcw/tcw-config.yaml`, whose
first line records the version of the TCW that wrote it (`tcw-version: 4.0.0`),
with a canonical project ID, and scaffolds the stores I name, or all three when
I name none. Nothing is written at the project's root. It works whether or not the folder is in a git repository. There are no
per-axis `init` commands; `tcw init work` scaffolds the work store alone. On an
already configured project I may omit `--id` or repeat the same value; a
conflicting value is rejected. I can backfill a marker that has no ID with
`tcw init --id <project-id>` without losing tags or other configuration; the ID goes below the version
line, which no edit changes.

`init` prints nothing on standard output. Every file it writes and every folder
it creates is named on standard error (`wrote <path>`, `created <path>/`), and it
stages and commits nothing: committing the result is mine to do. Inside a
repository it adds `/tcw-config.local.yaml` to `.tcw/.gitignore`, beside the
personal file it names, unless that rule is already there with or without the
`/`, so a person's own configuration stays out of version control. Outside one it
says, in a `note:` line, that keeping that file out is mine to do.

Each store is one folder, with an empty `.gitkeep` so git keeps it while it is
empty. The work store is one folder of item folders: there are no status folders
and no ignore rules.

Each store's location is mine to choose: `--work-path`, `--taxonomy-path`, and
`--capabilities-path` scaffold that store somewhere other than
`docs/<component>` and record the choice in `.tcw/tcw-config.yaml`, so later commands
find it without being told again. A new work location replaces a default
`docs/work/` only when it holds no work item; moving existing work is mine to do.
A store whose home repository is declared is not scaffolded: `init` tells me to
run `tcw provision` instead, so an empty local store never hides the real one.

Every refusal `init` makes happens before it writes anything at all — no marker,
no config entry, no folders. It turns down a folder it would make that is really
a file, a `docs/work` that is a symlink elsewhere, and an unknown store name (a
usage error, exit 2). A `.tcw/tcw-config.yaml` it cannot read, or whose
`tcw-version` it cannot read, reports that plainly rather than failing part-way
through. In a TCW 3.x project, a folder with `tcw-config.yaml` at its root and
no `.tcw/` folder, `init` refuses like every other command, naming
`tcw migrate`.
