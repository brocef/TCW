# Spec — Personal configuration: user identity and per-user overrides

## Capability changes

Planned ledger changes. No records are written at this stage.

**Taxonomy, new:**

- Vocabulary `config-layer`: one of the places TCW reads configuration from,
  in a fixed order (built-in, `tcw-config.yaml`, the user-wide file, the local
  file), where a higher layer wins.
- Vocabulary `user-identity`: who the person running a command is, as matched
  against an item's `assignee`.
- Feature `personal-configuration`: untracked, per-person configuration layered
  over the team's `tcw-config.yaml`. Vocabulary: `config-layer`,
  `user-identity`, `work-item/lifecycle-stage`, `work-item/lifecycle-hook`.
  Relates to `configurable-work-lifecycle` and `configure-skill`.

**Capabilities, new** (all `Feature: personal-configuration`):

- `cli/override-the-team-configuration-for-myself`: the two personal files,
  the `inherit` chain, the allowlist of what a person may override, and the
  refusal when a personal file sets a shared key.
- `cli/show-the-effective-configuration`: `tcw config show [--origin]`.
- `work/tell-tcw-who-i-am`: `user.name` in filesystem mode, the Jira
  credentials in Jira mode (both answered through the backend's
  `current_user()`), `list --mine` and `--assign-me`, and the message when no
  identity is set.

**Capabilities, changed:**

- `work/configure-the-work-lifecycle`, `work/configure-procedures`,
  `work/run-a-lifecycle-stage` and `work/run-a-procedure`: each describes
  `builtin: true`, which this slice replaces with `inherit: true`.
  `run-a-lifecycle-stage` and `run-a-procedure` also gain the stderr note when
  personal layers changed the resolved list. TCW-70 decides whether each
  `docs/capabilities/work/` record survives and rewrites it for the 3.0
  `work.stages` shape (epic decision 12); this slice edits only the sentences
  about `builtin`/`inherit` and the personal note in the records as TCW-70
  leaves them, and TCW-73 later owns any change to their command wording.
- `cli/validate-a-node`: warns when `tcw-config.local.yaml` is tracked, and
  reports problems in personal files. (TCW-73 renames the record for the
  "node" to "project" sweep; this slice edits whichever name it has then.)
- `cli/scaffold-the-doc-trees` (`tcw init`): adds `tcw-config.local.yaml` to
  `.gitignore`.

**Not this slice's:** `skills/configure`. Every file under `skills/configure/`,
and the record describing that skill, belong to TCW-75 (epic decision 3),
including the shared/overridable table (Design 12).

**Checked and unchanged:** `cli/point-tcw-at-a-project-i-already-have`
(`TCW_PROJECT_<ID>`). Design 11 keeps that variable as the only way to say
where a project lives on this machine. `work/start-a-work-item` describes
`TCW_WORK_OWNER`, but the `start` verb and its record are removed by TCW-70
(epic decisions 2 and 12), so this slice does not edit it.

## Problem

1. **There is nowhere to put a fact about one person.** TCW reads one
   configuration file per project, `tcw-config.yaml`, which is tracked and
   shared. A person who wants their own instructions for a stage must change
   the team's file, which changes it for everyone, or not change it at all.
2. **Identity is guessed.** The person running a command is found by
   `_local_owner` (`tcw/work/cli.py:1447-1458`): the `--owner` flag, then the
   `TCW_WORK_OWNER` environment variable, then git's `user.email`, then git's
   `user.name`. Git's identity is an email address on most machines and a name
   on others, so the same person can match an item on one machine and not on
   another. The variable's name leaks into a dozen messages that tell a user to
   rerun a command as someone else, for example `tcw/work/cli.py:3154`,
   `tcw/store/base.py:3495`, `tcw/tracker/sync.py:1062` and
   `tcw/serve/__init__.py:1044-1045`.
3. **Configuration is read in many places, each its own way.** Five separate
   readers open `tcw-config.yaml` today, from 14 call sites:
   - `load_config` (`tcw/store/fs.py:1559-1577`), called at `fs.py:252`, `:376`,
     `:1230`, `:2124`, `:3930`, `:4046` and `:4073`. `fs.py:2124` is
     `FsTreeStore._config`, behind about twenty accessors such as
     `fs.py:7354` (the lifecycle policy);
   - `load_yaml(..., unique=True)` called directly by `tcw validate`
     (`tcw/validate.py:110`, `:145`, `:218`);
   - a bare `yaml.safe_load` in `tcw init` (`tcw/cli.py:59`);
   - `_node_config` (`tcw/work/recursion.py:518-524`), for delegation;
   - the project registry's own loader (`tcw/store/project.py:571`, with its
     own duplicate-key loader at `project.py:26-43`, a copy of
     `fs.py:1465-1481`), plus a second read at `project.py:1035`.

   A second layer added to any one of these would be missing from the others,
   so a person's override would apply to some commands and not to others.
4. **`builtin: true` only works one level deep.** A stage's prompt list may
   contain `builtin: true` to mean "TCW's own text here"
   (`tcw/work/resolve.py:208-209`); a stage with no list falls back to it
   (`resolve.py:456`). That is enough for one file over the built-in text, but
   not for a person's file over the team's: there is no way to say "the team's
   list here", only "TCW's text here".
5. **No list of what is safe to change.** No code says which keys are the
   team's agreement (where items live, which gates run) and which are a matter
   of taste (how a stage is worded). Unknown top-level keys are not even
   reported: the only keys checked are those each reader happens to look for
   (for example `fs.py:4076`, `project.py:599`).

## Goals

1. **Four layers, one loader.** Every command that reads the acting project's
   configuration reads it through one function that applies built-in →
   `tcw-config.yaml` → user-wide → local.
2. **One merge rule**: mappings merge key by key, and the four binding lists
   resolve through the `inherit` chain, with every resolved value and list entry
   knowing which layer it came from.
3. **One allowlist** that decides what a personal layer may set, refusing
   everything else by exit 1, naming the file and key.
4. **Visible results**: `tcw config show [--origin]`, a stderr note from
   `stage prompt` and `procedure`, and the layer of a failed `post` hook in
   `advance`'s outcome.
5. **One identity rule per backend**, with no fallback, and every use of
   `TCW_WORK_OWNER` and the git identity fallback gone.
6. **House rules kept**: personal files are never written by TCW, never hold
   secrets, are ignored by git in new projects, and are reported if tracked.

## Non-goals

- **The model and the `work.*` shape.** TCW-69 defines them. This slice changes
  TCW-69's parser only where the ticket says (`builtin` becomes `inherit`) and
  where Notes lists a cross-slice change.
- **Command names, output format and the exit-code table.** TCW-73 owns the
  surface of every command (epic decision 2): it names `tcw config show`,
  `list --mine` and `--assign-me`, fixes the table, and sets the output rules
  (epic decision 10: one identifier per stdout line, details through `--json`,
  warnings in the `warning:` form). This slice implements their behavior
  inside those rules, using TCW-73's codes (1 for a configuration problem, 2
  for a usage mistake). `config show` is in TCW-73's per-command table as a
  command that prints "its text", like `stage prompt`.
- **The Jira backend.** How TCW-71 authenticates, how it answers
  `current_user()`, and how it parses `work.jira` (including the shape of a
  credential variable name) are TCW-71's. This slice decides only which
  credential keys a person may override.
- **The backend interface.** TCW-69 defines its eleven operations (epic
  decision 1), including `current_user()`, which this slice's identity rule
  calls (Design 9). This slice adds no member.
- **Where a project lives on this machine.** It stays `TCW_PROJECT_<ID>`
  (Design 11). No personal-config key for it is added.
- **Display preferences**, or any personal key not on the allowlist. The
  original decision record mentioned display preferences; the ticket dropped
  them.
- **A `--json` form of `config show`**, and any command that writes a personal
  file. Personal files are edited by hand.
- **User guides and the configure skill** (TCW-75), **every other skill and
  prompt** (TCW-74), and **the migration guide** (TCW-76). The ticket puts the
  shared/overridable table in the configure skill's references; that folder is
  TCW-75's (epic decision 3), so TCW-75 writes the table and this slice
  supplies the allowlist constant it is checked against (Design 12).
- **Validating the shape of `taxonomy`, `capabilities` and `connected-projects`**
  (`projects` after TCW-73's rename) in `tcw-config.yaml`. Their parsers stay where they are; this slice only
  decides whether a personal layer may set them (it may not).

## Design

The loader is a new top-level module, `tcw/config.py`, because all three axes
read configuration, as `tcw/exit.py` is top-level for the same reason. It
depends on nothing in `tcw/work/` except TCW-69's `parse_work_config`, which it
calls on the merged result.

Four terms used below:

- A **layer** is one source of configuration. Its **name** is `built-in`,
  `project` (`tcw-config.yaml`), `user` (the user-wide file) or `local`
  (`tcw-config.local.yaml`). `user` and `local` are the **personal layers**.
- The **acting project** is the project whose root the command was run in: the
  nearest folder upwards holding a `tcw-config.yaml` file, as `find_node_root`
  finds it today (`tcw/store/fs.py:283-292`).
- The **effective configuration** is the merged result.
- An **origin** is the layer a value or list entry came from, and the file
  that layer was read from (none for `built-in`).

### 1. Where the layers are

1. `built-in` is not a file. It is the defaults TCW-69 already defines (for
   example `backend: filesystem`, `hooks.timeout: 300`), plus one built-in
   binding per binding list described in Design 3.3.
2. `project` is `<acting project root>/tcw-config.yaml`. It must exist; without
   it there is no acting project, as today.
3. `user` is `$XDG_CONFIG_HOME/tcw/config.yaml` when `XDG_CONFIG_HOME` is set to
   an absolute path, otherwise `~/.config/tcw/config.yaml`.
   - **[Decision]** A relative `XDG_CONFIG_HOME` is ignored, as the XDG base
     directory specification says, and the home-directory path is used.
     (TCW's one existing XDG reader, `tcw/store/checkouts.py:67`, does not
     check this; it is left alone.)
   - With no `XDG_CONFIG_HOME` and no home directory (Python's `Path.home()`
     raises), the user layer is skipped without a message.
4. `local` is `<acting project root>/tcw-config.local.yaml`. A local file in a
   folder with no `tcw-config.yaml` is never read.
5. A personal file that does not exist is an empty layer. An empty file, or one
   holding only `null`, is also empty.
6. `TCW_NO_PERSONAL_CONFIG=1` skips both personal layers: neither file is
   opened, so a broken personal file cannot fail a command. Unset or empty
   means the layers are read. **[Decision]** Any other value is a configuration
   error (exit 1) naming the variable, so `TCW_NO_PERSONAL_CONFIG=true` cannot
   silently do nothing.
7. **Personal layers apply only to the acting project.** Any other project
   that a command reads (a parent, child or upstream in the registry, a
   delegation target, the project of an item named by a full slug) is read
   from its `tcw-config.yaml` alone. Its own `tcw-config.local.yaml` is never
   opened, and the user-wide file is not applied to it.

### 2. One loader

1. `load_config(project_root, *, personal=True) -> Config` reads the layers,
   checks them (Design 4 and 5), merges them (Design 3) and returns:
   - `values`: the effective configuration as a plain mapping, including the
     built-in chain entries, each written `{builtin: true}` (Design 3.4);
   - `origins`: the origin of every scalar, every list and every list entry,
     keyed by key path. A key path is a tuple of keys, with a list index as
     an `int`: `("work", "stages", "spec", "prompt", 2)`. This is the form of
     TCW-69's `Problem.key_path` and of the `origins` argument of
     `parse_work_config` (review decision R8);
   - `work`: TCW-69's parsed `WorkConfig`, from
     `parse_work_config(values, origins)`;
   - `problems`: every problem found, each naming the file and key it came
     from (Design 5);
   - `skipped`: personal values that were read but not applied (Design 4.6);
   - `refused`: personal values that were read but refused as shared keys
     (Design 4.4), kept so that `config show --origin` can list them.

   `personal=False` reads `built-in` and `project` only. It is what TCW-70's
   `open_project` and the opening of a delegation target (TCW-70's
   `delegate`, review decision R5) use for another project (Design 1.7).
2. **Every reader of a project's whole configuration goes through this
   function**, and the YAML read itself exists once. The loader module also
   offers `read_project_file(project_root) -> (mapping, problems)`: the single
   read of one `tcw-config.yaml`, with the duplicate-key refusal, and nothing
   else (no layers, no allowlist, no `parse_work_config`). The two copies of
   the duplicate-key loader (`fs.py:1465-1481`, `project.py:26-43`) become
   this one function. Who uses which:
   - **`load_config`**: every command that acts on the acting project's
     configuration (Design 2.4), and TCW-70's `open_backend`, `open_project`
     and the delegation target (Design 2.5).
   - **`read_project_file`**, keeping today's tolerance: readers that look
     only at the shared graph keys (`id`, `connected-projects`, `projects`
     after TCW-73's rename, `work.repository`) and must still answer for a
     project graph that cannot be fully loaded. These are the project
     registry (`tcw/store/project.py:571` and `:1035`; it already tolerates
     problems in an upstream project's connections, `project.py:595-597`),
     and `provision`'s two readers, `declared_repository` and
     `declared_connected_projects` (`tcw/store/fs.py:4034`, `:4056`, called
     from `tcw/cli.py:136` and `:228`), which deliberately skip the refusing
     loader (`fs.py:1567-1570`). They never read a personal file and never
     run `parse_work_config`, so a project still on a 2.x `work.lifecycle`, or
     a broken personal file, does not stop `provision` or a walk of the
     project graph. Each keeps its own rule for which of its problems it
     reports.

   The other readers in Problem 3 are either deleted with the 2.x code they
   serve (TCW-70 removes the 2.x work store, which owns most of them) or
   changed to call one of these two functions.
3. The result is computed once per command. A command that loads config and
   gets problems exits 1 before doing anything else, except
   `tcw config show --origin` (Design 8) and `tcw validate` (Design 5.5).
   `load_config` itself returns its problems rather than raising, so those two
   can print them all. **[Decision]** The CLI turns a non-empty `problems` into
   one exception, `ConfigError`, carrying exit 1, which this slice adds to
   `tcw/errors.py` beside TCW-69's classes (epic decision 8), so the
   taxonomy and capabilities commands stop on it the same way.
4. Commands that **do not** call `load_config` for the acting project: `tcw
   --version`, `--help` on any command, `tcw init`, which reads and edits
   only `tcw-config.yaml` (Design 10), and `tcw provision`, which reads only
   the shared graph keys through `read_project_file` (Design 2.2). Every
   other command loads it.
5. **Where this meets TCW-70's code.** TCW-70's `open_backend(project_root)`
   reads `tcw-config.yaml` through `parse_work_config` itself and raises
   `BackendError` for a configuration problem (TCW-70 Design 2.1). This slice
   changes it to:
   - call `load_config(project_root)` once and raise `ConfigError` (exit 1,
     the same code) when `problems` is not empty;
   - build `FsWorkBackend` with `user_name` set to the effective `user.name`,
     or none when it is not set (Design 9.2).

   `open_project` and the delegation target call
   `load_config(root, personal=False)` instead, so their backend is built
   with no `user_name` even when the person has one.

### 3. Merging, and the `inherit` chain

1. **Mappings merge key by key**, from `built-in` upwards. When both the lower
   result and the higher layer hold a mapping at a key, the two merge; when the
   higher layer holds anything else at that key, it replaces the lower value.
2. **The four chain lists** are each stage's `prompt`, `pre` and `post`
   (`work.stages.<stage>.<list>`) and each procedure's list
   (`work.procedures.<id>`). For each one, layer by layer from `built-in`
   upwards:
   - a layer that does not set the key keeps what the layer below resolved;
   - a layer that sets the key replaces what the layer below resolved, unless
     its list contains an `inherit: true` entry, which is replaced, in place,
     by the list the layer below resolved.

   ```yaml
   prompt:
     - file: docs/lifecycle/house-rules.md   # before the inherited text
     - inherit: true                         # everything from the layer below
     - file: docs/lifecycle/after.md         # after it
   ```

   Inherited entries keep their own `when:` conditions and their own origins.
3. **The built-in lists.** For a stage whose `prompt` column is yes (TCW-69
   Design 3), the built-in `prompt` list is one entry: the packaged prompt
   `tcw/work/prompts/<stage>.md`. For each procedure id, the built-in list is
   one entry: the packaged procedure text. Every other built-in list is empty,
   including every `pre` and `post` list: TCW-69's built-in gates are not
   bindings, and they run before configured `pre` bindings whatever the lists
   say. So at the `project` layer, `inherit: true` in a `prompt` list is the
   built-in prompt, and in a `pre` list it adds nothing.
4. **Built-in entries are internal** (review decision R8). In `values` a
   built-in entry is the mapping `{builtin: true}`, the form TCW-69's parser
   already accepts, and its origin is `built-in`. Only the loader inserts it.
   **[Decision]** Writing `builtin:` in any file is an error, found in that
   file before the layers are merged, that says to use `inherit: true` and
   names TCW-69's migration guide (`docs/migration-guide-2.8-to-3.0.0.md`).
   So the parser never has to tell a file's entry from a built-in one: by the
   time it runs, every `builtin` entry came from the built-in layer.
   `config show` prints a built-in entry as `- builtin: true  # <packaged
   file>` (Design 8), which parses back to the same mapping, but a file that
   copies that line is refused like any other `builtin:`.
5. **The packaged text reaches a prompt only through the list.** `stage
   prompt` and `procedure` compose exactly the resolved list. No code adds
   the packaged text on its own, and the 2.x fallback that treats an empty
   list as `[builtin]` (`tcw/work/resolve.py:456`,
   `or [Binding(kind="builtin")]`) must not survive into 3.0: a stage the
   person sets to `[]` gets no packaged text. A project that wants the
   packaged text and its own writes `inherit: true` in its list.
6. **The `inherit` entry's rules.** Each is an error:
   - `inherit:` with any value other than `true` (there is no
     `inherit: false`; leaving the entry out means replace);
   - `inherit` together with `when:` or any other key in the same entry;
   - more than one `inherit` entry in one list;
   - `inherit` in any list other than the four chain lists.
7. **[Decision] An empty list is allowed in every chain list** and means
   "nothing from here down". TCW 2.8 refuses an empty `prompt` or `procedures`
   list (`tcw/store/base.py:2664-2690`, `:3084-3089`) because, after parsing,
   it cannot be told apart from an absent key, which falls back to the
   built-in text. The chain is decided before parsing, where "set to `[]`" and
   "not set" are different, so the reason no longer holds. `[{blob: ""}]` still
   works. This changes TCW-69's parser, whose plan still keeps the 2.8
   refusal for procedures ("an empty list is not an opt-out", TCW-69
   plan.md:184); the change is listed in Notes.
8. **[Decision] Duplicates** (same kind, value and `when:`) are refused by the
   loader within one layer's list as written, before merging: one problem
   naming that file and the list's key path. TCW-69's parser no longer refuses
   duplicates (review decision R8; TCW-69 plan.md:165-167), so the merged
   list is never checked for them. If a person's list and the team's both
   name the same file and the person inherits, the file appears twice, and
   `config show --origin` shows both entries with their layers.
9. **Every other list is replaced whole** by a layer that sets it. Among
   overridable keys none is a list, so this matters only for `project` over
   `built-in` (for example `work.tags`).
10. **[Decision] `null`** in a personal layer is an error. A personal layer
   cannot remove a value, only replace it, so a `null` there has no meaning to
   give it. `null` in `tcw-config.yaml` keeps whatever meaning that key's
   parser gives it today.

### 4. What a personal layer may set

1. **The allowlist.** One constant, `tcw.config.PERSONAL_KEYS`, lists the key
   paths a personal layer may set. `*` stands for exactly one key. Anything
   not on it is **shared**. A key added to TCW later is shared unless it is
   added here. It is a public name because TCW-75's documentation test
   imports it to check the shared/overridable table (Design 12).

   | Key path | Layers |
   | --- | --- |
   | `user.name` | personal only |
   | `work.stages.*.prompt` | all |
   | `work.stages.*.post` | all |
   | `work.procedures.*` | all |
   | `work.jira.credentials.email-env` | all |
   | `work.jira.credentials.token-env` | all |

   - **[Decision, owner 2026-10-01] A personal `post` list may replace the
     team's `post` hooks**, as the ticket asks: like any chain list, it
     replaces what the layer below resolved unless it contains
     `inherit: true` (Design 3.2). `pre` is not on this list, so the team's
     gates stay shared.
   - The two credential keys are the ones TCW-71's `work.jira` parser defines
     (TCW-71 Design 1), the same names as TCW 2.8's
     (`tcw/store/base.py:1620-1621`). They are listed by name rather than as
     `credentials.*`, so a key TCW-71 adds to `credentials` later is shared
     until it is added here.
   - **[Decision] Credential variable names inside a connected-project entry
     are shared**, like the rest of that entry. This reverses this spec's
     earlier draft, to agree with TCW-71. When a project delegates into a Jira
     target, TCW-71 reads the target's own `tcw-config.yaml` (with no personal
     layers) and falls back to the delegator's connected-project `jira` block
     only when it cannot, and it requires the site and the credential names to
     come from the same file, so that a token is never sent to a site another
     file named (TCW-71 Design 8, its decision on delegation settings). A
     personal override there would either do nothing (the target's file was
     read) or break that rule (the site from the team's file, the names from a
     personal one). A person whose shell uses other variable names exports the
     names the target's file gives.
   - The acting project's own credential names may come from a personal file
     while `work.jira.site` comes from `tcw-config.yaml`. That does not break
     TCW-71's same-file rule, which is about delegation: here the person
     chooses which of their own tokens is sent to the team's site.
2. **Shared**, among others: `id`, `work.backend`, `work.path`,
   `work.repository`, `work.jira.site`, `work.jira.project`, and every other
   `work.jira` key outside the two credential names (`fields`, `priorities`,
   `issue-type`, `inbox-query`, `timeout`), every stage's `enabled`, `status`
   and `pre`, `work.tags`, `work.documentation`, `taxonomy.*` and
   `capabilities.*` (including `extends`), and every connected-project entry
   (`connected-projects`, `projects` after TCW-73's rename), including its
   `jira` block.
3. **[Decision] `work.hooks.timeout` and `work.hooks.output-cap` are shared.**
   They bound the team's `pre` gates as well as `post` hooks and `generate`
   prompts, so a personal value could change whether a shared gate passes (a
   shorter timeout fails a gate that would have passed; a longer one lets a
   hung gate hold the command). A person's own `post` hooks and `generate`
   bindings run under the team's limits.
4. **How the check walks a personal file.** Each key path in the file is
   compared with the allowlist. A mapping on the way to an allowlisted path
   (`work`, `work.stages`, `work.stages.spec`) is walked into and must be a
   mapping; any other value there, and any key that leads to no allowlisted
   path, is a problem: "`<file>`: `<key path>` is shared and cannot be set in a
   personal file". This covers unknown keys too. A refused value is not
   merged; it is recorded in `refused` with its file and key path.
5. **`user.*` is personal only.** `user` in `tcw-config.yaml` is a problem:
   "`user.*` is personal; set it in `<user-wide path>` or
   `tcw-config.local.yaml`". `user` takes only `name`, a string that is not
   blank and has no leading or trailing whitespace (it is matched exactly,
   Design 9). Another key under `user` is a problem.
6. **[Decision] Personal Jira credential names are skipped outside Jira mode.**
   TCW-69 refuses a `work.jira` block when `backend` is not `jira`. A user-wide
   file is read in every project, of either backend, so a person who sets their
   Jira credential names there would otherwise break every filesystem-mode
   project. A personal `work.jira.credentials` value is therefore applied only
   when the effective `work.backend` is `jira`; otherwise it is recorded in
   `skipped` and listed by `config show --origin`. TCW-69's rule still applies
   to `tcw-config.yaml`.
7. **Credential variable names are names.** Their shape is TCW-71's to check
   (`^[A-Z_][A-Z0-9_]*$`, TCW-71 Design 1), on the merged mapping, so a name
   from a personal file is checked exactly like one from `tcw-config.yaml` and
   the problem is reported against the file it came from (Design 5.2). This
   slice adds one requirement on that message, which TCW-71's parser must meet
   (Notes): it names the key and does **not** print the value, so a token
   pasted by mistake into a personal file is not echoed to a terminal or a
   log.

### 5. Problems and exit codes

1. Every problem names the file and the key path: `<file>: <key path>:
   <message>`, with the key path written with dots and list indexes in
   brackets (`work.stages.spec.prompt[2]`).
2. **Mapping a parser problem back to a file** (review decision R8). The
   loader calls `parse_work_config(values, origins)`, which copies each
   origin onto the `Binding` built at that key path and returns each problem
   as a `Problem(key_path, message)`; a problem that involves two keys (for
   example two stages sharing one `status`) names the first. The loader then
   picks the problem's file:
   - the origin recorded for the problem's key path, if there is one;
   - otherwise the origin of the longest prefix of that key path that has
     one (a problem about a list entry's `when` gets the entry's origin);
   - otherwise, for a key path that names a mapping several layers wrote
     into, the highest layer that wrote any key under it;
   - otherwise `tcw-config.yaml`.

   So a bad binding in a personal file is reported against that file, not
   against `tcw-config.yaml`, and a built-in entry can never be blamed on a
   file.
3. Problems in any layer (unreadable YAML, a duplicate key, a shared key, a bad
   binding, a `TCW_NO_PERSONAL_CONFIG` value) make every command that loads
   config exit 1, writing the problems to stderr and nothing to stdout.
4. The exceptions are `tcw config show --origin` (Design 8.3) and
   `tcw validate`.
5. `tcw validate` reports each problem as an error-level `Finding` (TCW-73's
   `Finding(severity, where, message)`, review decision R14) whose `where` is
   the file and whose message starts with the key path, so it prints on
   stdout, in TCW-73's finding line form (TCW-73 Design 6.3), as
   `error: <file>: <key path>: <message>`, and exits 1. A project's
   continuous-integration run is not affected by a developer's personal files,
   because it has none (or sets `TCW_NO_PERSONAL_CONFIG=1`).

### 6. Relative paths, and commands from personal layers

1. **`file:` bindings resolve from the declaring file's folder**, and must stay
   inside it. Today a `file:` path is resolved from the project root and
   refused if it leaves it, symlinks followed (`_confined`,
   `tcw/work/resolve.py:123-137`). **[Decision]** The same check applies with
   the declaring file's folder as the root: the project root for `project` and
   `local`, and `~/.config/tcw/` (or `$XDG_CONFIG_HOME/tcw/`) for `user`. A
   person keeps their own prompt files under that folder. **[Decision]** The
   confinement is checked when the configuration loads, so a `file:` that
   leaves its folder is a problem from `load_config` (exit 1 for every
   command, Design 5.3); whether the file exists is still checked when the
   prompt is composed, as today.
2. **`generate:` and `command:` values are command lines, not paths.** TCW
   cannot tell which words in them are paths, so it does not rewrite them.
   They run with the project root as the working directory, as today
   (`tcw/work/generate.py:107-111`) and as epic decision 11 fixes for 3.0,
   whichever layer declared them. **[Decision]** Each one runs with
   `TCW_CONFIG_DIR` set to the declaring file's folder (the project root for
   `project`), so a personal hook can reach its own script as
   `"$TCW_CONFIG_DIR/scripts/x.sh"`. This adds one variable to the hook
   environment TCW-69 lists (Design 6, step 5: `TCW_SLUG`, which is the full
   slug `<project>/<folder>` per epic decision 11, `TCW_STAGE`,
   `TCW_FROM_STAGE`, `TCW_ITEM_PATH`, `TCW_PROJECT_ROOT`, and `TCW_FORCED` and
   `TCW_REASON` when forced), and to the `generate` binding environment
   TCW-69 Design 8 gives (review decision R13; this slice does not change
   what a `generate` binding receives on stdin). It is new in 3.0 and has no 2.x counterpart, so
   TCW-76's variable mapping lists it as new.
3. The trust model is unchanged: configuration is the user's own file, and
   hooks run as the user (`tcw/work/hooks.py:11-14`). A personal file is, if
   anything, more the user's own than the team's file.

### 7. Origins in results

1. **Bindings carry their origin.** TCW-69's `Binding(kind, value, when,
   origin=None)` (TCW-69 plan, Task 4, review decision R8) already has the
   field; this slice fills it, through `parse_work_config`'s `origins`
   argument (Design 5.2), with the layer name and file. The `file:` root
   (Design 6.1) and `TCW_CONFIG_DIR` (Design 6.2) are read from it.
2. **`advance` names the layer of a failed `post` hook.** TCW-69's `Outcome`
   (`code`, `stage`, `messages`, `overridden`) gains `post_failures`, a tuple of
   `(binding, origin, detail)`, one per failed `post` binding. The message for
   each says which hook failed, why, and the file it came from, for example:
   "post hook `./notify.sh` from /home/a/.config/tcw/config.yaml failed (exit
   1)". The exit code is TCW-69's 6. `pre` gates need no origin, because they
   can only come from `tcw-config.yaml`. These messages go to stderr; stdout
   stays the reported stage, as TCW-73's table says for `advance`.
3. **`stage prompt` and `procedure` note personal changes.** When either
   personal layer sets the list being resolved (`work.stages.<stage>.prompt`,
   or `work.procedures.<id>`), the command writes one line to stderr naming
   the files: "this prompt was changed by personal configuration:
   tcw-config.local.yaml". stdout is the resolved text, as without the note.
   **[Decision]** `procedure` gets the note too, because a procedure list
   resolves through the same chain; the ticket names only `stage prompt`.

### 8. `tcw config show [--origin]`

1. **Plain.** Prints the effective configuration (`values`) to stdout as YAML,
   with every key, including built-in defaults and the built-in chain
   entries, each printed `- builtin: true  # <packaged file>` (Design 3.4).
   **[Decision] Key order** is the order the merge produces: the merge walks
   the layers from `built-in` upwards and a key keeps the position where the
   lowest layer that has it put it, so built-in keys come first, in the order
   `tcw/config.py`'s built-in mapping lists them (TCW-69 Design 8's key order
   under `work`, stages in stage-table order), and keys no lower layer has
   follow in file order. The order is fixed so that the output is the same on
   every run; nothing parses it.
   Problems: exit 1, nothing on stdout. This is the "its text" row of TCW-73's
   per-command stdout table, and the command adds its row to TCW-73's contract
   test (`tests/test_cli_contract.py`), which fails for a command registered
   without one.
2. **`--origin`.** Prints the same YAML with a comment after each scalar and
   each list entry naming its origin: `# built-in` (with the packaged file
   for a built-in entry), `# project`, `# user: <path>` or `# local: <path>`.
   The output parses as YAML to exactly `values`, because every addition is a
   comment. After the configuration, a comment block lists each `skipped`
   value (Design 4.6) and each `refused` value (Design 4.4), one comment line
   each, giving its file, key path, value and reason, for example
   `# refused: id: other (shared key, tcw-config.local.yaml)`.
3. **`--origin` still runs with problems.** It prints what it can and exits 1,
   with the problems on stderr:
   - a shared key set in a personal file is not merged and appears only in
     the trailing comment block, marked `# refused:` (Design 8.2), so the
     output never holds the same key twice;
   - a personal file that cannot be read at all (bad YAML) is named on stderr
     and contributes nothing.

   This is how a person finds the line that is stopping every other command.
   A broken `tcw-config.yaml` still makes `--origin` exit 1 with nothing on
   stdout, because nothing above it can be merged without it.

### 9. Identity

1. **Filesystem mode** uses `user.name` from the effective configuration (so
   only from a personal layer, Design 4.5). It is compared with an item's
   `assignee` exactly: same characters, same case.
2. **The backend answers, through `current_user()`.** Identity is TCW-69's
   eleventh backend operation, `current_user() -> str | None` (epic decisions
   1 and 17; TCW-69 Design 5, "the three reads"). It returns the value the
   backend compares `Query.assignee` with, or `None` when no identity is
   configured.
   **It never raises for a missing identity** (review decision R3): `None` is
   the answer in every backend, and the CLI turns it into its own message.
   - The filesystem backend is constructed with `user.name` from the effective
     configuration (Design 2.5) and returns it, or `None` when it is not set.
     This replaces TCW-70's rule that it raises `BackendError` when built with
     no `user_name` (TCW-70 Design 3.3, item 11), listed in Notes.
   - The Jira backend answers with the account ID its credentials belong to
     (TCW-71 Design 10), and `None` when its credential variables are unset
     (R3). An error talking to Jira (credentials rejected, Jira unreachable)
     is not "no identity"; TCW-71 reports it as for any other operation.
   - **[Decision]** When `current_user()` returns `None`, the command raises
     `ConfigError` (exit 1, Design 2.3) with one message: "no identity is
     configured: set `user.name` in `<user-wide path>` or in
     `tcw-config.local.yaml`, or, in a Jira project, set the environment
     variables named by `work.jira.credentials`". It names both remedies, so
     the CLI never branches on the backend kind.

   A non-filesystem store can answer "who is calling" (Jira's own
   current-user lookup), so this passes the litmus test.
3. **Commands that use it:**
   - `list --mine` is `Query(assignee=backend.current_user())`;
   - `--assign-me` on `new` and `edit` sets `assignee` to
     `backend.current_user()` through `Changes`;
   - `--mine` together with `--assignee`, and `--assign-me` together with
     `--assignee`, are usage errors (exit 2).
   - **Identity is always the acting project's.** `current_user()` is asked
     of the acting project's backend, the only one built with personal
     layers (Design 1.7, 2.5).
   - **[Decision] `--assign-me` with `new --project <id>` naming another
     project is a usage error (exit 2)**, saying the target project assigns
     its own items. Delegation is TCW-70's `delegate(project_id, title,
     request, priority)`, which takes no assignee (review decision R5), and
     the acting project's identity may not even be in the target's form (a
     filesystem name sent to a Jira target that expects an account ID,
     TCW-71 Design 10). `edit` of an item in another project is already
     refused (exit 3) by TCW-73's rule that another project's item is written
     only through `new --project` and `edit --blocks` (TCW-73 Design 3.4), so
     `edit <other project's slug> --assign-me` needs no rule of its own.

   The CLI hands the value to the backend and never compares it with
   `Item.assignee` itself. TCW-69 Design 5.4 requires both to be in the same
   form (in Jira mode, both are account IDs, TCW-71), but the backend stays the
   one place that knows that form. `list --mine` prints what `list` prints, one full
   slug per line (TCW-73). `current_user()` is called only by these, so no
   other command ever needs an identity.
4. **[Decision] A comment records no author in filesystem mode.** TCW-70
   leaves this question here (its Notes). The filesystem backend's
   `read_comments` returns `author=None`, and `comment` writes only the text,
   as TCW-70 specifies. Recording `user.name` would make every comment,
   including the trace note `advance` writes with each move, depend on an
   optional personal setting; git already records who committed the comment
   file; and Jira records the author itself.
5. **No fallback.** `TCW_WORK_OWNER`, `--owner`, and git's `user.name` and
   `user.email` are never read for identity. Every use in code 3.0 keeps is
   deleted, along with every message that tells a user to set or use them.
   Today these are `_local_owner` and its callers (`tcw/work/cli.py:1447-1458`,
   `:1620-1624`, `:2666`, `:3154`, `:3399`, `:3647`, `:3760-3764`, `:4015`,
   `:4922`, `:4990`), `tcw/store/base.py:3495`, `tcw/tracker/sync.py:1062` and
   `tcw/serve/__init__.py:1040-1046`. Most go with the 2.x code TCW-70
   deletes, since it removes every command the 2.x store built (claims,
   `start`, the tracker verbs, and the 2.x web routes; epic decision 2);
   whatever is still there when this slice is implemented is removed by it.
   The docstring of `override_variable` (`tcw/store/project.py:69-71`), which
   cites `TCW_WORK_OWNER` as the precedent for `TCW_PROJECT_<ID>`, is
   reworded.
6. **[Decision] Nothing for the documentation allowance list.** Epic decision
   6 gives `tests/test_documented_cli_surface.py` a temporary list of removed
   commands and keys that documents may still name. The only flag this rule
   removes, `--owner`, belongs to `start` (`tcw/work/cli.py:4990`), which
   TCW-70 removes and lists itself. What this slice removes is a variable
   (`TCW_WORK_OWNER`) and an input form (`builtin:`), which today's test does
   not parse. If the list has grown to cover keys and variables by the time
   this slice is implemented, it adds `TCW_WORK_OWNER` and `builtin: true`
   there, each with the guard that checks the entry really is gone. The
   documents that still name them (`skills/work/references/commands.md`,
   `docs/guide/work.md`, `docs/guide/jira.md`) are rewritten by TCW-74 and
   TCW-75, whose own check (TCW-75 criterion 2) refuses both names.

### 10. Writing configuration, and keeping the local file untracked

1. **Commands that edit configuration write only `tcw-config.yaml`**, and edit
   it from its own text, never from the effective configuration, so a personal
   value is never copied into the team's file. Today's writers already work on
   the file's own text (`config_edit`, used by `_write_node_config`,
   `tcw/store/fs.py:2183-2210`); 3.0's writers (`tags add|rm`, the `extends`
   subcommands, `init`) keep that. No command writes a personal file.
2. **`tcw init`** adds the line `/tcw-config.local.yaml` to the `.gitignore` in
   the folder holding `tcw-config.yaml`, unless that file already has a line
   that is exactly `/tcw-config.local.yaml` or `tcw-config.local.yaml`.
   **[Decision]** Either spelling counts as present, so a person who wrote the
   rule without the `/` does not get a second one; today's `ensure_ignored`
   (`tcw/store/fs.py:982-994`) compares whole lines exactly and would add it,
   so `init` checks both spellings before calling it. The leading `/` limits
   the rule to that folder. It writes the file and stages nothing: TCW never
   changes git state (review decision R4). Which `init` form runs this
   (`tcw init`, or TCW-73's `tcw init <axis>` for the work axis) is TCW-73's
   surface; the line is written whenever `init` creates or finds
   `tcw-config.yaml`.
   - **Outside a repository** (TCW-73 Design 8.3 makes `init` work there)
     it writes no `.gitignore` and prints exactly this notice on stderr,
     exit 0: `tcw init: not inside a repository, so no ignore rule was
     written; keep tcw-config.local.yaml out of version control yourself`.
     Whether the folder is inside a repository is found by the read that
     finds the repository root, which review decision R4 allows.
   - **[Decision] Fixed wording, no git words.** Both this notice and the
     warning in 10.3 avoid every word on TCW-73's git word list (TCW-73
     Design 9.1) apart from the filename `.gitignore`, which that test
     already exempts, so neither needs an exemption of its own.
3. **`tcw validate`** warns (exit 0 if nothing else is wrong) when
   `tcw-config.local.yaml` is tracked in the acting project. It finds out by
   reading only: `git --no-optional-locks status --porcelain --ignored --
   tcw-config.local.yaml`, the same read-only status command review decision
   R4 allows for the uncommitted-changes check, limited to that one file. The
   file is tracked when it exists and that command reports it neither as
   untracked (`??`) nor as ignored (`!!`). The warning is a `warning`-level
   `Finding` ("a tracked personal file", TCW-73 Design 6.2; review decision
   R14), printed as a finding line on stdout (TCW-73 Design 6.3) with exactly
   this text: `warning: tcw-config.local.yaml: tracked; personal
   configuration should stay out of version control (stop tracking it and
   list it in .gitignore)`.
   Outside a repository there is nothing to check and nothing is printed.
4. **Secrets** never go in configuration: configuration names environment
   variables (TCW-71's parser enforces the shape of those names, Design 4.7).

### 11. Where a project lives on this machine (the ticket's open question)

**[Decision] `TCW_PROJECT_<ID>` stays, and it stays the only way.** Personal
configuration gets no key for a project's location. Reasons:

1. **It is a fact about an environment, not about one project.** The variable
   exists so that one setting serves every session in an environment (a cloud
   session's base folder, a CI runner) whichever projects that session holds
   (`tcw/store/project.py:703-710`, and the capability record
   `cli/point-tcw-at-a-project-i-already-have`). Those are exactly the places
   where personal files are absent or skipped with `TCW_NO_PERSONAL_CONFIG=1`.
2. **Locations are read while walking several projects.** Personal layers
   apply only to the acting project (Design 1.7). A location in the acting
   project's local file would make the project graph depend on which project
   the command was run from; one in the user-wide file would be a second way
   of stating the same fact, needing a rule for which wins and adding a new way
   for an override to "do nothing".
3. **It costs nothing.** The variable already works and is documented. A person
   who wants a permanent setting exports it in their shell profile.

`TCW_PROJECT_<ID>` is read whether or not `TCW_NO_PERSONAL_CONFIG` is set: it
is not configuration. A declared project that is not on this machine is exit
5, and delegation into it exit 3 (epic decision 4); personal files cannot
change either, because they hold no location.

### 12. Documentation this slice writes

- The release-note and changelog entry files under `upcoming/`, named by this
  item's folder, as the project's documentation entries require. **The
  release-notes entry starts with its first `##` heading**, with no text
  before it: only TCW-75's entry may carry the 3.0.0 introduction (epic
  decision 15).
- The capability and taxonomy records in Capability changes.
- `tcw.config.PERSONAL_KEYS` (Design 4.1), as the single source the
  documentation is checked against.

**Not written here:** the configure skill, including
`skills/configure/references/personal.md` with **the shared/overridable
table** the ticket makes canonical, and the router line in
`skills/configure/SKILL.md`. Every file under `skills/configure/` is TCW-75's
(epic decision 3). TCW-75 writes the table and its criterion 7 checks that the
overridable rows are exactly `PERSONAL_KEYS`, so the table cannot drift from
the code. This slice's ticket said to write the table; the epic decision moves
it. Other skills that mention identity or `builtin` are TCW-74's. User guides
(`docs/guide/`) are TCW-75's; the migration steps (`builtin: true` to
`inherit: true`, `TCW_WORK_OWNER` to `user.name`, ignoring the local file in
existing projects, the new `TCW_CONFIG_DIR`) are TCW-76's.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| Loading and merging layers, the allowlist, `config show` | **Not a store operation.** Configuration is files in the repository and the user's home in both backends; nothing here touches a work store. |
| `current_user()` | **Backend interface** (TCW-69's eleventh operation; this slice calls it and adds nothing). Jira answers from the authenticated account; the filesystem backend from `user.name`. A third store would answer from its own login. |
| `list --mine`, `--assign-me` | **Model**, over `current_user()`, `Query` and `Changes`. The CLI never compares the identity with `Item.assignee` itself, so a store whose assignee is shown in a different form from its user identifier still works. |
| Comment author | **Backend interface**, through `read_comments`' `Comment.author`: `None` in filesystem mode (Design 9.4), the ticket comment's author in Jira. |
| `post` hook origin | **Model**: a field on `advance`'s outcome. |
| `.gitignore` line, tracked-file warning | **Filesystem-local**, about the configuration file rather than the work store, and the same in both backends. |

**Harness compatibility.** Every rule here is enforced by the `tcw` CLI, so
Claude and Codex users get the same behavior. Skills only document it.

## Acceptance criteria

Unless a criterion names a command, it is checked by pytest tests in
`tests/config/` that call `load_config` against temporary folders, with
`XDG_CONFIG_HOME` and `HOME` pointed into the test's temporary folder.
Criteria naming a command run it as a subprocess or through its `main`
function, with a temporary project.

1. **Finding the layers.**
   - With `XDG_CONFIG_HOME=/abs/x`, the user layer is `/abs/x/tcw/config.yaml`.
   - With it unset, it is `$HOME/.config/tcw/config.yaml`.
   - With `XDG_CONFIG_HOME=rel/x`, it is `$HOME/.config/tcw/config.yaml`.
   - With `XDG_CONFIG_HOME` and `HOME` both unset and `Path.home()` patched to
     raise, the user layer is skipped and there are no problems.
   - A `tcw-config.local.yaml` in the parent folder of the acting project is
     not read.
2. **Skipping personal layers.** With `TCW_NO_PERSONAL_CONFIG=1` and both
   personal files holding invalid YAML, `load_config` has no problems and
   `origins` holds only `built-in` and `project`. With the variable set to
   `true`, there is one problem naming `TCW_NO_PERSONAL_CONFIG`.
3. **Mappings merge.** With `tcw-config.yaml` setting
   `work.stages.spec.pre: [{command: a}]` and a local file setting
   `work.stages.spec.prompt: [{blob: x}]`, the effective `work.stages.spec` has
   both, `pre[0]`'s origin is `project` and `prompt[0]`'s is `local`.
4. **The chain.** For `work.stages.spec.prompt`, writing each layer's list as
   given (`-` means the layer does not set the key; `B` is the built-in entry):

   | project | user | local | resolved |
   | --- | --- | --- | --- |
   | – | – | – | `[B]` |
   | `[a]` | – | – | `[a]` |
   | `[inherit, a]` | – | – | `[B, a]` |
   | `[a]` | `[b, inherit]` | – | `[b, a]` |
   | `[a]` | `[b, inherit]` | `[inherit, c]` | `[b, a, c]` |
   | `[a]` | `[b, inherit]` | `[d]` | `[d]` |
   | `[a]` | – | `[]` | `[]` |
   | `[inherit]` (in `pre`) | – | – | `[]` |

   Each resolved entry's origin is the layer that wrote it. An entry with a
   `when:` keeps it when inherited.
5. **`inherit` and `builtin` errors.** Each of these is one problem naming the
   file and key: `inherit: false`; `{inherit: true, when: {tags: [bug]}}`; two
   `inherit` entries in one list; `inherit: true` under `work.tags`; and
   `builtin: true` in any layer, whose message contains `inherit: true` and
   `docs/migration-guide-2.8-to-3.0.0.md`. Two identical `{file: a.md}`
   entries in one `tcw-config.yaml` list are one problem naming
   `tcw-config.yaml`; the same `{file: a.md}` in the project's list and in a
   local list `[inherit, {file: a.md}]` is no problem, and the resolved list
   holds it twice, with origins `project` and `local`.
   **Built-in entries.** With no personal files and no `prompt` set for spec,
   `values["work"]["stages"]["spec"]["prompt"] == [{"builtin": True}]`, its
   origin is `built-in`, and `load_config` has no problems (so
   `parse_work_config` accepted it).
6. **The allowlist.** A local file setting each of these gives one problem
   naming `tcw-config.local.yaml` and the key: `id`, `work.backend`,
   `work.path`, `work.tags`, `work.documentation`, `work.hooks.timeout`,
   `work.hooks.output-cap`, `work.stages.spec.enabled`,
   `work.stages.spec.pre`, `work.stages.spec.status`, `taxonomy.extends`,
   `capabilities.extends`, `connected-projects.x.path` (`projects.x.path` after
   TCW-73's rename), `connected-projects.x.jira.credentials.email-env`,
   `work.jira.site`, `work.jira.timeout`, and an unknown key `display`. A local file setting `work.stages: [a]` gives a problem that
   `work.stages` must be a mapping. A local file setting `user.name`,
   `work.stages.spec.prompt`, `work.stages.spec.post`,
   `work.procedures.<a real procedure id>` and
   `work.jira.credentials.email-env` and `work.jira.credentials.token-env` (in
   a Jira-mode project) gives none.
7. **`user` is personal.** `user: {name: a}` in `tcw-config.yaml` is a
   problem. `user.name: " a"`, `user.name: ""` and `user.email: a` in a
   personal file are each a problem. `null` anywhere in a personal file is a
   problem.
8. **Every command that loads config refuses.** With a local file setting
   `id: other`, each of these exits 1 with stderr naming `tcw-config.local.yaml`
   and `id`, and prints nothing on stdout: `tcw work list`,
   `tcw work stage prompt spec`, `tcw config show`, one read-only
   `tcw taxonomy` command and one read-only `tcw capabilities` command.
   `tcw validate` exits 1 with a stdout line starting
   `error: tcw-config.local.yaml: id`. `tcw --version` exits 0.
9. **Other projects ignore personal layers.** In a two-project graph
   (parent and child, both filesystem mode, on this machine):
   - with the child's `tcw-config.local.yaml` setting `id: wrong`,
     `tcw validate` run in the parent reports nothing about that file, and
     `tcw work new --project <child> "x"` run in the parent exits 0 and
     creates the item in the child;
   - with a user-wide `user.name: Brian`, the backend from `open_backend`
     on the parent answers `current_user() == "Brian"`, and the backend from
     `open_project` for the child answers `None`;
   - `tcw work new --project <child> --assign-me "x"` exits 2 and creates
     nothing.
   **Graph readers tolerate what `load_config` refuses.** With the child's
   `tcw-config.yaml` also holding a 2.x `work.lifecycle` block, and with the
   parent's own `tcw-config.local.yaml` holding invalid YAML, `tcw provision`
   in the parent exits as it does with neither problem present, and TCW-73's
   project listing (`tcw projects list`) with `TCW_NO_PERSONAL_CONFIG=1`
   still lists the child.
10. **Paths and commands.** A user-wide `file: prompts/spec.md` reads
    `$XDG_CONFIG_HOME/tcw/prompts/spec.md`. A user-wide `file: ../x.md` is a
    problem from `load_config` naming the user-wide file, whether or not
    `../x.md` exists, so `tcw work list` exits 1 on it.
    A `post` command from the local file runs with the project root as its
    working directory and `TCW_CONFIG_DIR` set to the project root; one from
    the user-wide file gets `TCW_CONFIG_DIR` set to `$XDG_CONFIG_HOME/tcw`.
11. **Origins.** Through `advance` on a filesystem test project (TCW-70's
    backend), a failing `post` hook from the user-wide file gives exit 6, one
    `post_failures` entry whose origin is `user`, and a message containing the
    user-wide file's path. `tcw work stage prompt spec` writes the personal
    note on stderr when the local file sets `work.stages.spec.prompt` and not
    otherwise, and its stdout is the same either way when the local list is
    `[inherit]`. **The packaged text only through the list:** with a local
    `work.stages.spec.prompt: []`, `stage prompt spec` exits 0 and its stdout
    contains no line of the packaged `tcw/work/prompts/spec.md`; with a
    project list `[{blob: house}]` and no `inherit`, its stdout contains
    `house` and no line of the packaged file; with `[{inherit: true},
    {blob: house}]`, it contains both, packaged text first.
12. **`config show`.**
    - With no personal files, `yaml.safe_load` of its stdout equals
      `load_config(...).values`, which contains `{"builtin": True}` entries;
      a stdout line for a built-in entry reads `- builtin: true  #
      tcw/work/prompts/<stage>.md`; and every `--origin` comment is
      `built-in` or `project`.
    - Run twice, both forms print byte-for-byte the same output.
    - With a local file setting `id: other` and `work.stages.spec.prompt:
      [{blob: x}]`: plain `show` exits 1 with empty stdout; `--origin` exits
      1, `yaml.safe_load` of its stdout equals `load_config(...).values`
      (so the refused `id` is not printed as a key), its stdout has a line
      starting `# refused:` that contains `id`, `other` and
      `tcw-config.local.yaml`, and the `blob: x` entry carries a
      `# local:` comment.
    - In a filesystem-mode project, a user-wide
      `work.jira.credentials.email-env` produces no problem, is absent from the
      effective configuration, and is listed as skipped by `--origin`.
13. **Identity, filesystem mode.** With `user.name: Brian`:
    - `list --mine` lists an item with `assignee: Brian` and not one with
      `assignee: brian`;
    - `new --assign-me` writes `assignee: Brian`;
    - `list --mine --assignee x` exits 2.

    With no `user.name`, `TCW_WORK_OWNER=Brian` set and git's `user.name` and
    `user.email` configured in the repository, the filesystem backend's
    `current_user()` returns `None` without raising, and `list --mine` and
    `new --assign-me "x"` each exit 1 with stderr naming `user.name`, the
    user-wide path, `tcw-config.local.yaml` and `work.jira.credentials`;
    `new` creates nothing.

    **Identity, through the interface.** Against a recording test backend
    built on TCW-69's in-memory backend, whose `current_user()` returns
    `"acct-1"`, `list --mine` passes `Query(assignee="acct-1")` to the
    backend and prints what the backend returns, and `new --assign-me`
    passes `Changes(assignee="acct-1")`; the CLI never reads `Item.assignee`
    to decide what to print. With `current_user()` returning `None`,
    `list --mine` exits 1 with the same message as above. The Jira behavior
    itself is TCW-71's to test.
14. **No fallback left.** A test asserts that no Python module under `tcw/`
    contains `TCW_WORK_OWNER`, and that none passes `user.name` or
    `user.email` to `git config`. Skills and guides are left to TCW-74 and
    TCW-75 (Design 9.6), whose criterion 2 refuses the name.
15. **The allowlist is importable.** `from tcw.config import PERSONAL_KEYS`
    gives exactly the six paths in Design 4.1's table, as a tuple of strings
    in that order. Comparing it with `personal.md`'s table is TCW-75's
    criterion 7, not this slice's.
16. **Writers.** With a local file present, `tcw work tags add x` leaves the
    local file byte-for-byte unchanged and changes `tcw-config.yaml` only in
    `work.tags`. A user-wide `post` hook does not appear in `tcw-config.yaml`
    afterwards.
17. **`init` and `validate`.**
    - `tcw init` in a git repository adds `/tcw-config.local.yaml` to the
      `.gitignore` beside `tcw-config.yaml`, once; running it again does not
      add it twice; with a `.gitignore` that already has the line
      `tcw-config.local.yaml` (no `/`), it adds nothing; and
      `git status --porcelain` shows nothing staged (no line whose first
      column is not a space or `?`).
    - `tcw init` outside a git repository exits 0, writes no `.gitignore`,
      and prints exactly the notice of Design 10.2 on stderr.
    - After `git add -f tcw-config.local.yaml`, `tcw validate` prints exactly
      the warning line of Design 10.3 on stdout and exits 0; with the file untracked and
      ignored, and with it untracked and not ignored, no warning; outside a
      git repository, no warning.
18. **Secrets.** In a Jira-mode project, a local
    `work.jira.credentials.token-env: "abc def/123"` gives one problem naming
    `tcw-config.local.yaml` and `work.jira.credentials.token-env`, whose text
    does not contain `abc def/123`. (The shape check is TCW-71's parser; this
    criterion checks the file attribution of Design 5.2 and the requirement on
    the message.)
19. **Test isolation.** `tests/conftest.py` has an autouse fixture, beside the
    existing `TCW_PROJECT_*` guard (`tests/conftest.py:187-188`) and cache
    guard (`:207`), that sets `TCW_NO_PERSONAL_CONFIG=1` and points
    `XDG_CONFIG_HOME` into the test's temporary folder. A test asserts both are
    set in an ordinary test; personal-layer tests remove the first explicitly.
20. **Nothing else changes.** The full test suite passes. The only earlier
    criteria this slice changes on purpose are TCW-70's, which exist when it
    lands (review decision R1), and each change is made in the same commit as
    the behavior: TCW-70's `init` test asserts only that no status-folder
    ignore rule is added, not that `.gitignore` is untouched (TCW-70
    criterion 18); TCW-70's contract test expects `current_user()` to return
    `None`, not raise, for a backend built with no `user_name` (TCW-70
    criterion 1); and TCW-70's `stage prompt` fixtures write `inherit: true`
    where they wrote `builtin: true` (TCW-70 criterion 21).
21. **`open_backend` uses the loader.** On a project whose local file sets
    `id: other`, TCW-70's `open_backend` raises `ConfigError` with exit code
    1, and the message names `tcw-config.local.yaml` and `id`. With
    `TCW_NO_PERSONAL_CONFIG=1` and the same file, it opens. With a local
    `user.name: Brian`, the backend it returns answers `current_user() ==
    "Brian"`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Layers | 1, 2, 9 |
| 2 One loader | 8, 9, 21 |
| 3 Merging and the chain | 3, 4, 5, 7, 11 |
| 4 Allowlist | 6, 7, 12, 18 |
| 5 Problems | 5–8, 10, 18 |
| 6 Paths and commands | 10 |
| 7 Origins | 3, 4, 11 |
| 8 `config show` | 12 |
| 9 Identity | 9, 13, 14, 21 (9.6: none needed, nothing is added) |
| 10 Writing, `.gitignore` | 16, 17, 20 |
| 11 `TCW_PROJECT_<ID>` | none needed: no behavior changes |
| 12 Documentation | 15 (the table itself: TCW-75 criterion 7) |

## Risks

- **A person's override can quietly drop the team's rules.** A personal
  `prompt` list without `inherit` replaces the team's text, and a personal
  `post` list replaces the team's hooks (for example a hook that publishes a
  stage change). That is what the ticket asks for, and the owner confirmed it
  on 2026-10-01. Mitigation: `pre` gates are
  shared and cannot be touched; `stage prompt` notes the change on every run;
  `config show --origin` shows exactly what replaced what.
- **The user-wide file is read in every project.** A mistake there, or a key
  that suits one project and not another (a `post` hook on a side stage, a
  stage a project-defined table does not have), fails every command in every
  project. Mitigation: every message names the file; Jira credential names,
  the likeliest cross-mode key, are skipped outside Jira mode; the local file
  exists for per-project settings.
- **Tests and CI picking up a developer's own files.** Mitigation: the autouse
  fixture (AC 19) and `TCW_NO_PERSONAL_CONFIG=1`.
- **A linked git worktree has no local file**, because the file is untracked
  and a new worktree starts with only tracked files. Commands run in the
  worktree see only the user-wide file. Mitigation: TCW-75 documents it in
  `personal.md` (Notes); the user-wide file covers settings meant for every
  checkout.
- **Removing `TCW_WORK_OWNER` breaks anything that sets it**, including
  scripts and cloud environments. Mitigation: 3.0 is a breaking release; the
  migration guide (TCW-76) maps it to `user.name`, and the missing-identity
  message says exactly what to set.
- **A merged list can hold the same file twice** (Design 3.8). It is visible in
  `config show --origin` and harmless beyond repeated text.
- **Sequencing.** The order is fixed (review decision R1): 69 → 70 → 71 →
  73 → 72 → {74, 77} → 75 → 76, and this slice's direct blocker is TCW-73.
  So when it is implemented, TCW-70's CLI wiring and `open_backend`, TCW-71's
  Jira backend and `work.jira` parser (needed by criteria 6 and 18 and by
  Design 4.7), and TCW-73's surface (`init` outside a repository, the
  `warning:` and finding forms, the contract test, `--mine` and
  `--assign-me` flags) all exist. The risk is the reverse one: this slice
  edits code and tests those slices just wrote, listed in criterion 20.
  TCW-74, TCW-77 and then TCW-75 come after it, so TCW-75's table test can
  import `PERSONAL_KEYS`.

## Notes

- Reconciled with the epic's cross-slice decisions on 2026-10-01.
- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  - a relative `XDG_CONFIG_HOME` is ignored (1.3);
  - `TCW_NO_PERSONAL_CONFIG` with a value other than `1` or empty is an error
    (1.6);
  - configuration problems stop a command through one `ConfigError` (exit 1)
    in `tcw/errors.py` (2.3);
  - `builtin:` in any file is an error; built-in entries are inserted only by
    the loader, as `{builtin: true}` (3.4, review decision R8);
  - an empty chain list is allowed and means "nothing from here down" (3.7);
  - duplicates are checked per layer by the loader, not after merging (3.8);
  - `null` in a personal layer is an error (3.10);
  - credential variable names inside connected-project entries are
    **shared**, reversing the earlier draft to agree with TCW-71's same-file
    rule for delegation (4.1);
  - `work.hooks.timeout` and `work.hooks.output-cap` are shared (4.3);
  - personal Jira credential names are skipped outside Jira mode (4.6);
  - `file:` bindings are confined to the declaring file's folder, checked
    when the configuration loads (6.1);
  - hooks and `generate` scripts get `TCW_CONFIG_DIR` (6.2);
  - `procedure` gets the personal-change note, as `stage prompt` does (7.3);
  - a `None` identity is one backend-neutral message naming `user.name`, both
    personal files and the Jira credential variables (9.2);
  - `--assign-me` with `new --project` naming another project is exit 2
    (9.3);
  - `config show`'s key order is the merge order (8.1);
  - either spelling of the local file's ignore line counts as present, and
    the `init` notice and `validate` warning have fixed wording with no git
    words (10.2, 10.3);
  - a filesystem comment records no author (9.4);
  - this slice adds nothing to the documentation allowance list unless it has
    grown to cover keys and variables (9.6);
  - `TCW_PROJECT_<ID>` stays the only way to say where a project lives (11),
    which answers the ticket's open question.
- **Cross-slice findings settled by the epic decisions.**
  - The ninth backend member `me()` this spec proposed is replaced by
    TCW-69's `current_user()`, one of eleven operations (decisions 1 and 17).
    The owner question about a ninth member is closed.
  - The shared/overridable table and the configure skill are TCW-75's
    (decision 3); this slice supplies `PERSONAL_KEYS` (Design 12), which is
    the constant TCW-75's Notes asked this spec to name.
  - `config show`, `--mine` and `--assign-me` are named by TCW-73 and follow
    its output rules (decisions 2 and 10). TCW-73's surface now lists
    `--assign-me` on both `new` and `edit`, so the disagreement this spec
    noted is gone.
  - Exception classes live in `tcw/errors.py` (decision 8).
  - Hooks run from the project root, and `TCW_SLUG` is the full slug
    (decision 11).
  - The `docs/capabilities/work/` records are TCW-70's to keep or remove
    (decision 12), and `start` with its record is removed by TCW-70
    (decision 2).
  - Release notes start at their first `##` (decision 15).
  - TCW-71 answered its own open points: its credential keys are
    `work.jira.credentials.email-env` and `token-env`, and `work.jira` is not
    inherited from parent projects (TCW-71 Capability changes), so personal
    layers are 3.0's only layering of configuration.
- **Changes other slices need.** Nothing has been posted to those tickets.
  - **TCW-69:** already made in its 2026-10-02 revision under review decision
    R8: `Binding` has `origin`, `parse_work_config` takes `origins` and
    returns `Problem(key_path, message)`, `builtin: true` stays accepted, and
    duplicates are allowed. Still needed: `Outcome` gains `post_failures`;
    `TCW_CONFIG_DIR` joins the hook and `generate` environments; and the
    empty-list refusal for procedures ("an empty list is not an opt-out",
    TCW-69 plan.md:184) is dropped, with no empty-list refusal for `prompt`
    either (Design 3.7). `tcw/errors.py` gains `ConfigError` (exit 1), added
    by this slice.
  - **TCW-70:** `current_user()` returns `None` rather than raising
    `BackendError` when built with no `user_name` (its Design 3.3 item 11 and
    criterion 1; review decision R3). Its criterion 18 should say that
    `init` adds no status-folder ignore rule, not that it adds no line to
    `.gitignore`, because this slice later adds `/tcw-config.local.yaml`
    there. Its Design 7.2 should say that `stage prompt` composes the
    resolved `prompt` list, which holds the packaged prompt only where a
    `builtin` (later `inherit`) entry or the built-in default puts it, not
    that it always adds the packaged file. `open_backend` is changed by this
    slice as Design 2.5 says. If TCW-70 does not make these edits, this
    slice makes them to TCW-70's tests (criterion 20).
  - **TCW-71:** its Design 10 says the Jira `current_user()` never returns
    `None` and raises `BackendError` for unset credential variables. Review
    decision R3 says it returns `None` and never raises for a missing
    identity, so TCW-71 must return `None` there (Design 9.2). Its message
    rule for a malformed credential name (name the key, never the value) is
    already in TCW-71 Design 1.
  - **TCW-73:** add `config show`'s row to the contract test (Design 8.1).
    The `init` notice and `validate` warning (Design 10.2, 10.3) avoid every
    git word, so its git-word test needs no exemption for them. Keep the two
    credential paths in `PERSONAL_KEYS` correct through the
    `connected-projects` to `projects` rename (only `work.jira.*` paths are
    on the list, so the rename changes none of them).
  - **TCW-75:** writes `personal.md`, the table and the router line, and
    documents that a linked git worktree has no local file (Risks). This
    slice writes **no** first `personal.md` and **no** table test, so
    TCW-75 writes the test tying the table to `PERSONAL_KEYS` from scratch
    rather than extending one (its Design 6.3 and Notes say otherwise). Its
    table's `user.*` row should read `user.name`, the only key under `user`.
  - **TCW-76:** the migration guide must also map `TCW_WORK_OWNER` (and the
    git identity fallback) to `user.name`, map `builtin: true` to
    `inherit: true` (and explain that a list without it replaces the
    packaged text), list `TCW_CONFIG_DIR` as a new hook variable, and add
    `/tcw-config.local.yaml` to `.gitignore` in existing projects, since
    `tcw init` does that only for new ones.
  - **TCW-77:** its project endpoint's `user` field ("filesystem mode:
    TCW-72's `user.name`, or `null`") can come from `current_user()` in both
    modes, so the viewer does not read configuration for it.
- **Questions only the owner can answer.** None remain.
  - Settled by the owner on 2026-10-01: personal configuration may replace the
    team's `post` hooks, as the ticket says; `pre` stays shared (Design 4.1).
- **Assumptions.**
  - This slice is implemented after TCW-69, TCW-70, TCW-71 and TCW-73
    (review decision R1), so `advance`, `stage prompt`, `list`, `new`,
    `edit`, `open_backend`, the Jira backend and TCW-73's surface exist as
    3.0 code. The criteria that run commands depend on that.
  - The shape of `work.jira` beyond its credential names is TCW-71's; the
    loader passes the merged block to TCW-71's parser.
  - Problem 3's count of readers is of TCW 2.8.1 as checked out on
    2026-10-01; by the time this is implemented, TCW-70 will have removed
    several of them.
- **Request.** `initial-request.md` was written by an agent from the ticket,
  with no user to ask; its assumptions are listed in its own Notes.
- **Driving this item.** Its implementation edits `tcw/`. For the whole epic
  (TCW-70 to TCW-77) the 2.x board is edited by hand, and this item's Jira
  ticket, TCW-72, is moved by hand to In Progress, In Review and Done as the
  item moves (epic decision 7). Read-only views of the board may use a
  released 2.8 `tcw` installed outside this checkout.

### Review 2026-10-02

Findings of the 2026-10-02 review, each checked against the repository and
the sibling specs; review decisions R1 to R20 applied where they touch this
slice (R1, R3, R4, R5, R8, R13, R14).

1. ACCEPTED. Settled by R3: `current_user()` returns `None` and never raises
   for a missing identity; Design 9.2 says so for both backends, and Notes
   now asks TCW-70 (Design 3.3 item 11, criterion 1) and TCW-71 (Design 10)
   to change.
2. ACCEPTED. Settled by R8: a built-in entry is `{builtin: true}` in
   `values`, inserted only by the loader, which refuses `builtin:` in a file
   before merging (Design 2.1, 3.4); new check in criterion 5.
3. ACCEPTED. Settled by R8: TCW-69's parser allows duplicates (its plan
   already says so); the per-layer refusal is the loader's (Design 3.8),
   and criterion 5 now tests both halves.
4. ACCEPTED. Settled by R8: `origins` is passed to `parse_work_config`,
   problems come back as `Problem(key_path, message)`, and Design 5.2 gives
   the rule for picking a problem's file.
5. ACCEPTED. Settled by R1 (73 → 72): TCW-71 and TCW-73 land first; Risks
   and Assumptions rewritten, `state.yaml` already lists TCW-73 as the
   blocker.
6. ACCEPTED. TCW-70 criterion 18 forbids any `.gitignore` line; criterion 20
   now names it as a test this slice narrows, and Notes asks TCW-70 to
   narrow it first.
7. ACCEPTED. Design 3.5 says the packaged text reaches a prompt only through
   the resolved list and the 2.x fallback (`tcw/work/resolve.py:456`) must
   go; criterion 11 checks `[]`, a list without `inherit` and one with it
   through `stage prompt`; Notes asks TCW-70 to reword its Design 7.2.
8. ACCEPTED. Design 9.3: identity is always the acting project's;
   `--assign-me` with `new --project` is exit 2 (`delegate` takes no
   assignee, R5); `edit` of another project's item is already refused by
   TCW-73 Design 3.4. Tested in criterion 9.
9. ACCEPTED. Criterion 9 no longer relies on a hook that creation never
   runs; it checks `open_project`'s `current_user()` and that `new --project`
   ignores the target's broken local file.
10. ACCEPTED. Refused values move to the trailing comment block (Design
    8.2, 8.3), and criterion 12 now requires `--origin` output to parse to
    exactly `values`.
11. ACCEPTED. Design 2.2 adds `read_project_file` for the registry and
    `provision`'s two readers, keeping their tolerance
    (`tcw/store/fs.py:1567-1570`, `tcw/store/project.py:595-597`); criterion
    9 tests it.
12. ACCEPTED. The `init` notice and `validate` warning have fixed wording
    with no git words (Design 10.2, 10.3), applying R4; the tracked check
    uses R4's read-only status command.
13. ACCEPTED. Design 2.5 names `open_backend`, `open_project` and the
    delegation target, what each calls, and the switch to `ConfigError`;
    criterion 21 tests it.
14. ACCEPTED. The stale TCW-71 note is removed; criterion 13's interface
    test no longer speaks of a displayed assignee.
15. ACCEPTED. Notes tells TCW-75 to write its table test from scratch.
16. ACCEPTED. Key order defined (Design 8.1); `file:` confinement is
    checked when the configuration loads (Design 6.1, criterion 10); both
    spellings of the ignore line count as present (Design 10.2, criterion
    17).
