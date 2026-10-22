# Spec — TCW 4.0: the `.tcw/` folder and a version on every file TCW writes

Child 1 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "Requirements for TCW as a whole" 6 and 7,
"The `.tcw/` folder" (the two configuration files only), "Versions and
migration" (the version rule), and the naming rule in "Personal overrides and
environment variables". Built on the `v4` branch.

## Capability changes

- **New** `cli/read-a-file-by-the-format-version-it-records`: every file TCW
  writes records the TCW version whose format it follows, and TCW refuses a
  file whose version it cannot read, naming what to do.
- **Changed** `cli/scaffold-the-doc-trees`: `tcw init` writes
  `.tcw/tcw-config.yaml`, with its version, and the ignore rule for the
  personal file in `.tcw/.gitignore`.
- **Changed** `cli/validate-a-project`: reports a missing or unreadable
  version, a key or project ID that breaks the naming rule, and a 3.x
  `tcw-config.yaml` left at the root of a 4.0 project.
- **Changed** `cli/override-the-team-configuration-for-myself`: the personal
  file is `.tcw/tcw-config.local.yaml` and carries a version.
- **Changed** `work/configure-the-work-lifecycle` and
  `work/configure-procedures`: a binding's `when` takes `not-tags`, not
  `not_tags`.
- **Taxonomy:** new `format-version`; changed `project` and
  `personal-configuration`.

## Problem

Today a project is marked by a file at its root, and nothing records which
format a file follows.

1. The marker is `tcw-config.yaml` at the project's root: `SENTINEL` in
   `tcw/config.py:37`, `tcw/store/fs.py:254` and `tcw/store/project.py:23`.
   `find_project_root` (`tcw/store/fs.py:293-302`) returns the nearest
   folder holding that file. The personal file sits beside it
   (`LOCAL_FILE`, `tcw/config.py:38`; `LOCAL_CONFIG`, `tcw/store/fs.py:196`),
   and `tcw init` adds `/tcw-config.local.yaml` to the root `.gitignore`
   (`ignore_personal_file`, `tcw/store/fs.py:222-233`; called at
   `tcw/cli.py:76-79`). TCW-99 requirement 6 moves both files into one
   `.tcw/` folder, so a project is recognised by one folder holding all of
   TCW's own files (the manifests join it in TCW-107).
2. No file says which format it follows. `load_config`
   (`tcw/config.py:541-605`) reads whatever is there. The only defence
   against an older format is a list of retired keys
   (`refuse_retired_config`, `tcw/store/fs.py:306-326`, run for every
   command at `tcw/cli.py:651-652`). 4.0 changes the format of every file, so
   a 4.0 TCW must be able to tell a 3.x file, a 4.0 file and a file from a
   newer TCW apart without guessing from keys.
3. A `file:` binding is read relative to the folder of the file that
   declares it, and may not leave it (`Origin.folder`, `tcw/config.py:70-74`;
   `_confinement`, `tcw/config.py:502-524`). Moved into `.tcw/`, every
   project's `file: docs/lifecycle/…` binding would resolve under `.tcw/`
   and be refused for leaving it. This repository's own configuration has
   nine such bindings.
4. Project IDs already follow the rule lowercase letters and digits joined by
   single hyphens (`PROJECT_ID_PATTERN` via `validate_project_id`,
   `tcw/store/project.py:28-36`). Configuration keys do not: a binding's
   `when` takes `not_tags` (`tcw/work/config.py:97-212`, used in this
   repository's `tcw-config.yaml` under `work.stages.spec.prompt`). TCW-109
   derives an environment variable from every key, which needs every key to
   follow one rule, so the rule is set and enforced now. Every other key TCW
   defines today already follows it (`WORK_KEYS`, `STAGE_KEYS`, `HOOK_KEYS`
   in `tcw/work/config.py:40-44`; `KEYS`, `CREDENTIAL_KEYS`, `FIELD_KEYS`,
   `DELEGATION_KEYS` in `tcw/work/jira/config.py:31-37`; `PROCEDURE_IDS` in
   `tcw/store/base.py:654`; the stage names in `tcw/work/model.py`).

## Goals

1. A project is a folder holding `.tcw/tcw-config.yaml`. The active project
   is the nearest folder, the starting folder included, that holds one.
2. The personal file is `.tcw/tcw-config.local.yaml`.
3. Every `tcw-*.yaml` file TCW reads in 4.0 carries a version, and TCW
   refuses a file whose version is missing, malformed, older than 4.0 or
   newer than the running TCW, each with its own message.
4. A 3.x project (a `tcw-config.yaml` at the root and no
   `.tcw/tcw-config.yaml`) is refused by every command with a message naming
   `tcw migrate`.
5. Every key in every configuration file follows the naming rule, and
   `not_tags` becomes `not-tags`.
6. Paths in the configuration keep meaning what they meant: relative to the
   project's root, not to `.tcw/`.

## Non-goals

- Manifests, finding other projects' folders, and `.tcw/`'s other files
  (TCW-107).
- The state files of objects (`tcw-taxonomy.yaml` and the others, TCW-111).
  They follow the version rule set here; this item writes none.
- Converting a 3.x project (`tcw migrate`, TCW-116). Until then the message
  names a command that does not exist yet on `v4`; it ships in the same
  release.
- Converting this repository with `tcw migrate`. That is TCW-116's proof
  that the command works (TCW-99 success criterion 2), run on a copy of
  `main`, which stays 3.x until `v4` merges. On `v4` this repository holds
  both configurations until then: the root `tcw-config.yaml`, which the
  released 3.x CLI driving its lifecycle reads, and `.tcw/tcw-config.yaml`,
  which the code under test reads (Design 4.3 applies to it). A test keeps
  the two the same.
- Guides and skills that describe the configuration file's location or
  teach `not_tags` (`skills/configure/references/work.md`,
  `docs/guide/configuration.md`), and the eval cases that grade which files
  an agent changed (`evals/evals.json`) (TCW-117). Until then `v4` teaches
  a key it refuses; nothing is released in between. Only the capability and taxonomy records whose behavior this
  item changes are updated here.
- The user-wide file (`~/.config/tcw/config.yaml`). TCW never writes it and
  it is not a `tcw-*.yaml` file, so it carries no version. It is still
  checked against the naming rule, since it holds configuration keys.
- Unknown keys at the top level of `tcw-config.yaml` (a known gap in
  `docs/use-cases.md`, S-9). The naming rule checks a key's spelling, not
  whether TCW knows it.

## Design

### 1. The `.tcw/` folder

1.1. The project's configuration is `<root>/.tcw/tcw-config.yaml` and its
personal file `<root>/.tcw/tcw-config.local.yaml`. The folder's name and
place are fixed; no setting moves it.

1.2. A folder is a TCW project when it holds `.tcw/tcw-config.yaml` as a
file. A `.tcw/` folder without that file does not make a project.

1.3. **The project root is the folder holding `.tcw/`** — for a path to a
configuration file, its folder's folder, never its own folder. Every path
that was relative to the project root stays relative to it: store paths,
the folder a command runs from, `TCW_PROJECT_ROOT`, a relative `projects:`
locator (`path: ../app` in `<root>/.tcw/tcw-config.yaml` names
`<root>/../app`), the folder a declared `repository` is provisioned under,
the folder a `TCW_PROJECT_<ID>` variable names, and the root of a connected
project read from its configuration file's path (`tcw/store/project.py`
`:635`, `:701`, `:713`, `:758`, `:781`, `:1027`; `tcw/store/fs.py:3133`).
One function turns a configuration file's path into its project root, and
every one of these sites calls it.

1.4. **A file in `.tcw/` is read as though it sat at the project root** for
`file:` bindings and for `TCW_CONFIG_DIR`: the declaring file's folder, for
both, is the project root. `file: docs/lifecycle/spec.md` in
`.tcw/tcw-config.yaml` names `<root>/docs/lifecycle/spec.md`, and may not
leave `<root>`, exactly as today. The user-wide file keeps its own folder.

1.5. `tcw init` creates `.tcw/` and writes `.tcw/tcw-config.yaml`. As in
3.x, TCW helps keep the personal file untracked but never depends on it
being untracked (the design: keeping it out of git is the owner's job); the
help moves with the file. Inside a git repository it adds `/tcw-config.local.yaml` to `.tcw/.gitignore` (the
leading `/` limits the rule to that folder), unless a line there already
reads that or `tcw-config.local.yaml`. Outside a repository it prints the
same `note:` as today, naming `.tcw/tcw-config.local.yaml`.
`tcw validate`'s warning for a tracked personal file looks at the new
place.

### 2. Finding the active project

2.1. From the starting folder (the current directory, resolved), each folder
is checked from the nearest outwards, up to the filesystem root.

2.2. The first folder that holds `.tcw/tcw-config.yaml` is the active
project, whether or not it also holds a root `tcw-config.yaml`.

2.3. A folder that holds a `tcw-config.yaml` file but no
`.tcw/tcw-config.yaml` is a 3.x project, unless the folder is itself named
`.tcw`: that is a 4.0 project's own folder, never a project, and the search
goes on to its parent (so a command run from inside `<root>/.tcw/` acts on
`<root>`). If it is reached before any 4.0
project, the command is refused (Design 4).

2.4. With neither, the search goes on outwards; reaching the filesystem root
means there is no project, as today.

### 3. The version every `tcw-*.yaml` file records

3.1. **The field is `tcw-version`,** a key of the file's top-level mapping.
Its value is the version of the TCW that created the file, or that last
migrated it, written as text: `tcw-version: 4.0.0`. TCW writes it as the
file's first line, and its edits keep it there (`tcw init`'s `id` goes
after it). A reader accepts it anywhere in the top-level mapping.

3.2. **It is set when TCW creates a file and changed only by a migration.**
An edit TCW makes to an existing file (`tcw init` giving it an `id`,
`tcw work tags`, `tcw taxonomy extends`, a store path) never adds, removes
or changes it.

3.3. **It is file information, not configuration.** It is removed from each
file's mapping before the layers are merged: it is not shown by
`tcw config show`, no layer overrides another's, and the personal-file
allowlist neither needs nor refuses it.

3.4. **Reading it.** For each of `.tcw/tcw-config.yaml` and
`.tcw/tcw-config.local.yaml` (when present), in this order, the first that
applies is a configuration problem naming the file and `tcw-version`:

| # | The file's `tcw-version` | Message (shape) |
| - | ------------------------ | --------------- |
| a | missing | `has no tcw-version: add 'tcw-version: <running version>' as its first line, or, for a TCW 3.x file, run 'tcw migrate' in this project`. The file is still read as a TCW 3.x file. This wording was changed at qa, at the user's request, on 2026-10-22: it used to say first that the file is read as a TCW 3.x file and only at the end what line to add, and a person reading it should see the line to add first |
| b | not a YAML string matching `^[0-9]+\.[0-9]+(\.[0-9]+)?$`. An unquoted `4.0` is a YAML number and is refused by this row; `"4.0"` and `4.0.0` are accepted | `must be a TCW version written as text, such as '4.0.0'` |
| c | major version below 4 | `is in the format of TCW <X.Y>; run 'tcw migrate' in this project` |
| d | the pair (major, minor) compares greater than the running TCW's pair, compared as a pair (major first); the patch number is ignored, so a `4.0.5` file is read by 4.0.3 | `was written by TCW <X.Y>, newer than this TCW (<running>); upgrade TCW` |

Otherwise the file is read.

3.4a. **Who checks.** One function, `version_problem`, decides the row, and
every reader of a `tcw-*.yaml` file calls it: the layered reader
(`tcw.config.load_config`), the raw reader (`tcw.store.fs.load_config`,
which then refuses with a `ValueError`, so `tcw init`, `tcw provision` and
every edit to the file refuse before writing), the registry's own read of a
connected project (`_read_config`), and `tcw validate`'s direct reads. For
the active project's files it is a configuration problem: every command
stops on it, exit 1, `tcw validate` included, which reports it as an error.
For another project's file (a connected, upstream or delegation project) it
is a problem with that connection, reported the way an unreadable connected
configuration is today, and that project is not read. The readers that
deliberately never refuse (`declared_repository`,
`declared_connected_projects`) treat such a file as declaring nothing, as
they treat an unreadable one.

3.5. The running TCW's version is `tcw.__version__`. On `v4` the five
version fields move to `4.0.0` in this item, so the files a development
build writes are 4.0 files. `scripts/cut_version.py` refuses to cut the
version already current (`:168-169`), so TCW-118 changes it to allow that
when no tag for the version exists yet; this item records that on TCW-118.

3.6. The same rule, under the same field, applies to every later `tcw-*.yaml`
file (manifests in TCW-107, state files in TCW-111). The check is one
function that each of those readers calls.

### 4. Refusing a 3.x project

4.1. Every command, `tcw validate` and `tcw init` included, first finds the
nearest project marker (Design 2). When that is a 3.x project it refuses
with exit 1 and one line naming the folder:
`<folder> is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4`.
`tcw --version` and `--help` do not look for a project and are not refused.

4.2. A project reached through a 3.x `projects:` connection whose folder is
a 3.x project is reported as that connection's problem with the same
wording, printed after the folder it is about (`<folder>: is a TCW 3.x
project …`), and is not read. (`projects:` itself is replaced in TCW-107 and
TCW-108; until then connections are followed to `<folder>/.tcw/tcw-config.yaml`.)

4.3. A 4.0 project that still holds a root `tcw-config.yaml` (for example a
migration someone finished by hand) is read as 4.0, and `tcw validate`
warns: `tcw-config.yaml: a TCW 3.x configuration file at the root of a TCW 4 project; TCW 4 reads .tcw/tcw-config.yaml only, so delete this one`.

### 5. The naming rule

5.1. A project ID, and every key of every mapping in
`.tcw/tcw-config.yaml`, `.tcw/tcw-config.local.yaml` and the user-wide file,
is one or more groups of lowercase letters and digits joined by single
hyphens: `^[a-z0-9]+(-[a-z0-9]+)*$`. A key breaking it is a configuration
problem naming the file and the key path:
`key '<key>' must be lowercase letters and digits joined by single hyphens`.

5.2. Keys inside a list entry (a binding's `blob`, `when`, `tags`) are
mapping keys and are checked the same way. Values are not checked: tags,
messages and Jira status names keep their own rules. A key YAML reads as
something other than text (`on:` and `yes:` as booleans, `1:` as a number)
is refused with `key <key> must be text: lowercase letters and digits
joined by single hyphens`. Keys are matched as written, with no stripping.

5.3. A binding's `when` takes `tags` and `not-tags`. `not_tags` is refused
by rule 5.1 like any other key; the message for it adds `; write 'not-tags'`.
The JSON that `tcw work lifecycle --json` prints for a binding's `when`
uses `not-tags` too (`_binding_json`, `tcw/work/cli.py:549-554`).

5.5. The user-wide file is shared by every TCW installed for that person,
3.x and 4.0 alike, and under rule 5.1 a 4.0 TCW refuses a `not_tags` that
3.x requires. Whether `tcw migrate` converts or only reports the user-wide
file is TCW-116's decision; this item records it on TCW-116.

5.4. Project IDs keep their existing rule and reserved words
(`validate_project_id`), which already match 5.1.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| Finding the active project from a folder (Design 2) | deployment | Filesystem detail. A store that is not a folder of files is opened by its own means; the folder walk is how a checkout is recognised. |
| The `.tcw/` folder and its two files (Design 1) | deployment | Filesystem detail, by TCW-99's split ("What any store must support"). |
| Reading and stamping `tcw-version` (Design 3) | deployment | A property of a file's format. A database records its own schema version its own way; nothing in the model reads it. |
| Refusing a 3.x project (Design 4) | deployment | Recognises a 3.x folder layout; another store has no 3.x folders. |
| The naming rule for keys and project IDs (Design 5) | model | Any store can check a name's spelling. It is a rule on configuration, which every store's project has. |

No backend operation is added or changed; the twelve operations in
`tcw/work/backend.py` are untouched, and the Jira backend behaves the same.

## Use cases

- **UC-1 (a single project).** The layout becomes `.tcw/tcw-config.yaml`
  plus `.tcw/.gitignore` instead of `tcw-config.yaml` plus a root
  `.gitignore` line. The file holds one more line (`tcw-version`), written
  by `tcw init`. No extra configuration, output or slowness: finding the
  project checks two names per folder instead of one. Any subfolder still
  works as a starting point (Design 2).
- **UC-2 and UC-7 (a library others read; a public library).** A reader's
  connection to a library still in the 3.x format is reported as needing
  `tcw migrate` there (Design 4.2), not misread. The two must move to 4.0
  together, as TCW-99 says.
- **UC-3 (a monorepo).** The nearest `.tcw/` decides the active project, so
  `apps/server` still acts on the server, not the root (Design 2.2). A
  monorepo migrated partway refuses from inside a 3.x package even though
  its root is 4.0 (Design 2.3): the nearest marker decides, and running
  `tcw migrate` in each package fixes it.
- **UC-4 (a planning workspace) and UC-6 (a project not on this machine).**
  Connections are followed to `<folder>/.tcw/tcw-config.yaml`; one that
  cannot be reached is reported as it is today. A store kept in another
  repository is untouched.
- **UC-5 (a shared Jira project).** Not affected: no Jira operation changes,
  and nothing is stored on tickets.
- **UC-8 (several families).** Not affected; finding other projects is
  TCW-107.
- **S-4 (worktrees, clones).** A worktree holds its own tracked
  `.tcw/tcw-config.yaml`; its missing personal file behaves as today.
  Reading the main checkout's personal file from a worktree is TCW-107's.
- **S-5 (personal configuration).** The personal file moves into `.tcw/`,
  must carry `tcw-version` (Design 3.4), and keeps its allowlist.
- **S-9 (upgrades).** The core of this item: a file says which format it
  follows, a 3.x file is refused naming `tcw migrate`, and a file from a
  newer TCW is refused naming an upgrade, so neither is misread.
- **S-10 (things TCW does not own).** A dependency folder holding its own
  `.tcw/` would still be taken for the project when a command runs from
  inside it, as with today's `tcw-config.yaml`; the walk only goes outwards,
  and nothing scans downwards.
- **S-11 (version control).** TCW still writes an ignore rule and commits
  nothing. It never checks git before acting.

Checklist: 1 (where it looks) Design 2; 2 (whose things) only the active
project's own files are written; 3 (reading across projects) Design 4.2;
4 (backends) the litmus table; 5 (who is present) nothing asks a person;
6 (harness) the CLI carries everything; 7 (stopping halfway) `tcw init`
writes its config change in one atomic write, as today; 8 (single project)
UC-1 above; 9 (older and newer TCW) Design 3.4 and 4; 10 (testing the setup
claimed) the criteria below build monorepo and connected-project fixtures,
not only one project.

## Acceptance criteria

1. In an empty folder, `tcw init --id demo` creates `.tcw/tcw-config.yaml`
   whose first line is `tcw-version: <tcw --version's number>` and which
   holds `id: demo`; no `tcw-config.yaml` is written at the root.
2. Inside a git repository, the same command writes `.tcw/.gitignore`
   holding the line `/tcw-config.local.yaml`, and writes no root
   `.gitignore`. Run again, it adds no second line. Outside a repository
   the `note:` names `.tcw/tcw-config.local.yaml`.
3. From `<root>/a/b`, `tcw work list` in a project at `<root>` acts on
   `<root>`. In a monorepo fixture with projects at `<root>` and
   `<root>/apps/server`, the same command from `<root>/apps/server/src`
   acts on the server.
4. A folder holding `.tcw/` with no `tcw-config.yaml` in it is not a project:
   from inside it, with no other project above, `tcw work list` gives the
   same "not in a project" refusal as an empty folder.
5. In a folder holding only a root `tcw-config.yaml` (a 3.x project), each of
   `tcw work list`, `tcw validate`, `tcw init --id x` and `tcw config show`
   exits 1 and prints the Design 4.1 message naming the folder and
   `tcw migrate`; nothing is written. `tcw --version` exits 0.
6. A 4.0 project nested inside a 3.x project's folder is the active project
   from inside itself (Design 2.2), and the 3.x project is refused from a
   folder of its own outside the nested one (Design 2.3).
7. For each row a–d of Design 3.4, a `.tcw/tcw-config.yaml` with that
   `tcw-version` makes `tcw work list` exit 1 with that row's message, and
   `tcw validate` report it as an error naming `.tcw/tcw-config.yaml` and
   `tcw-version`. The same four rows hold for `.tcw/tcw-config.local.yaml`.
   A file at the running version, or at a lower 4.x minor version, is read.
8. `tcw config show` does not print `tcw-version`, and a personal file
   carrying `tcw-version` raises no allowlist problem.
9. After `tcw init --id demo` gives an `id` to a `.tcw/tcw-config.yaml`
   holding only `tcw-version: 4.0.0`, the version is still the first line.
   After `tcw work tags` (or another command that edits the configuration)
   changes `.tcw/tcw-config.yaml`, its `tcw-version` line is unchanged,
   including when it names an older 4.x version than the running one.
10. `file: docs/x.md` in `.tcw/tcw-config.yaml` composes `<root>/docs/x.md`
    into `tcw work stage prompt`, and `file: ../outside.md` is refused for
    leaving `<root>`. A command binding sees `TCW_CONFIG_DIR=<root>`.
11. A key breaking the naming rule (`Work`, `my_key`, `a--b`, `-a`) in
    `.tcw/tcw-config.yaml`, `.tcw/tcw-config.local.yaml` or the user-wide
    file is a configuration problem naming the file and the key path.
12. `when: {not-tags: [bug]}` selects a binding for an item without the tag
    `bug`, and `tcw work lifecycle --json` prints it under `not-tags`;
    `when: {not_tags: [bug]}` is a configuration problem whose message says
    `write 'not-tags'`; `on: x` under `work:` is refused as a key that must
    be text.
13. A 3.x `projects:` connection whose folder holds only a root
    `tcw-config.yaml` is reported by `tcw projects list` and `tcw validate`
    with the Design 4.1 wording, and that project is not read.
13a. Two 4.0 projects connected under `projects:` by a relative path
    (`../app`), and the same pair found through `TCW_PROJECT_<ID>`, are both
    listed by `tcw projects list` with each project's root (not its
    `.tcw/`) as its folder. A connected project whose `.tcw/tcw-config.yaml`
    has `tcw-version: 99.0.0` is reported by `tcw validate` as that
    connection's problem, naming the upgrade, and `tcw init --id demo` in a
    project whose own file has it writes nothing.
14. A 4.0 project that also holds a root `tcw-config.yaml` is read from
    `.tcw/`, and `tcw validate` warns as Design 4.3 says.
14a. From inside `<root>/.tcw/`, `tcw work list` acts on `<root>`.
14b. `tcw validate` warns when `.tcw/tcw-config.local.yaml` is tracked by git.
14c. A command binding declared in `.tcw/tcw-config.local.yaml` sees
     `TCW_CONFIG_DIR=<root>`. `tcw --help` in a 3.x project exits 0.
15. The five version fields read `4.0.0`, and
    `tests/test_plugin_manifests.py` passes.
16. The full suite, run as CI runs it (bare `pytest`), passes on `v4`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 location of both files | 1, 7 |
| 1.2 `.tcw/` without the file | 4 |
| 1.3 paths relative to the root | 3, 10, 13a |
| 1.4 `file:` and `TCW_CONFIG_DIR` | 10, 14c |
| 1.5 `tcw init` and the ignore rule | 1, 2, 14b |
| 2.1 walk outwards from any subfolder | 3 |
| 2.2 nearest `.tcw/` wins, root file or not | 3, 6, 14 |
| 2.3 3.x reached first is refused; `.tcw` itself is not 3.x | 5, 6, 14a |
| 2.4 nothing found | 4 |
| 3.1 field and first line | 1 |
| 3.2 edits never change it | 9 |
| 3.4a every reader, other projects | 13a |
| 3.3 not configuration | 8 |
| 3.4 a–d, both files | 7 |
| 3.5 running version is 4.0.0 | 1, 15 |
| 3.6 one shared check | n/a here: no other `tcw-*.yaml` reader exists until TCW-107 (manifests) and TCW-111 (state files); the plan names the function they call |
| 4.1 every command refuses 3.x | 5, 14c |
| 4.2 a 3.x connection | 13 |
| 4.3 leftover root file | 14 |
| 5.1 every key, three files | 11 |
| 5.2 keys in list entries | 12 |
| 5.3 `not-tags`, JSON output | 12 |
| 5.5 user-wide file | n/a here: recorded on TCW-116 |
| 5.4 project IDs | existing `test_invalid_or_reserved_project_ids` (`tests/test_project_registry.py:53`), unchanged |

## Risks

- **The suite is large and nearly every test writes a root
  `tcw-config.yaml`** (75 test files, 315 lines). Changing them by hand risks
  a test that silently stops testing what it did. The plan gives the tests
  one helper for writing a project's configuration and changes the fixtures
  mechanically, then reads the failures rather than editing assertions to
  pass.
- **Messages naming `tcw migrate` before it exists.** On `v4` only, until
  TCW-116; nothing is released in between.
- **A hand-made personal file now needs a `tcw-version` line.** The message
  gives the exact line to add, so the cost is one line once.
- **`.tcw/.gitignore` instead of the root `.gitignore`.** A project whose
  root `.gitignore` already ignores `/tcw-config.local.yaml` keeps that dead
  line; harmless, and `tcw migrate` (TCW-116) can remove it.

## Notes

The field name `tcw-version` was left to the spec by the design. It follows
the naming rule, cannot be mistaken for the project's own version, and reads
the same in every `tcw-*.yaml` file.
