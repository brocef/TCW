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
  credentials in Jira mode, `list --mine` and `--assign-me`, and the message
  when no identity is set.

**Capabilities, changed:**

- `work/configure-the-work-lifecycle`, `work/configure-procedures`,
  `work/run-a-lifecycle-stage` and `work/run-a-procedure`: each describes
  `builtin: true`, which this slice replaces with `inherit: true`.
  `run-a-lifecycle-stage` also gains the stderr note when personal layers
  changed a prompt. TCW-70 rewrites the same records for the 3.0 `work.stages`
  shape; whichever slice lands second reconciles the text.
- `cli/validate-a-node`: warns when `tcw-config.local.yaml` is tracked, and
  reports problems in personal files.
- `cli/scaffold-the-doc-trees` (`tcw init`): adds `tcw-config.local.yaml` to
  `.gitignore`.
- `skills/configure`: the configure skill now covers personal configuration
  and holds the shared/overridable table.

**Checked and unchanged:** `cli/point-tcw-at-a-project-i-already-have`
(`TCW_PROJECT_<ID>`). Design 11 keeps that variable as the only way to say
where a project lives on this machine. `work/start-a-work-item` describes
`TCW_WORK_OWNER`, but the `start` verb and its record go in TCW-70 and TCW-73,
so this slice does not edit it.

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
- **Command names and the exit-code table.** TCW-73 names `tcw config show`,
  `list --mine` and `--assign-me` and fixes the table. This slice implements
  their behavior, using TCW-73's codes (1 for a configuration problem, 2 for a
  usage mistake).
- **The Jira backend.** How TCW-71 authenticates, and how it turns its
  credentials into an identity, is TCW-71's. This slice fixes only the
  interface member it answers through (Design 9.2) and which credential keys a
  person may override.
- **Where a project lives on this machine.** It stays `TCW_PROJECT_<ID>`
  (Design 11). No personal-config key for it is added.
- **Display preferences**, or any personal key not on the allowlist. The
  original decision record mentioned display preferences; the ticket dropped
  them.
- **A `--json` form of `config show`**, and any command that writes a personal
  file. Personal files are edited by hand.
- **User guides** (TCW-75) and **the migration guide** (TCW-76). This slice
  writes only the shared/overridable table in the configure skill's references,
  which the ticket makes canonical.
- **Validating the shape of `taxonomy`, `capabilities` and `connected-projects`**
  in `tcw-config.yaml`. Their parsers stay where they are; this slice only
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
   - `values`: the effective configuration as a plain mapping;
   - `origins`: the origin of every scalar and every list entry, keyed by key
     path (`work.stages.spec.prompt[2]`);
   - `work`: TCW-69's parsed `WorkConfig`, from `parse_work_config(values)`;
   - `problems`: every problem found, each naming the file and key it came
     from (Design 5);
   - `skipped`: personal values that were read but not applied (Design 4.5).

   `personal=False` reads `built-in` and `project` only. The project registry
   uses it for every project, including the acting one, because it reads only
   shared keys (`id`, `connected-projects`).
2. Every 3.0 reader of `tcw-config.yaml` goes through this function. The five
   readers in Problem 3 are either deleted with the 2.x code they serve
   (TCW-70 removes the 2.x work store, which owns most of them) or changed to
   call the loader. The YAML read itself, with its duplicate-key refusal,
   exists once, in the loader; the two copies of the duplicate-key loader
   (`fs.py:1465-1481`, `project.py:26-43`) become one.
3. The result is computed once per command. A command that loads config and
   gets problems exits 1 before doing anything else, except
   `tcw config show --origin` (Design 8).
4. Commands that **do not** load the acting project's configuration: `tcw
   --version`, `--help` on any command, and `tcw init`, which reads and edits
   only `tcw-config.yaml` (Design 10). Every other command loads it.

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
4. **Built-in entries are internal.** They are bindings of kind `builtin`,
   produced only by the `built-in` layer. **[Decision]** Writing `builtin:` in
   any file is an error that says to use `inherit: true` and names TCW-69's
   migration guide (`docs/migration-guide-2.8-to-3.0.0.md`). `config show`
   prints a built-in entry as `builtin: <packaged file>` so it can be seen, but
   that form is never accepted as input.
5. **The `inherit` entry's rules.** Each is an error:
   - `inherit:` with any value other than `true` (there is no
     `inherit: false`; leaving the entry out means replace);
   - `inherit` together with `when:` or any other key in the same entry;
   - more than one `inherit` entry in one list;
   - `inherit` in any list other than the four chain lists.
6. **[Decision] An empty list is allowed in every chain list** and means
   "nothing from here down". TCW 2.8 refuses an empty `prompt` or `procedures`
   list (`tcw/store/base.py:2664-2690`, `:3084-3089`) because, after parsing,
   it cannot be told apart from an absent key, which falls back to the
   built-in text. The chain is decided before parsing, where "set to `[]`" and
   "not set" are different, so the reason no longer holds. `[{blob: ""}]` still
   works. This changes TCW-69's parser rule, which keeps the 2.8 refusal (see
   Notes).
7. **[Decision] Duplicates** (same kind, value and `when:`) are refused within
   one layer's list as written, as TCW-69's parser does. They are not removed
   after merging: if a person's list and the team's both name the same file and
   the person inherits, the file appears twice, and `config show --origin`
   shows both entries with their layers.
8. **Every other list is replaced whole** by a layer that sets it. Among
   overridable keys none is a list, so this matters only for `project` over
   `built-in` (for example `work.tags`).
9. **[Decision] `null`** in a personal layer is an error. A personal layer
   cannot remove a value, only replace it, so a `null` there has no meaning to
   give it. `null` in `tcw-config.yaml` keeps whatever meaning that key's
   parser gives it today.

### 4. What a personal layer may set

1. **The allowlist.** One constant in `tcw/config.py` lists the key paths a
   personal layer may set. `*` stands for exactly one key. Anything not on it
   is **shared**. A key added to TCW later is shared unless it is added here.

   | Key path | Layers |
   | --- | --- |
   | `user.name` | personal only |
   | `work.stages.*.prompt` | all |
   | `work.stages.*.post` | all |
   | `work.procedures.*` | all |
   | `work.jira.credentials.*` | all |
   | `connected-projects.*.jira.credentials.*` | all |

   - `work.jira.credentials.*` are the credential variable-name keys TCW-71
     defines (TCW 2.8's are `email-env` and `token-env`,
     `tcw/store/base.py:1620-1621`). Their exact names are TCW-71's.
   - **[Decision]** Credential variable names inside a connected-project entry
     are overridable too. The ticket lists connected-project entries as shared
     and credential variable names as overridable; TCW-71 lets a delegator's
     connected-project entry carry a target's credential variable names, which
     falls under both. The variable names a person's shell exports are a
     personal fact, so the narrower rule wins. The entry's other keys stay
     shared. The key path follows TCW-73's rename of `connected-projects`.
2. **Shared**, among others: `id`, `work.backend`, `work.path`,
   `work.repository`, the Jira site and project, every stage's `enabled`,
   `status` and `pre`, field and priority mappings, the inbox query,
   `work.tags`, `work.documentation`, `taxonomy.*` and `capabilities.*`
   (including `extends`), and connected-project entries apart from their
   credential variable names.
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
   personal file". This covers unknown keys too.
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
7. **Credential variable names are names.** **[Decision]** Each must match
   `^[A-Za-z_][A-Za-z0-9_]*$`, in every layer. A value that does not is a
   problem whose message names the key and does **not** print the value, so a
   token pasted by mistake is not echoed to a terminal or a log.

### 5. Problems and exit codes

1. Every problem names the file and the key path: `<file>: <key path>:
   <message>`. A problem found by TCW-69's parser on the merged mapping is
   given the file of the value's origin, so a bad binding in a personal file is
   reported against that file, not against `tcw-config.yaml`.
2. Problems in any layer (unreadable YAML, a duplicate key, a shared key, a bad
   binding, a `TCW_NO_PERSONAL_CONFIG` value) make every command that loads
   config exit 1, writing the problems to stderr and nothing to stdout.
3. The exception is `tcw config show --origin` (Design 8.3).
4. `tcw validate` reports these problems the same way and exits 1. A project's
   continuous-integration run is not affected by a developer's personal files,
   because it has none (or sets `TCW_NO_PERSONAL_CONFIG=1`).

### 6. Relative paths, and commands from personal layers

1. **`file:` bindings resolve from the declaring file's folder**, and must stay
   inside it. Today a `file:` path is resolved from the project root and
   refused if it leaves it, symlinks followed (`_confined`,
   `tcw/work/resolve.py:123-137`). **[Decision]** The same check applies with
   the declaring file's folder as the root: the project root for `project` and
   `local`, and `~/.config/tcw/` (or `$XDG_CONFIG_HOME/tcw/`) for `user`. A
   person keeps their own prompt files under that folder.
2. **`generate:` and `command:` values are command lines, not paths.** TCW
   cannot tell which words in them are paths, so it does not rewrite them.
   They run with the project root as the working directory, as today
   (`tcw/work/generate.py:107-111`). **[Decision]** Each one runs with
   `TCW_CONFIG_DIR` set to the declaring file's folder (the project root for
   `project`), so a personal hook can reach its own script as
   `"$TCW_CONFIG_DIR/scripts/x.sh"`. This adds one variable to the hook
   environment TCW-69 Design 6.5 lists.
3. The trust model is unchanged: configuration is the user's own file, and
   hooks run as the user (`tcw/work/hooks.py:11-14`). A personal file is, if
   anything, more the user's own than the team's file.

### 7. Origins in results

1. **Bindings carry their origin.** TCW-69's `Binding(kind, value, when)`
   (TCW-69 plan, Task 4) gains `origin` (the layer name and file). The `file:`
   root (Design 6.1) and `TCW_CONFIG_DIR` (Design 6.2) are read from it.
2. **`advance` names the layer of a failed `post` hook.** TCW-69's `Outcome`
   (`code`, `stage`, `messages`, `overridden`) gains `post_failures`, a tuple of
   `(binding, origin, detail)`, one per failed `post` binding. The message for
   each says which hook failed, why, and the file it came from, for example:
   "post hook `./notify.sh` from /home/a/.config/tcw/config.yaml failed (exit
   1)". The exit code is TCW-69's 6. `pre` gates need no origin, because they
   can only come from `tcw-config.yaml`.
3. **`stage prompt` and `procedure` note personal changes.** When either
   personal layer sets the list being resolved (`work.stages.<stage>.prompt`,
   or `work.procedures.<id>`), the command writes one line to stderr naming
   the files: "this prompt was changed by personal configuration:
   tcw-config.local.yaml". stdout is the resolved text, as without the note.
   **[Decision]** `procedure` gets the note too, because a procedure list
   resolves through the same chain; the ticket names only `stage prompt`.

### 8. `tcw config show [--origin]`

1. **Plain.** Prints the effective configuration (`values`) to stdout as YAML,
   with every key, including built-in defaults and the built-in chain entries
   (Design 3.4), in the order of the built-in key list and then file order.
   Problems: exit 1, nothing on stdout.
2. **`--origin`.** Prints the same YAML with a comment after each scalar and
   each list entry naming its origin: `# built-in`, `# project`,
   `# user: <path>` or `# local: <path>`. The output still parses as YAML to the
   same mapping. Personal values that were `skipped` (Design 4.6) are listed
   after the configuration in a comment block, each with its file and reason.
3. **`--origin` still runs with problems.** It prints what it can and exits 1,
   with the problems on stderr:
   - a shared key set in a personal file is shown where it was written,
     marked `# refused: shared key (<file>)`, and is not merged;
   - a personal file that cannot be read at all (bad YAML) is named on stderr
     and contributes nothing.

   This is how a person finds the line that is stopping every other command.
   A broken `tcw-config.yaml` still makes `--origin` exit 1 with nothing on
   stdout, because nothing above it can be merged without it.

### 9. Identity

1. **Filesystem mode** uses `user.name` from the effective configuration (so
   only from a personal layer, Design 4.5). It is compared with an item's
   `assignee` exactly: same characters, same case.
2. **The backend answers.** **[Decision]** Identity is a ninth member of
   TCW-69's backend interface: `me() -> str`. It returns the identity in the
   same form the backend uses for `Item.assignee`, or raises an error with
   exit 1 whose message says how to set one.
   - The filesystem backend is constructed with `user.name` and returns it.
     With none, the message names both personal files: "no identity: set
     `user.name` in `<user-wide path>` or in `tcw-config.local.yaml`".
   - The Jira backend answers from its credentials (TCW-71), and its message
     names the credential variables when they are not set.

   A non-filesystem store can answer "who is calling" (Jira's own
   current-user lookup), so this passes the litmus test, and the CLI never
   branches on which backend it has.
3. **Commands that use it:**
   - `list --mine` is `Query(assignee=backend.me())`;
   - `--assign-me` on `new` and `edit` sets `assignee` to `backend.me()`;
   - `--mine` together with `--assignee`, and `--assign-me` together with
     `--assignee`, are usage errors (exit 2).

   `me()` is called only by these, so no other command ever needs an identity.
4. **No fallback.** `TCW_WORK_OWNER`, `--owner`, and git's `user.name` and
   `user.email` are never read for identity. Every use in code 3.0 keeps is
   deleted, along with every message that tells a user to set or use them.
   Today these are `_local_owner` and its callers (`tcw/work/cli.py:1447-1458`,
   `:1620-1624`, `:2666`, `:3154`, `:3399`, `:3647`, `:3760-3764`, `:4015`,
   `:4922`, `:4990`), `tcw/store/base.py:3495`, `tcw/tracker/sync.py:1062` and
   `tcw/serve/__init__.py:1040-1046`. Most go with the 2.x code TCW-70 and
   TCW-73 delete (claims, `start`, the tracker verbs); whatever is still there
   when this slice is implemented is removed by it. The docstring of
   `override_variable` (`tcw/store/project.py:69-71`), which cites
   `TCW_WORK_OWNER` as the precedent for `TCW_PROJECT_<ID>`, is reworded.

### 10. Writing configuration, and keeping the local file untracked

1. **Commands that edit configuration write only `tcw-config.yaml`**, and edit
   it from its own text, never from the effective configuration, so a personal
   value is never copied into the team's file. Today's writers already work on
   the file's own text (`config_edit`, used by `_write_node_config`,
   `tcw/store/fs.py:2183-2210`); 3.0's writers (`tags add|rm`, the `extends`
   subcommands, `init`) keep that. No command writes a personal file.
2. **`tcw init`** adds the line `/tcw-config.local.yaml` to the `.gitignore` in
   the folder holding `tcw-config.yaml`, if that line is not already there
   (today's `ensure_ignored`, `tcw/store/fs.py:982-994`, does exactly this
   check). The leading `/` limits the rule to that folder. Outside a git
   repository it writes no `.gitignore` and prints a notice on stderr saying
   why. It stages nothing; TCW never changes git state.
3. **`tcw validate`** warns (exit 0 if nothing else is wrong) when
   `tcw-config.local.yaml` is tracked by git in the acting project, reading git
   to find out. Outside a git repository there is nothing to check.
4. **Secrets** never go in configuration: configuration names environment
   variables (Design 4.7 enforces the shape of those names).

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
is not configuration.

### 12. Documentation this slice writes

- `skills/configure/references/personal.md`: the two personal files, the
  chain, identity, `config show`, and **the shared/overridable table**, which
  the ticket makes canonical and TCW-75 links to. The table is generated from
  the allowlist constant by a test that fails when they differ (AC 15).
- `skills/configure/SKILL.md`: one line routing personal configuration to it.
- The release-note and changelog entry files under `upcoming/`, as the project's
  documentation entries require.

User guides (`docs/guide/`) are TCW-75's; the migration steps (`builtin: true`
to `inherit: true`, `TCW_WORK_OWNER` to `user.name`, ignoring the local file in
existing projects) are TCW-76's.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| Loading and merging layers, the allowlist, `config show` | **Not a store operation.** Configuration is files in the repository and the user's home in both backends; nothing here touches a work store. |
| `me()` | **Backend interface.** Jira answers from the authenticated account; the filesystem backend from `user.name`. A third store would answer from its own login. |
| `list --mine`, `--assign-me` | **Model**, over `me()`, `Query` and `Changes`. |
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
   `docs/migration-guide-2.8-to-3.0.0.md`.
6. **The allowlist.** A local file setting each of these gives one problem
   naming `tcw-config.local.yaml` and the key: `id`, `work.backend`,
   `work.path`, `work.tags`, `work.documentation`, `work.hooks.timeout`,
   `work.hooks.output-cap`, `work.stages.spec.enabled`,
   `work.stages.spec.pre`, `work.stages.spec.status`, `taxonomy.extends`,
   `capabilities.extends`, `connected-projects.x.path`, and an unknown key
   `display`. A local file setting `work.stages: [a]` gives a problem that
   `work.stages` must be a mapping. A local file setting `user.name`,
   `work.stages.spec.prompt`, `work.stages.spec.post`,
   `work.procedures.<a real procedure id>` and
   `work.jira.credentials.<a TCW-71 key>` (in a Jira-mode project) gives none.
7. **`user` is personal.** `user: {name: a}` in `tcw-config.yaml` is a
   problem. `user.name: " a"`, `user.name: ""` and `user.email: a` in a
   personal file are each a problem. `null` anywhere in a personal file is a
   problem.
8. **Every command that loads config refuses.** With a local file setting
   `id: other`, each of these exits 1 with stderr naming `tcw-config.local.yaml`
   and `id`, and prints nothing on stdout: `tcw work list`,
   `tcw work stage prompt spec`, `tcw validate`, `tcw config show`, one
   read-only `tcw taxonomy` command and one read-only `tcw capabilities`
   command. `tcw --version` exits 0.
9. **Other projects ignore personal layers.** In a two-project graph whose
   child has a `tcw-config.local.yaml` setting `id: wrong`, `tcw validate` run
   in the parent reports nothing about that file. A user-wide file setting a
   `post` hook on review is not run when an item in a delegation target is
   created (`new --project`).
10. **Paths and commands.** A user-wide `file: prompts/spec.md` reads
    `$XDG_CONFIG_HOME/tcw/prompts/spec.md`; `file: ../x.md` there is refused.
    A `post` command from the local file runs with the project root as its
    working directory and `TCW_CONFIG_DIR` set to the project root; one from
    the user-wide file gets `TCW_CONFIG_DIR` set to `$XDG_CONFIG_HOME/tcw`.
11. **Origins.** Through `advance` on a filesystem test project (TCW-70's
    backend), a failing `post` hook from the user-wide file gives exit 6, one
    `post_failures` entry whose origin is `user`, and a message containing the
    user-wide file's path. `tcw work stage prompt spec` writes the personal
    note on stderr when the local file sets `work.stages.spec.prompt` and not
    otherwise, and its stdout is the same either way when the local list is
    `[inherit]`.
12. **`config show`.**
    - With no personal files, `yaml.safe_load` of its stdout equals
      `load_config(...).values`, and every `--origin` comment is `built-in` or
      `project`.
    - With a local file setting `id`, plain `show` exits 1 with empty stdout;
      `--origin` exits 1, its stdout contains `# refused: shared key`, and
      every other value is printed.
    - In a filesystem-mode project, a user-wide
      `work.jira.credentials.<key>` produces no problem, is absent from the
      effective configuration, and is listed as skipped by `--origin`.
13. **Identity, filesystem mode.** With `user.name: Brian`:
    - `list --mine` lists an item with `assignee: Brian` and not one with
      `assignee: brian`;
    - `new --assign-me` writes `assignee: Brian`;
    - `list --mine --assignee x` exits 2.

    With no `user.name`, `TCW_WORK_OWNER=Brian` set and git's `user.name` and
    `user.email` configured in the repository, `list --mine` exits 1 and
    stderr names the user-wide path and `tcw-config.local.yaml`.
14. **No fallback left.** A test asserts that no file under `tcw/` or
    `skills/` contains `TCW_WORK_OWNER`, and that no module under `tcw/` passes
    `user.name` or `user.email` to `git config`.
15. **The table matches the allowlist.** A test reads the table in
    `skills/configure/references/personal.md` and asserts that its overridable
    rows are exactly the allowlist constant's paths.
16. **Writers.** With a local file present, `tcw work tags add x` leaves the
    local file byte-for-byte unchanged and changes `tcw-config.yaml` only in
    `work.tags`. A user-wide `post` hook does not appear in `tcw-config.yaml`
    afterwards.
17. **`init` and `validate`.**
    - `tcw init` in a git repository adds `/tcw-config.local.yaml` to the
      `.gitignore` beside `tcw-config.yaml`, once; running it again does not
      add it twice; `git status --porcelain` shows nothing staged.
    - `tcw init` outside a git repository writes no `.gitignore` and prints a
      notice on stderr.
    - After `git add -f tcw-config.local.yaml`, `tcw validate` prints a warning
      naming the file and exits 0; with the file untracked, no warning.
18. **Secrets.** A local `work.jira.credentials.<key>: "abc def/123"` gives a
    problem whose text does not contain `abc def/123`.
19. **Test isolation.** `tests/conftest.py` has an autouse fixture, beside the
    existing `TCW_PROJECT_*` guard (`tests/conftest.py:187-188`) and cache
    guard (`:207`), that sets `TCW_NO_PERSONAL_CONFIG=1` and points
    `XDG_CONFIG_HOME` into the test's temporary folder. A test asserts both are
    set in an ordinary test; personal-layer tests remove the first explicitly.
20. **Nothing else changes.** The full test suite passes.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Layers | 1, 2, 9 |
| 2 One loader | 8, 9 |
| 3 Merging and the chain | 3, 4, 5, 7 |
| 4 Allowlist | 6, 7, 12, 18 |
| 5 Problems | 5–8 |
| 6 Paths and commands | 10 |
| 7 Origins | 3, 4, 11 |
| 8 `config show` | 12 |
| 9 Identity | 13, 14 |
| 10 Writing, `.gitignore` | 16, 17 |
| 11 `TCW_PROJECT_<ID>` | none needed: no behavior changes |
| 12 Documentation | 15 |

## Risks

- **A person's override can quietly drop the team's rules.** A personal
  `prompt` list without `inherit` replaces the team's text, and a personal
  `post` list replaces the team's hooks (for example a hook that publishes a
  stage change). That is what the ticket asks for. Mitigation: `pre` gates are
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
  worktree see only the user-wide file. Mitigation: documented in
  `personal.md`; the user-wide file covers settings meant for every checkout.
- **Removing `TCW_WORK_OWNER` breaks anything that sets it**, including
  scripts and cloud environments. Mitigation: 3.0 is a breaking release; the
  migration guide (TCW-76) maps it to `user.name`, and the missing-identity
  message says exactly what to set.
- **A merged list can hold the same file twice** (Design 3.7). It is visible in
  `config show --origin` and harmless beyond repeated text.
- **Sequencing.** This slice needs TCW-69's library and TCW-70's CLI wiring.
  If TCW-73 lands later and reshapes `list`, `new` and `edit`, it must keep
  `--mine` and `--assign-me` calling `me()`. AC 13 guards the behavior through
  the commands.

## Notes

- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  - a relative `XDG_CONFIG_HOME` is ignored (1.3);
  - `TCW_NO_PERSONAL_CONFIG` with a value other than `1` or empty is an error
    (1.6);
  - `builtin:` in any file is an error; built-in entries are internal and
    displayed only (3.4);
  - an empty chain list is allowed and means "nothing from here down" (3.6);
  - duplicates are checked per layer, not after merging (3.7);
  - `null` in a personal layer is an error (3.9);
  - credential variable names inside connected-project entries are
    overridable (4.1);
  - `work.hooks.timeout` and `work.hooks.output-cap` are shared (4.3);
  - personal Jira credential names are skipped outside Jira mode (4.6);
  - credential variable names must look like variable names, and a bad one is
    never printed (4.7);
  - `file:` bindings are confined to the declaring file's folder (6.1);
  - hooks and `generate` scripts get `TCW_CONFIG_DIR` (6.2);
  - `procedure` gets the personal-change note, as `stage prompt` does (7.3);
  - identity is a ninth backend member, `me()` (9.2);
  - `TCW_PROJECT_<ID>` stays the only way to say where a project lives (11),
    which answers the ticket's open question.
- **Changes other slices need.** Nothing has been posted to those tickets.
  - **TCW-69:** `builtin: true` becomes `inherit: true` (the ticket already
    says so); `Binding` gains `origin`; `Outcome` gains `post_failures`;
    `TCW_CONFIG_DIR` joins the hook environment (Design 6.5 there); the
    backend interface gains `me()`, a ninth member after the owner confirmed
    eight; the empty-list refusal for `prompt` and procedures is dropped; and
    `parse_work_config` is called on the merged mapping, with its problems
    mapped back to files by key path.
  - **TCW-71:** must name its credential variable keys under `work.jira`
    (this spec assumes `work.jira.credentials.*`), implement `me()` in the
    same form as `Item.assignee`, and say whether `work.jira` inherits from
    parent projects as 2.8's `work.tracker` does (capability
    `work/inherit-tracker-settings-from-parent-nodes`). If it does, that is a
    second way of layering configuration, and personal layers sit on top of
    its result.
  - **TCW-73:** its `new` flags omit `--assign-me`, which this ticket puts on
    `new` as well as `edit`; the two tickets disagree and TCW-73's list needs
    it. Its rename of `connected-projects` fixes the key path of
    Design 4.1's second credential row.
  - **TCW-76:** the migration guide must also map `TCW_WORK_OWNER` (and the
    git identity fallback) to `user.name`, and add `/tcw-config.local.yaml`
    to `.gitignore` in existing projects, since `tcw init` does that only for
    new ones.
  - **TCW-75:** links to `skills/configure/references/personal.md` for the
    table, as its ticket already says.
- **Questions only the owner can answer.**
  - Should a person be able to replace the team's `post` hooks at all, or
    only add to them (that is, should a personal `post` list be required to
    contain `inherit: true`)? The ticket says replace; this spec follows it.
  - Is a ninth backend member acceptable, given the owner confirmed eight for
    TCW-69? The alternative is for the CLI to branch on the backend kind,
    which the abstraction test argues against.
- **Assumptions.**
  - This slice is implemented after TCW-70 has wired TCW-69's model into the
    CLI, so `advance`, `stage prompt`, `list`, `new` and `edit` exist as 3.0
    commands. The criteria that run commands depend on that.
  - The shape of `work.jira` beyond its credential names is TCW-71's and is
    passed through unparsed, as TCW-69 does.
  - Problem 3's count of readers is of TCW 2.8.1 as checked out on
    2026-10-01; by the time this is implemented, TCW-70 will have removed
    several of them.
- **Request.** `initial-request.md` was written by an agent from the ticket,
  with no user to ask; its assumptions are listed in its own Notes.
- **Driving this item.** Its implementation edits `tcw/`. From `implement`
  onwards, the repository's board is driven by editing files, per `CLAUDE.md`.
