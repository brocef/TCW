## Changed

- The plugin's session-start install pins `tcw-cli` to the plugin's own
  version (`pipx install --force tcw-cli==<version>`), and the version warning
  for an older CLI advises the same pinned command in place of
  `pipx upgrade tcw-cli`. (TCW-118)

## Fixed

- A refused `tcw://` address is quoted whole in the error, scheme included,
  rather than without its `tcw://`. (TCW-118)
- A store `path` or `tcw -C` target written with an uppercase scheme, such as
  `TCW://p1.path/x`, is refused as a malformed address instead of being looked
  for as a folder named `TCW:`. (TCW-118)
- `tcw validate` no longer repeats the config file's absolute path inside a
  finding already placed at that file, when a store cannot be opened.
  (TCW-118)
- `tcw capabilities set --parent` refuses, with exit code 2 and nothing
  written, a parent that is the capability itself or whose chain of parents
  comes back to it; before, the write succeeded and only `tcw validate`
  reported it. (TCW-118)
- A stage-named folder in the work store, which only a 2.x layout makes, is
  reported with a pointer to the 2.8-to-3.0 migration guide again. (TCW-118)
- Merging configuration clears the recorded list places of `work.tags` when a
  later layer replaces the list with a value that is not a list. (TCW-118)
- The `note:` naming the personal configuration that changed a stage's prompt
  names only the files and variables whose list is used, not one a later list
  without `inherit: true` replaced. (TCW-118)
- `tcw capabilities rm` and `tcw taxonomy rm` name each object still referring
  to the one being removed by its full identifier, as `tcw capabilities reset`
  does, instead of a bare id-path. (TCW-118)
- `tcw capabilities rm` refuses to remove a capability that another capability
  names as its `parent`, which before left that `parent` dangling. (TCW-118)
- `tcw capabilities rm`, `tcw capabilities reset` and `tcw taxonomy rm` remove
  each organising folder the removal leaves empty, and name it on standard
  error, as `move` does; before, the empty folder stayed and `tcw validate`
  warned `holds no TCW object`. (TCW-118)
- `tcw taxonomy rename` and `tcw capabilities rename`/`move` onto a name that
  differs from an existing folder only in letter case name that folder as it
  is spelled on disk. (TCW-118)
- When several projects fetched by `tcw project provision` have a problem in
  their own files, the refusal names each one's folder and how to undo its
  fetch, not only the first one's. (TCW-118)
- Test docstrings describe the own-scope list instead of the `--local` flag
  TCW 4.0 replaced. (TCW-118)
- `tcw capabilities drift`'s `unreviewed` line says the capability's status is
  still the one it inherits, instead of the TCW 3.x term "upstream default".
  (TCW-118)
- `tcw project config --origin`'s help says that an inherited setting a parent
  cannot give stops it, as it does, instead of saying it prints whatever is
  wrong. (TCW-118)
- `tcw migrate`'s A14 report is now tested for an absolute path taken from a
  parent project's `tcw-config.yaml`, which it names by its path from the
  project. (TCW-118)
- `tcw migrate` run before a related project still in TCW 3.x form now ends
  its summary with `check after the run stopped: a related project is still
  TCW 3.x; run 'tcw validate' once it is migrated`. Before, it gave no sign
  that the project's own findings were never checked. (TCW-118)
- `tcw migrate`'s A8 list of related projects still in TCW 3.x form now puts
  each parent before its child, including among a workspace's descendants.
  (TCW-118)
- `tcw migrate`'s summary says `1 file written` and `1 ticket edited` for a
  count of one. (TCW-118)
- A `tcw migrate` run refused by B9 no longer lists, among its planned lines,
  a name (C12, D7) and an empty `description.md` for the override it refused.
  (TCW-118)
- `tcw project new --<axis>-path tcw://…` is refused naming
  `tcw project new`, not the `init` command 4.0 no longer has. (TCW-118)
- `tcw project config --origin`'s `# skipped:` line names the override
  variable a Jira credential name came from, instead of ending in an empty
  name. (TCW-118)
- The advice for a missing taxonomy or capabilities store names `--id <id>`
  only where no project with an ID is found; inside one it says
  `tcw project new <axis>`. (TCW-118)
- `tcw project provision` with no store declaring a repository says
  `no store to fetch: no store declares a repository in .tcw/tcw-config.yaml`
  in place of `Nothing to provision: …`, which it printed before going on to
  provision the projects. (TCW-118)
- Exit 1's meaning, in `tcw --help`, `tcw/exit.py` and `docs/guide/cli.md`,
  covers something TCW was told to read failing, such as a configuration
  problem or an unknown project ID, which already exit 1; no exit code
  changes. (TCW-118)
- The migration guide says that a dry run in a project whose work is kept in
  Jira needs the credentials, and gives a finished Jira project's re-run with
  `--no-jira` or with Jira failing; the taxonomy and capabilities guide says a
  move changes no `parent` and how to set it; the validation guide's
  folder-and-parent warning gives its `not set` form. (TCW-118)

## Internal

- `scripts/cut_version.py X.Y.Z` cuts an untagged current version without
  bumping; it refuses an already tagged one, and refuses `patch`, `minor` and
  `major` while the current version has no tag. (TCW-118)
