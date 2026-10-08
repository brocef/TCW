As a user, I run `tcw init --id <project-id> [taxonomy|capabilities|work]` to
scaffold component trees in the current git work tree and create a
`tcw-config.yaml` marker with a canonical project ID. The per-component mirrors
accept the same `--id`. On an already configured node I may omit `--id` or repeat
the same value; a conflicting value is rejected. I can backfill a legacy marker
with `tcw init --id <project-id>` without losing tags or other configuration.

Scaffolding the `work` component makes one empty folder, with a `.gitkeep` so
git keeps it: items are folders in it, and there are no status folders and no
ignore rules. `tcw work init` does the same alone.

For the work component I may instead pass `--work-path <path>` at top level or
`--path <path>` to `tcw work init`. TCW records that locator on the owning node
and makes the folder in the target repository. It replaces a default
`docs/work/` only when it holds no work item; moving existing work is mine to
do.

Every refusal `init` makes happens before it writes anything at all — no marker,
no config entry, no folders. It turns down a target outside a Git repository, one
behind a broken symlink, a folder it would make that is really a file, and a
`docs/work` that is a symlink elsewhere. A `tcw-config.yaml` it
cannot read reports that plainly rather than failing part-way through.

Each component's location is mine to choose: `--work-path`, `--taxonomy-path`,
and `--capabilities-path` scaffold that component somewhere other than
`docs/<component>` and record the choice in `tcw-config.yaml`, so later commands
find it without being told again.
