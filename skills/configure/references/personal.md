# Personal configuration

**Personal configuration** is settings that belong to one person rather than
to the team: their name, the variables holding their Jira credentials, and
their own additions to a stage's instructions or hooks. It lives in files that
are never shared, and it may set only the keys the table at the end of this
document marks `Overridable` or `Personal only`. Everything else is
**shared**: the team sets it in `tcw-config.yaml`, and a personal file that
tries to set it is reported and ignored.

## The layers, in order

A command reads its project's configuration from four layers, lowest first. A
higher layer wins.

1. **TCW's own defaults** (shown as `built-in`).
2. **`tcw-config.yaml`**, the team's file, in the project's root folder.
3. **The user-wide file**, which applies to every project this person works
   in: `$XDG_CONFIG_HOME/tcw/config.yaml` when the environment variable
   `XDG_CONFIG_HOME` holds an absolute path, and otherwise
   `~/.config/tcw/config.yaml`.
4. **`tcw-config.local.yaml`**, beside `tcw-config.yaml`, which applies to
   this project only.

`tcw-config.local.yaml` is kept out of version control: `tcw project new` adds a
`/tcw-config.local.yaml` line to the project's `.gitignore`, and
`tcw validate` warns when the file is tracked. For the same reason, a linked
git worktree of the project (a second working folder of the same repository)
has no `tcw-config.local.yaml` of its own; copy the file there to use the same
settings.

Personal files apply only to the project a command acts on. Another project
the command reads, such as an upstream project or the project an item is
created in, is read from its own `tcw-config.yaml` alone.

Setting the environment variable `TCW_NO_PERSONAL_CONFIG=1` skips both
personal files, which helps when checking what the team's configuration does
on its own. Any other non-empty value is reported, and the personal files are
then not read either.

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
- A value of `null` in a personal file is reported: to leave a key unset,
  remove it.
- The Jira credential names (`work.jira.credentials.*`) are used only in a
  project whose backend is Jira; in any other project a personal value is set
  aside, and `tcw project config --origin` lists it.

```yaml
# tcw-config.local.yaml
work:
    stages:
        spec:
            prompt:
                - blob: Read the team notes first.
                - inherit: true
```

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

`user` in `tcw-config.yaml` is reported, since a name is not the team's to
set. In a Jira-mode project, you are the Jira account the credentials belong
to. A command that needs to know who you are, and cannot, stops with exit
code 1 and this message:

```
no identity is configured: set `user.name` in ~/.config/tcw/config.yaml or in tcw-config.local.yaml, or, in a Jira project, set the environment variables named by `work.jira.credentials`
```

## Seeing the result

`tcw project config` prints the configuration commands actually use, every layer
merged, as YAML. With `--origin`, a comment after each value names the layer
it came from, and a block at the end lists what a personal file set that was
not used, and why. This excerpt is from a project whose team file adds a
`post` hook to `spec`, with the user-wide file setting `user.name` and the
local file shown above (the other stages and the procedures are left out, and
the user-wide file's path is shortened):

```yaml
work:
  backend: filesystem  # built-in
  hooks:
    timeout: 300  # built-in
    output-cap: 65536  # built-in
  stages:
    spec:
      prompt:
        - blob: Read the team notes first.  # local: tcw-config.local.yaml
        - builtin: true  # built-in, tcw/work/prompts/spec.md
      post:
        - command: echo team  # project
id: demo  # project
user:
  name: Sam  # user: ~/.config/tcw/config.yaml
```

The built-in entry stands for TCW's own text, and its comment names the
packaged file that holds it. It is how `config show` prints that text; a
configuration file never writes it, and one that does is reported. To keep
TCW's own text in a list, write `- inherit: true`.

## Who may set each key

Every configuration key path, with who may set it. `*` stands for a name the
project chooses: a stage, a procedure or a project ID. A key that TCW adds
later is shared unless it is added to the personal list.

| Key path | Who may set it | Described in |
| --- | --- | --- |
| `id` | Shared | [`projects.md`](projects.md#id) |
| `user.name` | Personal only | [`personal.md`](#username) |
| `taxonomy.path` | Shared | [`stores.md`](stores.md#taxonomypath) |
| `taxonomy.repository` | Shared | [`stores.md`](stores.md#taxonomyrepository) |
| `capabilities.path` | Shared | [`stores.md`](stores.md#capabilitiespath) |
| `capabilities.repository` | Shared | [`stores.md`](stores.md#capabilitiesrepository) |
| `work.path` | Shared | [`work.md`](work.md#workpath) |
| `work.repository` | Shared | [`work.md`](work.md#workrepository) |
| `work.backend` | Shared | [`work.md`](work.md#workbackend) |
| `work.tags` | Shared | [`work.md`](work.md#worktags) |
| `work.documentation` | Shared | [`docs-sync.md`](docs-sync.md#workdocumentation) |
| `work.procedures.*` | Overridable | [`work.md`](work.md#workprocedures) |
| `work.stages.*.enabled` | Shared | [`work.md`](work.md#workstagesenabled) |
| `work.stages.*.status` | Shared | [`work.md`](work.md#workstagesstatus) |
| `work.stages.*.prompt` | Overridable | [`work.md`](work.md#workstagesprompt) |
| `work.stages.*.pre` | Shared | [`work.md`](work.md#workstagespre) |
| `work.stages.*.post` | Overridable | [`work.md`](work.md#workstagespost) |
| `work.hooks.timeout` | Shared | [`work.md`](work.md#workhookstimeout) |
| `work.hooks.output-cap` | Shared | [`work.md`](work.md#workhooksoutput-cap) |
| `work.jira.site` | Shared | [`jira.md`](jira.md#workjirasite) |
| `work.jira.project` | Shared | [`jira.md`](jira.md#workjiraproject) |
| `work.jira.issue-type` | Shared | [`jira.md`](jira.md#workjiraissue-type) |
| `work.jira.inbox-query` | Shared | [`jira.md`](jira.md#workjirainbox-query) |
| `work.jira.timeout` | Shared | [`jira.md`](jira.md#workjiratimeout) |
| `work.jira.priorities` | Shared | [`jira.md`](jira.md#workjirapriorities) |
| `work.jira.credentials.email-env` | Overridable | [`jira.md`](jira.md#workjiracredentialsemail-env) |
| `work.jira.credentials.token-env` | Overridable | [`jira.md`](jira.md#workjiracredentialstoken-env) |
| `work.jira.fields.project` | Shared | [`jira.md`](jira.md#workjirafieldsproject) |
| `work.jira.fields.item` | Shared | [`jira.md`](jira.md#workjirafieldsitem) |
| `work.jira.fields.effort` | Shared | [`jira.md`](jira.md#workjirafieldseffort) |
| `work.jira.fields.complexity` | Shared | [`jira.md`](jira.md#workjirafieldscomplexity) |
| `projects.parent.*.path` | Shared | [`projects.md`](projects.md#projectsparentpath) |
| `projects.parent.*.repository` | Shared | [`projects.md`](projects.md#projectsparentrepository) |
| `projects.children.*.path` | Shared | [`projects.md`](projects.md#projectschildrenpath) |
| `projects.children.*.repository` | Shared | [`projects.md`](projects.md#projectschildrenrepository) |
| `projects.upstream.*.path` | Shared | [`projects.md`](projects.md#projectsupstreampath) |
| `projects.upstream.*.repository` | Shared | [`projects.md`](projects.md#projectsupstreamrepository) |
| `projects.parent.*.jira.site` | Shared | [`projects.md`](projects.md#projectsparentjirasite) |
| `projects.parent.*.jira.project` | Shared | [`projects.md`](projects.md#projectsparentjiraproject) |
| `projects.parent.*.jira.inbox-status` | Shared | [`projects.md`](projects.md#projectsparentjirainbox-status) |
| `projects.parent.*.jira.credentials.email-env` | Shared | [`projects.md`](projects.md#projectsparentjiracredentialsemail-env) |
| `projects.parent.*.jira.credentials.token-env` | Shared | [`projects.md`](projects.md#projectsparentjiracredentialstoken-env) |
| `projects.parent.*.jira.fields.project` | Shared | [`projects.md`](projects.md#projectsparentjirafieldsproject) |
| `projects.children.*.jira.site` | Shared | [`projects.md`](projects.md#projectschildrenjirasite) |
| `projects.children.*.jira.project` | Shared | [`projects.md`](projects.md#projectschildrenjiraproject) |
| `projects.children.*.jira.inbox-status` | Shared | [`projects.md`](projects.md#projectschildrenjirainbox-status) |
| `projects.children.*.jira.credentials.email-env` | Shared | [`projects.md`](projects.md#projectschildrenjiracredentialsemail-env) |
| `projects.children.*.jira.credentials.token-env` | Shared | [`projects.md`](projects.md#projectschildrenjiracredentialstoken-env) |
| `projects.children.*.jira.fields.project` | Shared | [`projects.md`](projects.md#projectschildrenjirafieldsproject) |
| `projects.upstream.*.jira.site` | Shared | [`projects.md`](projects.md#projectsupstreamjirasite) |
| `projects.upstream.*.jira.project` | Shared | [`projects.md`](projects.md#projectsupstreamjiraproject) |
| `projects.upstream.*.jira.inbox-status` | Shared | [`projects.md`](projects.md#projectsupstreamjirainbox-status) |
| `projects.upstream.*.jira.credentials.email-env` | Shared | [`projects.md`](projects.md#projectsupstreamjiracredentialsemail-env) |
| `projects.upstream.*.jira.credentials.token-env` | Shared | [`projects.md`](projects.md#projectsupstreamjiracredentialstoken-env) |
| `projects.upstream.*.jira.fields.project` | Shared | [`projects.md`](projects.md#projectsupstreamjirafieldsproject) |
