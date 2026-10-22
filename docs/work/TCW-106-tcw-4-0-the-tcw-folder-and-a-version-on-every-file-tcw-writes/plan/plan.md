# Plan — TCW 4.0: the `.tcw/` folder and a version on every file TCW writes

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). The
lifecycle is driven by the released 3.x CLI from the same worktree, whose
own configuration stays in the 3.x format (spec, Non-goals).

Every step ends with the named tests passing. The full suite runs at steps 5
and 9.

## Step 1 — one module that knows the project's files

**Creates** `tcw/project_files.py`, importing nothing from `tcw` but
`tcw.__version__`:

- `TCW_FOLDER = ".tcw"`, `CONFIG_NAME = "tcw-config.yaml"`,
  `LOCAL_CONFIG_NAME = "tcw-config.local.yaml"`, and
  `SENTINEL = ".tcw/tcw-config.yaml"`, `LOCAL_SENTINEL =
  ".tcw/tcw-config.local.yaml"` (relative paths, so `root / SENTINEL` keeps
  working everywhere it is written today, and every message that prints
  `SENTINEL` names the new place); `LEGACY_SENTINEL = "tcw-config.yaml"`.
- `root_of(config_path) -> Path`: the project root for a path to
  `.tcw/tcw-config.yaml` (its folder's folder).
- `find_marker(start) -> tuple[Path, str] | None`: Design 2's walk,
  returning the folder and `"4"` or `"3"`; a folder named `.tcw` is never
  a 3.x marker (Design 2.3).
- `VERSION_KEY = "tcw-version"`, `version_line() -> str`
  (`"tcw-version: <__version__>\n"`), and `version_problem(mapping) -> str |
  None`: Design 3.4 rows a–d, in that order, comparing `(major, minor)`
  as a pair with the running version's, patch ignored; a non-string value
  (an unquoted `4.0`) is row b. This is the one function TCW-107's manifests
  and TCW-111's state files will call (Design 3.6).
- `KEY_PATTERN` (the project-ID pattern) and `key_problems(mapping) ->
  list[(key_path, message)]`: Design 5.1–5.3, walking mappings and list
  entries.
- `legacy_message(folder) -> str`: Design 4.1's wording.

**Changes** `tcw/config.py:37-38`, `tcw/store/fs.py:194-199,254`,
`tcw/store/project.py:23` to import `SENTINEL` and the local name from it
rather than define their own.

**Proves it:** new `tests/test_project_files.py`: `find_marker` on a 4.0
folder, a 3.x folder, both, `.tcw/` without the file, nothing; each row of
`version_problem` including a YAML float `4.0`, `4.0` as text, a lower 4.x
minor, the running version, a newer minor and a newer major; `key_problems`
on `Work`, `my_key`, `a--b`, `-a`, `not_tags` (with the `write 'not-tags'`
hint), a boolean key (`on`), a number key, and a key inside a list entry;
`find_marker` from inside `<root>/.tcw/`. Unit tests only, so the rest of the
suite is untouched by this step.

## Step 2 — the five version fields

**Changes** `pyproject.toml`, `tcw/__init__.py`, `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` to `4.0.0`
(spec Design 3.5). Done with `scripts/cut_version.py`'s own
`bump_files(root, "3.0.2", "4.0.0")` from a one-off Python call, so no
commit or tag is made.

**Proves it:** `tests/test_plugin_manifests.py`, `tests/test_cut_version.py`
(AC 15).

## Step 3 — a test helper for writing a project's configuration

**Creates** `tests/projectfiles.py` with `config_file(root)` (makes
`root/.tcw/` and returns the path), `local_config_file(root)`,
`write_config(root, text="")` and `write_local_config(root, text="")`, which
put `version_line()` first unless the text already holds a `tcw-version`
line, and `write_config_file(path, text)` for tests that hold a path or dump
YAML. (Corrected at implement: `write_config_data` was never needed, since the
tests that dump YAML already hold the path. The version line goes only in front
of text that stays one mapping with it; a null document such as `---` or `~`,
a list, or bytes that are not UTF-8 are written as given, so a test of a broken
file still tests that file.)

**Changes** every test that writes or reads a project's configuration
(75 files; the list is `grep -rln 'tcw-config' tests`), mechanically by a
one-off script kept in the scratchpad, not the repository:

- `(<expr> / "tcw-config.yaml").write_text(<args>)` → `write_config(<expr>, <args>)`;
  the same for `.local.yaml`, `write_bytes` and `yaml.safe_dump(…, open(…))`.
- `<name> = <expr> / "tcw-config.yaml"` → `<name> = config_file(<expr>)`, and
  that name's later `.write_text(` calls → `write_config_file(<name>, `.
- Remaining literal `"tcw-config.yaml"` in assertions on messages: changed
  by hand to the path the message now prints (`.tcw/tcw-config.yaml`).

Then the failures are read one by one. An assertion is changed only where
the message it checks has legitimately moved (a path), never to make a
different behavior pass. `tests/fixtures/tcw-config-2.8.yaml` is a 2.x
fixture and stays as it is.

This step and step 4 land together: the helper writes the new layout, which
only the step-4 code reads.

## Step 4 — reading the project from `.tcw/`

**Changes**

- `tcw/store/fs.py`: `find_project_root` (`:293-302`) returns the folder of
  the nearest `.tcw/tcw-config.yaml` (via `find_marker`), or None when the
  nearest marker is a 3.x one — it never walks past a 3.x project to an
  outer 4.0 one, so a library caller cannot silently act on the wrong
  project (the command itself is refused at step 6);
  `personal_file_tracked` and `ignore_personal_file` (`:202-233`) look at
  and write `.tcw/tcw-config.local.yaml` and `.tcw/.gitignore` (rule
  `/tcw-config.local.yaml`); `write_sentinel` and `init` (`:259-272`,
  `:604-760`) create `.tcw/` and start a new file with `version_line()`;
  `load_config` (`:863-881`) calls `version_problem` and raises
  `ValueError` on rows a–d, so every edit and `init` refuses first
  (Design 3.4a); `_is_store_layout` (`:3133`) looks for
  `.tcw/tcw-config.yaml`;
  the `.parent` of a config path used as a project root (`:3133`, `:3197`,
  `:3450` and the call sites the grep `SENTINEL` lists) becomes `root_of`.
- `tcw/store/config_edit.py:420-426` (`plan_id`): a new `id:` line goes
  after a top-level `tcw-version` line rather than above the first key.
- `tcw/store/project.py`: every `config_path.parent` / `cfg.path.parent` /
  `source_config.parent` used as a project folder (`:576`, `:635`, `:701`,
  `:713`, `:781`, `:798`, `:841`, `:846`, `:890`, `:918`, `:1027`) becomes
  `root_of(...)` (Design 1.3); `_config_file` (`:110-115`) resolves the project folder,
  not `.tcw/`.
- `tcw/config.py`: `Origin.folder` (`:70-74`) is the project root for the
  `project` and `local` layers (Design 1.4), the file's folder for `user`;
  the local layer reads `root / LOCAL_SENTINEL` (`:650-655`).
- `tcw/cli.py`, `tcw/validate.py` (`:146`, `:202`, `:229`, `:236`, `:360-372`,
  `:672-691`), `tcw/work/cli.py:630-635`: the literal `"tcw-config.yaml"`
  joined to a root becomes `SENTINEL`.
- `evals/seed_fixture.py:499,615-622`: the fixture's config path and the
  message.

**Proves it:** the suite as converted in step 3; new tests in
`tests/test_project_files_cli.py` for AC 1, 2, 3 (one project and a monorepo
fixture), 4, 10, 13a (relative locator and `TCW_PROJECT_<ID>`), 14a, 14b,
14c.

## Step 5 — the version and naming checks in the configuration reader

**Changes** `tcw/config.py`:

- `load_config` (`:541-605`): after `_read` of the project file and of the
  local file, `version_problem` adds a `Problem(file, (), …)` for rows a–d
  (corrected at implement: with the key path `("tcw-version",)` the line read
  `tcw-version: tcw-version must be…`, since every row's message already
  names the key, with the file as its subject); the key is then removed from the mapping before
  `_list_problems`, `_allowed` and `_merge` (Design 3.3).
- `key_problems` runs on all three files' mappings (project, user, local)
  before merging, each as a `Problem` naming the file.
- `tcw/work/config.py:97-212`: the `When` field and the accepted key become
  `not-tags` (the dataclass attribute stays `not_tags`, as a Python name);
  the "expected" messages name `not-tags`; `_binding_json`
  (`tcw/work/cli.py:549-554`) prints `not-tags`.

**Changes** the tests that build a `when:` with `not_tags`
(`grep -rn not_tags tests`) to `not-tags`, except those asserting the new
refusal.

**Proves it:** AC 7 (both files, four rows), 8, 9 (`tcw work tags` on a file
with `tcw-version: 4.0.0` while the running version is `4.0.0`, and on one
naming a lower 4.x minor written by the test), 11, 12, in
`tests/test_project_files_cli.py`. Then **the full suite**
(`.venv/bin/pytest -n 8`, and bare `.venv/bin/pytest` at step 9).

## Step 5a — this repository's own configuration on `v4`

Tests such as `tests/test_repo_lifecycle.py` load this repository's own
configuration with the code under test, so on `v4` the repository needs a
4.0 configuration. The released 3.x CLI that drives the lifecycle needs the
3.x one. Both stay until TCW-116 (spec, Non-goals).

**Creates** `.tcw/tcw-config.yaml`: the root `tcw-config.yaml` with
`tcw-version: 4.0.0` first and `not_tags` written `not-tags`, and
`.tcw/.gitignore`.

**Creates** `tests/test_repo_config_pair.py`: the two files hold the same
configuration once the version line is removed and `not-tags` is read as
`not_tags`, so a 3.x patch merged from `main` into the root file cannot
leave the 4.0 copy behind unnoticed.

**Proves it:** `tests/test_repo_lifecycle.py` and the new test pass with the
`v4` code; the 3.x CLI still reads the worktree (`tcw work show TCW-106`).

## Step 6 — refusing a 3.x project

**Changes**

- `tcw/store/fs.py`: `refuse_legacy_project(start)` raising `BackendError`
  (exit 1) with `legacy_message(folder)` when `find_marker` returns a 3.x
  folder.
- `tcw/cli.py:_dispatch` (`:640-660`): calls it first, for every command,
  `validate` and `init` included. `--version` and `--help` exit inside
  argparse before `_dispatch` and are unaffected.
- `tcw/store/project.py`: where a connection's folder has no
  `.tcw/tcw-config.yaml` (`_read_config`, the `"no tcw-config.yaml here"`
  problem at `:574`, and `_resolve_override` at `:758-760`), a folder
  holding a root `tcw-config.yaml` is reported with Design 4.1's wording and
  not read (Design 4.2): as `<folder>: is a TCW 3.x project …`, or
  `TCW_PROJECT_<ID> names a TCW 3.x project …` for a variable (corrected at
  implement: `legacy_message` after the folder the problem is printed under
  named the folder twice). `_read_config` (`:552-640`) reads a connected project's
  file itself, outside `tcw.config`, so it also calls `version_problem` on
  the mapping it read and records a problem for rows a–d (Design 3.4 holds
  for every reader).
- `tcw/validate.py`: the Design 4.3 warning when a 4.0 project's root also
  holds `tcw-config.yaml`.

**Proves it:** AC 5 (four commands, nothing written, `--version` exits 0),
6, 13, 14, in `tests/test_project_files_cli.py`.

## Step 7 — records

**Changes** on `v4`, in this repository's 3.x-format ledgers (converted with
everything else in TCW-116):

- New `docs/capabilities/cli/read-a-file-by-the-format-version-it-records/`
  (`meta.yaml`, `description.md`), status `Supported`, subject `project`,
  feature `project-registry`.
- `docs/capabilities/cli/scaffold-the-doc-trees/description.md`,
  `cli/validate-a-project/description.md`,
  `cli/override-the-team-configuration-for-myself/description.md`,
  `work/configure-the-work-lifecycle/description.md`,
  `work/configure-procedures/description.md`: the sentences the spec's
  Capability changes name.
- New `docs/taxonomy/format-version/`; `docs/taxonomy/project/description.md`
  and `docs/taxonomy/personal-configuration/description.md`.

**Proves it:** `.venv/bin/tcw`'s ledger readers cannot read this 3.x
repository, so the records are checked with the 3.x CLI:
`tcw validate` from the worktree, and `tcw work advance --dry-run` at the
end of implement (the records gate).

## Step 7a — notes for the later children

`tcw work comment` on TCW-118: `cut_version.py` refuses the current version
(`:168-169`) and `v4` already reads `4.0.0`, so the release changes it to
allow cutting the current version when no tag for it exists. On TCW-116:
decide whether `tcw migrate` converts or reports a user-wide file holding
`not_tags` (spec Design 5.5), and that this repository is proven on a copy of
`main`, then its root `tcw-config.yaml` deleted on `v4`.

## Step 8 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: where the configuration lives | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99 design, "How 4.0 is built"); recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | no | Nothing a command does to a ticket changes. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: where a setting is declared | Deferred to TCW-117, as above. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written: the `.tcw/` folder, the version line, the naming rule, 3.x projects refused. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added / Changed / Internal. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: file location | Deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: `not-tags`, `tcw-version` | Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-1's layout | Deferred to TCW-117, which owns `docs/use-cases.md` for 4.0. |

The two `upcoming/` files are named
`TCW-106-tcw-4-0-the-tcw-folder-and-a-version-on-every-file-tcw-writes.md`.

## Step 9 — the suite as CI runs it

Bare `.venv/bin/pytest` from the worktree root (AC 16). A failure is fixed in
the step it belongs to, not with a skip.

## Verification the tests cannot do

- The QA plan's scenarios are run by hand with `.venv/bin/tcw` in throwaway
  folders under the scratchpad, at qa.
- That this repository's lifecycle still runs on `v4` with the 3.x CLI:
  `tcw work show TCW-106` and `tcw validate` from the worktree after step 7.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1, 2, 3, 4, 10, 13a, 14a, 14b, 14c | 4 |
| 7, 8, 9, 11, 12 | 5 |
| 5, 6, 13, 14 | 6 |
| 15 | 2 |
| 16 | 9 |

Every step traces to an acceptance criterion except 3 (the test helper, which
5, 6 and 9 rely on), 7 (records, the spec's Capability changes) and 8
(documentation).
