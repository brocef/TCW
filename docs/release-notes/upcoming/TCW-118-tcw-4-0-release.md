## Upgrading

- Holding the plugin at an older version now holds the CLI it installs at
  that version too.

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
