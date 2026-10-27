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
- `tcw validate` reports an unfinished `tcw migrate` (its progress record still in `.tcw/`) as an error naming `tcw migrate` to finish it, instead of passing with advice to delete the 3.x root `tcw-config.yaml`. (TCW-118)
- A state file (`tcw-taxonomy.yaml`, `tcw-capability.yaml`, `tcw-work-item.yaml`) with no `tcw-version` is told only to add the line, no longer to run `tcw migrate`, which converts nothing in it. (TCW-118)
- `tcw work move <item> --into <KEY>` (or `<project>.work/<KEY>`) moves the item into the folder of
  the item carrying that key, instead of making a new folder named after the key; a key no item
  carries stops the move (exit 4). (TCW-118)
- `tcw work|taxonomy|capabilities move --into` takes a `tcw://` object address, as every other
  option naming an object does. (TCW-118)
- A `tcw://` address written with an upper-case scheme (`TCW://…`) as an object argument is refused
  as an address, not as a folder to rename by hand. (TCW-118)
- `tcw capabilities set <path> --parent <path>` on an inherited capability is refused as naming the
  capability itself, instead of writing the capability it overrides as its parent. (TCW-118)
- `tcw work move --into` no longer makes a folder named like a tracker key at any depth: `--into TCW-1/sub` or `--into 2026/TCW-5` is refused with exit code 2, where it used to make `TCW-1/` beside the item carrying that key (and, in Jira, write that path to the ticket). A key-shaped folder that already exists can still be used as part of the path. (TCW-118)
- `tcw -C <address>` run from a TCW 3.x project, or from one whose configuration has problems, now says
  it was resolving that address, and from which folder, before the refusal.
- The 3.x to 4.0 migration guide gives one `grep` command that finds every removed command and flag in
  agent-instruction files and scripts.
- The migration guide says that `TCW_SLUG` holds the full identifier in 4.0, that a `generate:` script's
  input is `"schema": 2`, and that converting tickets from any copy affects every 3.x user of that Jira
  project.
- `tcw validate` no longer warns about a `README.md` directly inside an organising folder of any store,
  which 3.x accepted, so a migrated capability ledger that describes its group folders can reach 0
  warnings. Any other file there, and a `README.md` in a store's root, still warn.
- `tcw migrate` names each file it writes once: `.tcw/.gitignore`, written twice in a run, is one change
  line with the conversions of both writes.
- The migration guide says `.tcw/tcw-migration.yaml` is written only when there is something to record,
  and that in a family migrated parents first every run but the last stops its check, so the other
  projects need a `tcw validate` once all are migrated.
- `tcw migrate` refuses, with blocker B18, a run that would write a file git ignores, such as `.tcw/`
  under a root `.gitignore` that ignores everything and re-includes only what is tracked, naming the rule
  and the line to add; it used to write the ignored files and delete the tracked `tcw-config.yaml`.
- `tcw migrate` lists a project's upstream before its parent when that parent names the same upstream, so
  the converted project no longer gets a load-order warning in every `tcw validate`.
- The load-order warning names the `parents:` list to reorder, and the order that would keep every other
  project's own order, instead of only "set it in '<project>'".
- `tcw migrate` no longer reports its D8 load-order report a second time as A12.
- In a linked git worktree, a relative manifest path or store path that leads
  out of the worktree is first read as written: when it lands in a checkout,
  main or linked, of another repository (of the repository the entry or store
  declares, when it declares one), it is read there, and only otherwise
  beside the main checkout. The search for a project with no manifest entry
  starts from such a worktree too, and from the main checkout when that finds
  nothing. Worktrees made one inside another, such as
  a child repository's worktree placed inside its workspace's worktree, read
  each other instead of the folders they were made from; `tcw migrate` reads
  a 3.x store path the same way. (TCW-118)
- `tcw migrate` refuses, with blocker B19 and nothing written, a run that
  would change files in another checkout of a repository the project sits
  in, such as a linked worktree's main checkout. (TCW-118)
- `tcw migrate` names a planned file in no checkout the project sits in, such
  as one in a clone of a store's repository, by its absolute path, instead of
  a relative path climbing towards `/`. (TCW-118)

## Removed

- `tests/test_repo_config_pair.py`, which kept this repository's 3.x root
  `tcw-config.yaml` and its 4.0 `.tcw/tcw-config.yaml` in step until the
  repository was migrated, and the root `.gitignore` line
  `/tcw-config.local.yaml`, the 3.x place of the personal configuration file.
  (TCW-118)

## Internal

- This repository is migrated to TCW 4.0. (TCW-118)
- This repository's own taxonomy and capability records are now read by the
  documentation scan for 3.x forms; `UNMIGRATED_RECORDS`, which left them out
  until the migration, is deleted. (TCW-118)
- `scripts/cut_version.py X.Y.Z` cuts an untagged current version without
  bumping; it refuses an already tagged one, and refuses `patch`, `minor` and
  `major` while the current version has no tag. (TCW-118)
