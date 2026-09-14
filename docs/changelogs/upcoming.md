# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **Eval harness: `tool_input_contains` and `tool_input_absent` predicates.**
  They search only the `input` of `tool_use` content blocks (a `Read`'s
  `file_path`, a `Bash` command), not assistant text, user messages or tool
  results, so a routing check no longer passes because a loaded skill merely
  mentions a path. `tool_input_absent` fails with "no tool calls found" when a
  transcript has no tool calls at all, so an unrecognised transcript shape
  cannot pass it vacuously. The shape is checked against hand-built transcripts
  only; the first real run must confirm it.
- **Eval harness: a `bare` fixture variant and a per-case `fixture` key.**
  `python evals/seed_fixture.py --bare <dir>` commits the fixture's code files
  to a repository with no TCW set up. A case in `evals/evals.json` can name the
  variant it runs against in every arm. Seeding a bare fixture inside a TCW
  project raises `ValueError`, because `tcw` searches parent folders for
  `tcw-config.yaml` and would resolve to the outer project; the runner's default
  `eval-runs/` inside this checkout is such a place, so run bare cases with
  `--out` outside it.

## Changed

- **Eval harness: `files_changed_exactly` compares against the seeded commit.**
  It used to run `git diff --name-only HEAD~1 HEAD`, which measured whether the
  agent committed, and read the seeder's own last commit when the agent made
  none. It now takes the union of `git diff --name-only --no-renames
  <seeded_head>` (the working tree against the seeded commit) and `git ls-files
  --others --exclude-standard`, and fails with git's error if either command
  fails. `seed()` records `seeded_head` in its manifest, the
  runner copies it into `timing.json`, and `grade_run` passes it on. **A run
  directory recorded before this change has no `seeded_head` and now fails this
  check**, with evidence saying so, instead of returning the old misleading
  answer. The seeder excludes its own untracked `manifest.json` through
  `.git/info/exclude` so it is not counted as a change. Case B10 no longer
  expects `src/reports.py`, which the seeded fixture never changes.
- **Eval harness: fixture variants are names.** `seed(dest, variant="control")`
  takes `"customized"`, `"control"` or `"bare"` in place of `customized: bool`,
  and raises `ValueError` on anything else. `run_evals.variant_for` returns the
  name rather than a boolean.
