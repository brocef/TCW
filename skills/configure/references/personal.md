# Personal configuration

**Personal configuration** is settings that belong to one person rather than
to the team: their name, the variables holding their Jira credentials, and
their own additions to a stage's instructions or hooks. It lives in files
that are never shared, and in environment variables, and it may set only the
keys the table at the end of this document marks `Overridable` or
`Personal only`; that set is the **allowed list**. Everything else is
**shared**: the team sets it in `.tcw/tcw-config.yaml`. A personal file that
sets a shared key is an error naming the file and the key, and every command
stops with exit code 1 until it is removed:

```text
tcw work list: .tcw/tcw-config.local.yaml: work.tags: a shared key; a personal file cannot set it
```

## The layers, in order

A command reads its project's configuration from five layers, lowest first. A
higher layer wins.

1. **TCW's own defaults** (shown as `built-in`).
2. **`.tcw/tcw-config.yaml`**, the team's file, in the project's `.tcw/`
   folder.
3. **The user-wide file**, which applies to every project this person works
   in: `$XDG_CONFIG_HOME/tcw/config.yaml` when the environment variable
   `XDG_CONFIG_HOME` holds an absolute path, and otherwise
   `~/.config/tcw/config.yaml`. It needs no `tcw-version` line.
4. **`.tcw/tcw-config.local.yaml`**, beside the team's file, which applies to
   this project only. Like every `tcw-*.yaml` file, it starts with
   `tcw-version: 4.0.0`.
5. **Override variables**, environment variables that each set one key of
   one project (below).

`.tcw/tcw-config.local.yaml` is kept out of version control: `tcw project new`
writes a `.tcw/.gitignore` holding `/tcw-config.local.yaml`, and
`tcw validate` warns when the file is tracked anyway. A linked
git worktree of the project (a second working folder of the same repository)
has no copy of the file, since it is never shared; TCW then reads the main
checkout's copy, unless a copy has been placed in that second folder, which is
read instead.

The project's own personal file may also add to its `children`, which no
other personal layer can (`projects.md` has the rule). The user-wide file and
the variables apply to the project a command runs as, and from each of its
parents TCW reads only the keys that parent passes down; the guide
[Configuration](../../../docs/guide/configuration.md) in the TCW repository
says which.

## Turning personal configuration off: `TCW_NO_PERSONAL_CONFIG`

Setting the environment variable `TCW_NO_PERSONAL_CONFIG=1` skips the
user-wide file, `.tcw/tcw-config.local.yaml` and every override variable,
which helps when checking what the team's configuration does on its own. Any
other value stops every command with exit code 1:

```text
tcw work list: TCW_NO_PERSONAL_CONFIG must be 1, to skip personal configuration, or unset; got '2'
```

## How the layers merge

- **Mappings merge key by key.** A personal file that sets
  `work.stages.spec.prompt` leaves every other stage, and every other key of
  `spec`, as the team set it.
- **A list of bindings is replaced, not added to.** A stage's `prompt`,
  `pre` and `post` lists, and a procedure's list, are replaced by a layer
  that sets them, unless that layer's list holds the entry `- inherit: true`,
  which stands for the list the layer below resolved, at that position. A
  list holds at most one such entry, with no other key beside it. The rules
  for each list are in `work.md`.
- **A personal `post` list replaces the team's `post` hooks for that stage**
  unless it holds `inherit: true`. So one person can drop a team hook for
  themselves, and someone adding a hook of their own writes `- inherit: true`
  in the list to keep the team's as well.
- **`pre` hooks are shared.** A personal file cannot change them, so the
  team's checks always run.
- **`null` in a personal file is an error**
  (`user.name: null has no meaning in a personal file; remove the key instead`):
  to leave a key unset, remove it.
- The Jira credential names (`work.jira.credentials.*`) are used only in a
  project whose backend is Jira; in any other project a personal value is set
  aside, and `tcw project config --origin` lists it on a `# skipped:` line.

```yaml
# .tcw/tcw-config.local.yaml
tcw-version: 4.0.0
work:
    stages:
        spec:
            prompt:
                - blob: Read the team notes first.
                - inherit: true
```

## Override variables

A variable named `TCW_<KEY>__<PROJECT>` sets one key of the allowed list for
one project, on this machine only. The name is `TCW_`, then the key's parts
joined by `_`, then `__`, then the project ID, all in capitals, with each `-`
written `_`:

- `TCW_USER_NAME__APP` sets `user.name` in project `app`;
- `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ` sets
  `work.jira.credentials.email-env` in project `my-proj`;
- `TCW_WORK_STAGES_SPEC_PROMPT__APP` sets `work.stages.spec.prompt` in
  project `app`.

The variables are read after `.tcw/tcw-config.local.yaml`, so a variable wins
over both personal files.

- **Values are read by the key's kind.** A key that takes text, such as
  `user.name`, takes the value as written, so `no` and `null` are text. Any
  other key's value is read as YAML: a list, such as
  `[{blob: Read the notes.}, {inherit: true}]`, a mapping, a number, or
  `true` or `false`. `null` is refused: unset the variable instead.
- **A variable may name a mapping**, such as `TCW_USER__APP='{name: Pat}'`,
  which merges key by key like a file. When two variables set the same key,
  the more specific one wins: `TCW_WORK_STAGES_SPEC_PROMPT__APP` over the
  `prompt` inside `TCW_WORK_STAGES_SPEC__APP`.
- **Only the allowed list.** A variable naming a shared key stops every
  command with exit code 1, as does a name that is not of this form or names
  no key:

    ```text
    tcw work list: TCW_WORK_JIRA_SITE__APP: work.jira.site is a shared key; an environment variable cannot set it
    ```

    No message shows a variable's value.

- A variable that sets a key of the allowed list for a project the command
  does not read changes nothing; one naming a shared key is refused whatever
  project it names.
- `TCW_PROJECT_<ID>`, which says where a project is, is not an override
  variable; `projects.md` describes it.

## Your name

### `user.name`

Personal only: only personal configuration may set it.

The name TCW uses for you in a filesystem-mode project: what `--assign-me`
writes as an item's assignee and what `--mine` matches. It must be a
non-blank string with no space at either end, and it is matched exactly. Set
it in the user-wide file so it applies everywhere:

```yaml
# ~/.config/tcw/config.yaml
user:
    name: Sam Lee
```

`user` in `.tcw/tcw-config.yaml` is an error, since a name is not the team's
to set. In a Jira-mode project, you are the Jira account the credentials
belong to. A command that needs to know who you are, and cannot, stops with
exit code 1 and this message (the first path is your own user-wide file):

```text
no identity is configured: set `user.name` in ~/.config/tcw/config.yaml or in .tcw/tcw-config.local.yaml, or, in a Jira project, set the environment variables named by `work.jira.credentials`
```

## Seeing the result

`tcw project config` prints the configuration commands actually use, every
layer merged, as YAML. With `--origin`, a comment after each value names the
project that declared it and the layer it came from, and a line at the end
names each personal value that was not used, and why. This excerpt is from a
project `demo` whose team file adds a `post` hook to `spec`, with the
user-wide file setting `user.name` and the local file holding the `prompt`
shown above and a `token-env` (the other stages and the procedures are left
out, and the user-wide file's path is shortened):

<!-- prettier-ignore -->
```yaml
work:
  backend: filesystem  # built-in
  hooks:
    timeout: 300  # built-in
    output-cap: 65536  # built-in
  stages:
    spec:
      prompt:
        - blob: Read the team notes first.  # demo, local .tcw/tcw-config.local.yaml
        - builtin: true  # built-in, tcw/work/prompts/spec.md
      post:
        - command: echo team  # demo, project .tcw/tcw-config.yaml
id: demo  # demo, project .tcw/tcw-config.yaml
user:
  name: Sam  # demo, user ~/.config/tcw/config.yaml
# skipped: work.jira.credentials.token-env: (value not shown) (Jira credential names apply only in a Jira-mode project, .tcw/tcw-config.local.yaml)
```

A value set by an override variable names it, as in
`name: Sam Example  # demo, environment TCW_USER_NAME__DEMO`, and one a
parent passed down names that parent and its file. The built-in entry stands
for TCW's own text, and its comment names the packaged file that holds it. It
is how `tcw project config` prints that text; a configuration file never
writes it, and one that does is reported. To keep TCW's own text in a list,
write `- inherit: true`.

## Who may set each key

Every configuration key path, with who may set it. `*` stands for a name the
project chooses: a stage or a procedure. A key that TCW adds later is shared
unless it is added to the allowed list.

| Key path                          | Who may set it | Described in                                      |
| --------------------------------- | -------------- | ------------------------------------------------- |
| `id`                              | Shared         | [`projects.md`](projects.md#id)                   |
| `parents`                         | Shared         | [`projects.md`](projects.md#parents)              |
| `children`                        | Shared         | [`projects.md`](projects.md#children)             |
| `user.name`                       | Personal only  | [`personal.md`](#username)                        |
| `taxonomy.path`                   | Shared         | [`stores.md`](stores.md#taxonomypath)             |
| `taxonomy.repository`             | Shared         | [`stores.md`](stores.md#taxonomyrepository)       |
| `capabilities.path`               | Shared         | [`stores.md`](stores.md#capabilitiespath)         |
| `capabilities.repository`         | Shared         | [`stores.md`](stores.md#capabilitiesrepository)   |
| `work.path`                       | Shared         | [`work.md`](work.md#workpath)                     |
| `work.repository`                 | Shared         | [`work.md`](work.md#workrepository)               |
| `work.backend`                    | Shared         | [`work.md`](work.md#workbackend)                  |
| `work.tags`                       | Shared         | [`work.md`](work.md#worktags)                     |
| `work.documentation`              | Shared         | [`docs-sync.md`](docs-sync.md#workdocumentation)  |
| `work.procedures.*`               | Overridable    | [`work.md`](work.md#workprocedures)               |
| `work.stages.*.enabled`           | Shared         | [`work.md`](work.md#workstagesenabled)            |
| `work.stages.*.status`            | Shared         | [`work.md`](work.md#workstagesstatus)             |
| `work.stages.*.prompt`            | Overridable    | [`work.md`](work.md#workstagesprompt)             |
| `work.stages.*.pre`               | Shared         | [`work.md`](work.md#workstagespre)                |
| `work.stages.*.post`              | Overridable    | [`work.md`](work.md#workstagespost)               |
| `work.hooks.timeout`              | Shared         | [`work.md`](work.md#workhookstimeout)             |
| `work.hooks.output-cap`           | Shared         | [`work.md`](work.md#workhooksoutput-cap)          |
| `work.jira.site`                  | Shared         | [`jira.md`](jira.md#workjirasite)                 |
| `work.jira.project`               | Shared         | [`jira.md`](jira.md#workjiraproject)              |
| `work.jira.issue-type`            | Shared         | [`jira.md`](jira.md#workjiraissue-type)           |
| `work.jira.inbox-query`           | Shared         | [`jira.md`](jira.md#workjirainbox-query)          |
| `work.jira.timeout`               | Shared         | [`jira.md`](jira.md#workjiratimeout)              |
| `work.jira.priorities`            | Shared         | [`jira.md`](jira.md#workjirapriorities)           |
| `work.jira.credentials.email-env` | Overridable    | [`jira.md`](jira.md#workjiracredentialsemail-env) |
| `work.jira.credentials.token-env` | Overridable    | [`jira.md`](jira.md#workjiracredentialstoken-env) |
| `work.jira.fields.project`        | Shared         | [`jira.md`](jira.md#workjirafieldsproject)        |
| `work.jira.fields.item`           | Shared         | [`jira.md`](jira.md#workjirafieldsitem)           |
| `work.jira.fields.effort`         | Shared         | [`jira.md`](jira.md#workjirafieldseffort)         |
| `work.jira.fields.complexity`     | Shared         | [`jira.md`](jira.md#workjirafieldscomplexity)     |

`children` is shared, with the one exception that the project's own
`.tcw/tcw-config.local.yaml` may add to it.
