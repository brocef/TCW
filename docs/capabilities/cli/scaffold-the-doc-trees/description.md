As a user, I run `tcw init --id <project-id> [taxonomy|capabilities|work]` to
scaffold component trees in the current git work tree and create a
`tcw-config.yaml` marker with a canonical project ID. The per-component mirrors
accept the same `--id`. On an already configured node I may omit `--id` or repeat
the same value; a conflicting value is rejected. I can backfill a legacy marker
with `tcw init --id <project-id>` without losing tags or other configuration.

Scaffolding the `work` component also writes `.gitignore` rules that
[keep resolved work out of git](tcw://C/work/keep-resolved-work-out-of-git) —
the `completed/` and `discarded/` folders stay in the tracked tree, but what
lands in them does not. Re-running init on an older node adds any rule it lacks;
deleting the rules opts out.

For the work component I may instead pass `--work-path <path>` at top level or
`--path <path>` to `tcw work init`. TCW records that locator on the owning node,
scaffolds the target repository, and writes ignore rules relative to the target
repository. It replaces only an exactly pristine generated default scaffold;
existing work requires a manual migration.

Every refusal `init` makes happens before it writes anything at all — no marker,
no config entry, no folders. It turns down a target outside a Git repository, one
whose items the repository's ignore rules would hide (so nothing filed there
would be tracked), one behind a broken symlink, a status folder that is really a
file, and a `docs/work` that is a symlink elsewhere. A `tcw-config.yaml` it
cannot read reports that plainly rather than failing part-way through.
