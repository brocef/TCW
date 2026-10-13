As a user, I run `tcw init --id <project-id> [taxonomy|capabilities|work]` to
make the current folder a TCW project: it creates a `tcw-config.yaml` with a
canonical project ID and scaffolds the stores I name, or all three when I name
none. It works whether or not the folder is in a git repository. There are no
per-axis `init` commands; `tcw init work` scaffolds the work store alone. On an
already configured project I may omit `--id` or repeat the same value; a
conflicting value is rejected. I can backfill a marker that has no ID with
`tcw init --id <project-id>` without losing tags or other configuration.

`init` prints nothing on standard output. Every file it writes and every folder
it creates is named on standard error (`wrote <path>`, `created <path>/`), and it
stages and commits nothing: committing the result is mine to do.

Each store is one folder, with an empty `.gitkeep` so git keeps it while it is
empty. The work store is one folder of item folders: there are no status folders
and no ignore rules.

Each store's location is mine to choose: `--work-path`, `--taxonomy-path`, and
`--capabilities-path` scaffold that store somewhere other than
`docs/<component>` and record the choice in `tcw-config.yaml`, so later commands
find it without being told again. A new work location replaces a default
`docs/work/` only when it holds no work item; moving existing work is mine to do.
A store whose home repository is declared is not scaffolded: `init` tells me to
run `tcw provision` instead, so an empty local store never hides the real one.

Every refusal `init` makes happens before it writes anything at all — no marker,
no config entry, no folders. It turns down a folder it would make that is really
a file, a `docs/work` that is a symlink elsewhere, and an unknown store name (a
usage error, exit 2). A `tcw-config.yaml` it cannot read reports that plainly
rather than failing part-way through.
