# Implement round 1 — TCW-106

Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). The lifecycle was driven by the released 3.x CLI, which reads
the root `tcw-config.yaml`. This is the first implement round, so it answers no
rejection.

## What was done, step by step

- **Step 1 — `tcw/project_files.py`.** Covers the project's files
  (`SENTINEL = ".tcw/tcw-config.yaml"`, `LOCAL_SENTINEL`, `LEGACY_SENTINEL`),
  `root_of`, `find_marker` (Design 2), `version_line`, `version_problem`
  (Design 3.4 rows a–d), `without_version`, `key_problems` (Design 5) and
  `legacy_message` with its shared wording `LEGACY_PROJECT` (Design 4.1).
  Unit tests are in `tests/test_project_files.py`. Commit `e1652691`.
- **Step 2 — the five version fields** read `4.0.0` (commit `e1652691`).
  `tests/test_plugin_manifests.py` passes (AC 15).
- **Step 3 — the test helper.** `tests/projectfiles.py` provides
  `config_file`, `local_config_file`, `write_config`, `write_local_config` and
  `write_config_file`. The suite was converted to it, the failures were read
  one at a time, and the following were fixed:
  - **Old fixtures.** One fixture's name clashed with a local helper in
    `tests/test_taxonomy.py`: it is now `write_project_config`. The conversion
    had also routed some writes of files that are not configuration through the
    helper; they are plain writes again.
  - **Changed paths in messages.** Assertions on messages whose path moved
    now expect `.tcw/tcw-config.yaml`, `.tcw/tcw-config.local.yaml` and
    `.tcw/.gitignore`. Most of them match a prefix or the whole line, so the
    old form cannot pass. Where the root `.gitignore` used to be written, the
    test now also asserts it is absent.
  - **`tests/test_config_edit_writers.py`.** These tests compare bytes. Their
    `config()` now checks that the first line is the version line and returns
    the rest, so every edit test also proves Design 3.2.
  - **Behavior the spec changed.** A null document (`---`, `~`) has no
    `tcw-version`, so `write_sentinel` now refuses it rather than giving it an
    ID (Design 3.4 row a). A `null` personal file is a version problem rather
    than an empty layer. And `projects.children.Bad ID` is now reported by the
    naming rule (Design 5.1) before the registry's own check runs.
- **Step 4 — reading the project from `.tcw/`.**
  - Product code: `tcw/config.py`, `tcw/store/fs.py`,
    `tcw/store/config_edit.py`, `tcw/store/project.py`, `tcw/validate.py`,
    `tcw/cli.py`, `tcw/work/config.py` and `tcw/work/cli.py` (commit
    `66673deb`).
  - `evals/seed_fixture.py` reads `.tcw/tcw-config.yaml`. Its check for a bare
    fixture inside a project now uses `find_marker`, so a 3.x project above
    the fixture is caught too.
  - Help and error text that named `tcw-config.yaml` now names
    `.tcw/tcw-config.yaml`: the `init`, `config show` and three `extends`/`tags`
    "Writes" lines, the `builtin:` refusal, and the Jira credentials message
    (commit `e6dc72f6`).
- **Step 5 — the version and naming checks.** These are in commit `66673deb`,
  with two corrections in commit `81dc0f2c`:
  - The version problem carries no key path, since every row's message names
    `tcw-version` itself.
  - A 3.x connection names its folder once.
- **Step 5a — this repository's own configuration.** `.tcw/tcw-config.yaml` is
  the root file with `tcw-version: 4.0.0` added as its first line and
  `not_tags` written as `not-tags`. `.tcw/.gitignore` was added. The root
  `tcw-config.yaml` is kept. `tests/test_repo_config_pair.py` was
  mutation-checked: it went red for a changed value in the copy and for
  `not_tags` left in it. Commit `d6efa7d7`.
- **Step 6 — refusing a 3.x project.** In commit `66673deb`, with the message
  fix above.
- **New CLI tests.** `tests/test_project_files_cli.py` has 62 tests, each
  named after the criterion it proves. They cover AC 1–14c, including 13a,
  14a, 14b and 14c.
  - **Mutation checks.** Twenty-three breaks were each made alone and then
    reverted, and every one turned its criterion's tests red for the reason
    named. The breaks covered:
    - writing no version line;
    - the root `.gitignore`;
    - the rule written twice;
    - the old note;
    - `.tcw/` counted as a project on its own;
    - `.tcw` itself taken for a 3.x project;
    - no 3.x refusal;
    - a 3.x marker taking precedence over a 4.0 one;
    - no older-version or newer-version check;
    - a personal file that is never version-checked;
    - the version merged as a setting;
    - the ID put above the version;
    - `.tcw/` used as the folder for `file:` bindings and `TCW_CONFIG_DIR`;
    - no naming rule, and no `not-tags` hint;
    - the old JSON key;
    - a 3.x connection that is never read;
    - `root_of` returning `.tcw/`;
    - a connected project's version never checked;
    - the raw reader never checking the version;
    - no warning for a leftover root file;
    - the tracked-file check looking at the old place.
  - **AC 7 caught a real defect.** It failed first on
    `tcw-version: tcw-version must be…`, the key named twice, which led to the
    step 5 correction.
- **Step 7 — records.** See "Records changed" below. Commits `398719b5` and
  `48803a79`.
- **Step 7a — not done in this round.** Recording the notes on TCW-118 (the
  current-version cut) and TCW-116 (the user-wide file's `not_tags`, and
  proving `tcw migrate` on a copy of `main`) needs `tcw work comment`. That is
  left to the dispatching session, which keeps every board write.
- **Step 8 — documentation.** See "Documentation entries" below. Commit
  `39603cc4`.
- **Step 9 — the suite as CI runs it.** See "Test results".

## Test results

Run just now from the worktree root:

- `.venv/bin/pytest -n 8 -q -p no:cacheprovider`:
  `5266 passed, 118 skipped in 96.26s`.
- Bare `.venv/bin/pytest -q`: `5266 passed, 118 skipped in 458.76s`.
- The skip count fell from 119 to 118 because a test that runs only while an
  `upcoming/` entry file exists now runs: this item added one.
- The released 3.x CLI, run as `tcw validate` from the worktree:
  `0 errors, 0 warnings, 0 unresolved`.
- `tcw work show TCW-106` still reads the item.
- The earlier bare run failed 4 tests in `tests/test_documented_cli_surface.py`,
  because the records named `tcw migrate`, which does not exist on `v4` yet.
  The records were reworded (commit `48803a79`).

## What the plan or spec got wrong

- **Plan step 3's helper.** The plan named a `write_config_data` helper; it was
  never needed, because the tests that dump YAML already hold the path, and
  `write_config_file(path, text)` serves them. The plan also did not say that
  the version line cannot go in front of a null document or a list. Both are
  corrected in the plan.
- **Plan step 5's problem shape.** `Problem(file, ("tcw-version",), …)` printed
  `tcw-version: tcw-version must be…`. Design 3.4's message shapes take the file
  as their subject, so the problem now has no key path. Corrected in the plan.
- **Plan step 6 and spec Design 4.2's wording.** A 3.x connection is printed
  after its folder. With `legacy_message` the folder appeared twice:
  `<folder>: <folder> is a TCW 3.x project …`. It now reads
  `<folder>: is a TCW 3.x project …`, and a `TCW_PROJECT_<ID>` variable reads
  `TCW_PROJECT_<ID> names a TCW 3.x project …`. Corrected in the plan and in
  spec Design 4.2.
- **AC 7 and AC 9 cannot be tested at TCW 4.0.** "A lower 4.x minor version is
  read" and "an older 4.x version is kept by an edit" need an older 4.x version
  than the running one, and none exists while TCW is 4.0. Both are tested
  in-process with the running version patched to 4.3.0. The spec does not say
  this; it is recorded here rather than in the spec.
- **The spec's records cannot name `tcw migrate` yet.** The spec's Capability
  changes and Risks accept messages naming a command that does not exist on
  `v4`. `tests/test_documented_cli_surface.py` rightly refuses records that
  name a verb the CLI does not have. The records therefore say "the command
  that converts it to TCW 4", and TCW-116 can name it once it exists.
- **A consequence the spec states but nowhere spells out.** An existing
  `.tcw/tcw-config.yaml` that is empty, or a null document, has no
  `tcw-version`, so `tcw init` refuses it (row a) rather than filling it in.
  This follows from Design 3.4, which exempts no file. It is recorded here so
  that review can decide whether an empty file should be exempt.

## Records changed

- **New capability** `cli/read-a-file-by-the-format-version-it-records`
  (`cap-4f0a61`): Supported, Subject `project` and `format-version`, Feature
  `project-registry`.
- **Changed capabilities** (the sentences the spec's Capability changes name):
  `cli/scaffold-the-doc-trees`, `cli/validate-a-project`,
  `cli/override-the-team-configuration-for-myself`,
  `work/configure-the-work-lifecycle` and `work/configure-procedures`.
- **Taxonomy.** The new term `format-version`. The changed terms are `project`
  and `personal-configuration`.
- **Format and contradictions.** The ledgers stay in the 3.x file format, and
  the 3.x `tcw validate` reports no error or warning. Checked against the
  standing records: no other capability now contradicts these. Records that
  still name the root `tcw-config.yaml` in passing, outside the behavior this
  item changes, belong to TCW-117's 4.0 rewrite.

## Documentation entries

All eight entries from `tcw work docs` were evaluated with the
`documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass. |
| `docs/guide/jira.md` [Jira-Change] | no | Nothing a command does to a ticket changes. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | Deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written: `TCW-106-tcw-4-0-the-tcw-folder-and-a-version-on-every-file-tcw-writes.md`. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added, Changed and Internal, same name. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes | Deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes | Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | yes | Deferred to TCW-117. |
