TCW 4.0 is a major release. It changes where a project keeps its files, which
now sit together in a `.tcw/` folder, and how projects relate to each other:
a project names its parents, in place of the 3.x `projects:` list and
`extends`. A TCW 3.x project must be migrated with `tcw migrate` before 4.0
will work in it; [the migration guide](../migration-guide-3.X-to-4.0.0.md)
says how.

## Upgrading

- To move a project across, follow
  [the migration guide](../migration-guide-3.X-to-4.0.0.md).
- Keep any CI job or other automation that installs `tcw-cli` at
  `tcw-cli<4` until the project it works on is migrated.
- Everyone working on a project upgrades together: TCW 4.0 refuses a 3.x
  project's files except to migrate them.
- Commit your work, or back it up, before running `tcw migrate` for real,
  that is without `--dry-run`.
- From 4.0, the plugin installs the CLI of its own version
  (`tcw-cli==<the plugin's version>`), so a plugin update brings the matching
  CLI, and holding the plugin at an older version holds the CLI it installs
  at that version too. To stay on 3.x, keep the plugin at 3.0.2 by pinning it
  to the tag `v3.0.2`. Claude Code: `claude plugin marketplace remove tcw`,
  then `claude plugin marketplace add brocef/TCW#v3.0.2` and
  `claude plugin install tcw@tcw`. Codex:
  `codex plugin marketplace remove tcw`, then
  `codex plugin marketplace add brocef/TCW --ref v3.0.2` and
  `codex plugin add tcw@tcw`; Codex refreshes its marketplaces every time it
  starts, so without the pin it moves to 4.0 on its own. Pi:
  `pi remove git:github.com/brocef/TCW`, then
  `pi install git:github.com/brocef/TCW@v3.0.2`. One case needs a step of its
  own: a 3.x plugin installing on a machine for the first time still takes
  the newest CLI, so on such a machine run `pipx install --force 'tcw-cli<4'`
  once; after that the 3.x plugin leaves the CLI alone.
- TCW 3.x keeps a home: the branch `3.x` holds the last 3.x code. If a 3.x
  patch is ever needed, it is cut on that branch and published by pushing its
  tag.

## Fixes

- When TCW refuses a `tcw://` address, the error now quotes the address you
  wrote, `tcw://` included.
- A store location or `tcw -C` target written `TCW://…` now gets the address
  error that says what is wrong, instead of a confusing "not a directory" or
  "no such folder".
- `tcw validate` names `.tcw/tcw-config.yaml` once, not twice, when a store
  cannot be opened.
- `tcw capabilities set --parent` now refuses a parent that would make the
  capability its own ancestor, instead of writing it and leaving
  `tcw validate` to find the loop.
- `tcw validate` on a TCW 2.x work store points you to the 2.8-to-3.0
  migration guide, since `tcw migrate` does not convert 2.x.
- With two override variables setting one stage's prompt, the note on
  standard error names only the one whose prompt is used.
- `tcw capabilities rm` no longer removes a capability that another one names
  as its parent; it refuses and names the one to repoint first.
- Removing the last capability or term in a folder now removes the empty
  folder too, so `tcw validate` no longer warns about it afterwards.
- When you migrate a project before its parent, `tcw migrate` now says that
  its check of the result stopped at the parent, and asks you to run
  `tcw validate` once the parent is migrated.
- `tcw migrate` lists the related projects still to be migrated with parents
  first, in the order to migrate them.
- `tcw migrate`'s summary uses the singular for a count of one.
- Refusing a `tcw://` address given to `tcw project new --work-path`, TCW now
  names `tcw project new` rather than an `init` command that no longer exists.
- `tcw project config --origin` now says which environment variable a skipped
  Jira credential name came from.
- Inside a project that already has an ID, the advice for adding a taxonomy or
  capabilities store no longer asks for `--id`.
- `tcw project provision` no longer says "Nothing to provision" before going
  on to fetch the projects it names; it says there is no store to fetch.
- The migration guide now says that a dry run in a project whose work is kept
  in Jira needs the Jira credentials, or `--no-jira`.
