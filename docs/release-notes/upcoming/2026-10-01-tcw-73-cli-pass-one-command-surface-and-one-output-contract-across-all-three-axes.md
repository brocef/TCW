## One command surface and one output contract

Every `tcw` command now follows the same rules, so a script or an agent can
rely on what it prints and what its exit code means. The full table of renamed
and removed commands is in `docs/migration-guide-2.8-to-3.0.0.md`.

- **stdout carries only what a command produces.** `tcw work new` prints the
  new item's full slug, `tcw taxonomy add` and `tcw capabilities add` print the
  new entry's path, list and search commands print one path or slug per line,
  and a command that only changes something prints nothing. Everything said to
  a person — progress, warnings, errors — goes to stderr, and every file a
  command writes or removes is named there (`wrote …`, `removed …`). Every
  `--json` output is one object that starts with `"schema": 1`.
- **Exit codes mean one thing everywhere:** 0 OK, 1 an error, 2 a malformed
  command or value, 3 refused, 4 not found, 5 Jira or a declared project could
  not be reached, 6 the item moved but something after the move failed.
  `tcw --help` lists them.
- **Every command's `--help`** ends with what it prints and what it writes,
  and gives examples. Options have one long spelling each; the short ones
  (`-s`, `-p`) are gone.
- **`tcw validate` prints its findings on stdout,** one per line as
  `error: …`, `warning: …` or `unresolved: …`, with the count on stderr. Only
  an error fails the run. It checks the project you run it in; it no longer
  walks into child projects, and its path argument and `--no-recurse` are gone.
- **Renamed and removed commands.** `tcw work nodes` is now `tcw projects
  list`. `tcw <axis> init` is `tcw init <axis>`. `tcw taxonomy check` and
  `tcw capabilities check` are part of `tcw validate`. `tcw work procedure
  prompt <name>` is `tcw work procedure <name>`. `tcw capabilities extends
  <id> [--rm]` is `tcw capabilities extends add|rm <id>`, and `capabilities
  list --local-only` is `--local`. The `tcw taxonomy <path>` and
  `tcw capabilities <path>` shorthands are gone; use `show`.
- **`tcw taxonomy add` reads its description from stdin only,** as
  `tcw capabilities add` reads its body.
- **Taxonomy and capability edits are no longer staged in git.** They appear as
  ordinary unstaged changes; commit them yourself, or with a `post` hook.
- **`tcw provision --refresh` is gone.** `tcw provision` obtains what is
  missing and never fetches into a checkout you already have.
- **`connected-projects:` in `tcw-config.yaml` is now `projects:`,** with the
  same `parent`, `children` and `upstream` entries. The old key is an error that
  names the migration guide.
- **The capability fields `Planning doc` and `Tracker` are retired.** Setting
  either is refused, and `tcw validate` reports a record that still has one.
