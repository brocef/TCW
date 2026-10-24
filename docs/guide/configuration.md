# Configuration

A project's configuration is the file `.tcw/tcw-config.yaml`: its ID, its
parent links, where its stores live, its tags, how its stages behave, and its
documentation entries. It is a file in your own repository, trusted exactly as
much as any other file there: the commands it names run with your
permissions. This is not a sandbox.

This guide explains how the parts fit together, with short examples. Every key
is described once, with its exact rules, in the `configure` skill's reference
documents, which this guide links to:

- [`work.md`](../../skills/configure/references/work.md): stages, bindings,
  hooks, procedures and tags;
- [`jira.md`](../../skills/configure/references/jira.md): the Jira backend;
- [`stores.md`](../../skills/configure/references/stores.md): where stores live;
- [`projects.md`](../../skills/configure/references/projects.md): the
  project's ID, its parent links and its children;
- [`docs-sync.md`](../../skills/configure/references/docs-sync.md):
  documentation entries;
- [`personal.md`](../../skills/configure/references/personal.md): personal
  configuration, environment overrides, and one table of every key with who
  may set it.

See also [The Work component](work.md) and [Related projects](multi-repo.md).
After any change, run `tcw validate`; `tcw project config --origin` prints the
configuration commands actually use, and where each value came from.

## The `.tcw/` folder

A **project** is a folder holding `.tcw/tcw-config.yaml`; that folder is the
project's root. The place is fixed: no setting moves
`.tcw/`, and every path the configuration holds is read from the project's
root, not from `.tcw/`. `tcw project new` creates the folder. It can hold:

- `.tcw/tcw-config.yaml`, the project's shared file, committed with the
  project, which everyone working on it reads;
- `.tcw/tcw-config.local.yaml`, your **personal file** for this project,
  holding settings that are yours alone (see [Layers](#layers-the-projects-file-and-your-own));
- `.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml`, which say
  where other projects are on this machine, shared and personal. They are
  described in [Related projects](multi-repo.md);
- `.tcw/.gitignore`, which `tcw project new` writes so that the two personal
  files, `/tcw-config.local.yaml` and `/tcw-manifest.local.yaml`, are never
  committed.

A 3.x project keeps its configuration in a `tcw-config.yaml` at its root and
has no `.tcw/` folder. TCW 4.0 refuses to work in it, naming `tcw migrate`,
which converts the project in place:

```text
tcw work list: <folder> is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4
```

The [migration guide](../migration-guide-3.X-to-4.0.0.md) explains what
`tcw migrate` changes and how to run it.

## Every file says its format: `tcw-version`

Every `tcw-*.yaml` file TCW writes starts with a `tcw-version` line: the
shared and personal files, the manifests, and the file each object keeps in
its folder, such as a work item's `tcw-work-item.yaml`. It names the version
of TCW that created the file or last converted it, so a reader knows which
format the file follows:

```yaml
tcw-version: 4.0.0
id: app
```

A file with no `tcw-version` is read as a TCW 3.x file. A command that reads
such a file stops and says what to do, as does one that reads a file written
by a newer TCW:

```text
.tcw/tcw-config.local.yaml: has no tcw-version: add 'tcw-version: 4.0.0' as its first line, or, for a TCW 3.x file, run 'tcw migrate' in this project
.tcw/tcw-config.yaml: was written by TCW 4.9 (tcw-version 4.9.0), newer than this TCW (4.0.0); upgrade TCW
```

Converting a file to a newer format is called **migration**; `tcw migrate`
migrates a whole project, its files and its Jira tickets. Only the major and
minor numbers of `tcw-version` matter: a patch release never changes a
format. Your user-wide file (below) is not a `tcw-*.yaml` file and needs no
`tcw-version`.

Every key follows one naming rule: lowercase letters and digits joined by
single hyphens, and a key that breaks it is refused, naming the file and the
key. So a binding's condition is written `not-tags`. A 3.x file writes it
`not_tags`, which 4.0 refuses with `write 'not-tags'` and `tcw migrate`
renames.

## Layers: the project's file and your own

A command reads its project's configuration in **layers**, each a source of
settings that overrides the one before it:

1. TCW's own defaults (shown as `built-in`);
2. the project's shared file, `.tcw/tcw-config.yaml`;
3. your **user-wide file**, which applies to every project you work in:
   `$XDG_CONFIG_HOME/tcw/config.yaml` when that variable holds an absolute
   path, and otherwise `~/.config/tcw/config.yaml`;
4. your personal file for this project, `.tcw/tcw-config.local.yaml`;
5. environment variables that override one key of one project (below).

Your files and the variables may set only a few keys: your name, the names of
the variables holding your Jira credentials, a stage's `prompt` and `post`
lists, and procedures; the project's personal file may also add to its
`children`. That set is the **allowed list**, and a personal value for any
other key is refused with an error naming the file or variable. A personal `post` list for
a stage **replaces** the project's `post` hooks for that stage unless it holds
`inherit: true`, so you can drop a hook for yourself; `pre` hooks are shared,
so the project's checks always run. The merge rules and the full table of the
allowed list are in
[`personal.md`](../../skills/configure/references/personal.md).

**Environment overrides.** A variable named `TCW_<KEY>__<PROJECT>` sets one
key of the allowed list for one project, such as `TCW_USER_NAME__APP` for
`user.name` in project `app`, and `TCW_NO_PERSONAL_CONFIG=1` turns off both
personal files and every such variable; the name rule, how values are read,
and the examples are in
[`personal.md`](../../skills/configure/references/personal.md), and what a
3.x project's credential variable names need is in the
[migration guide](../migration-guide-3.X-to-4.0.0.md).

## What a project takes from its parents

A **parent link** is an entry in a project's `parents:` list naming another
project it takes things from; the project is that parent's **child**. Each
link's `inherit` says what it passes: `taxonomy`, `capabilities`, `config`,
any list of them, `all` (the default) or `none`. Parent links, children and
how TCW finds a parent on this machine are described in
[Related projects](multi-repo.md).

A link that passes `config` passes exactly these **inherited keys**:

- `work.tags`, the tags the project may apply;
- `work.jira`, with every key under it, which a project takes only when its
  own `work.backend` is `jira`.

Everything else is each project's own. In particular **`work.backend` is
never inherited**: a project that keeps its items in Jira says
`work.backend: jira` in its own file, and takes the rest of `work.jira` from
its parent. Stages, hooks, procedures, documentation entries and store
locations never cross a parent link either.

The parents come first: TCW reads each parent's layers, farthest first, then
the project's own five layers in the order above, so a value the project sets
itself wins. From a parent it takes only the inherited keys: from its shared
file, from its personal file (the Jira credential names), and from your
user-wide file and the variables naming that parent. A child of this project
in turn receives the inherited keys as this project's layers left them.
Mappings merge key by key, so a child can take `work.jira.site` from its
parent and set its own `work.jira.project`; a list or a single value set by a
later project replaces the earlier one whole. `tcw project config --origin`
shows which project each value came from:

```text
work:
  backend: jira  # app, project .tcw/tcw-config.yaml
  tags:
    - security  # lib, project <parent folder>/lib/.tcw/tcw-config.yaml
  jira:
    site: "https://example.atlassian.net"  # lib, project <parent folder>/lib/.tcw/tcw-config.yaml
    project: APP  # app, project .tcw/tcw-config.yaml
```

Each comment has one shape: the project that declared the value, then the
layer (`project`, `user` or `local`) and its file, as in
`# app, local .tcw/tcw-config.local.yaml`; or the project and the variable,
as in `# app, environment TCW_USER_NAME__APP`; or `# built-in`, followed by
TCW's own file for a built-in text. A file inside the project is named from
its root, and one outside it by its whole path. After the values, a
`# skipped:` or `# refused:` line names each personal value that was not
used, and why. With `--origin` the command prints even when one of the
project's own files has a problem, so you can find the line to fix, and still
exits 1. A setting a parent cannot give, because it is missing or broken
(below), stops it with nothing printed.

Two forms change what is inherited:

- **`inherit: true` in `work.tags`** stands for the tags the parents passed,
  at that position, so a child adds to them instead of replacing them.
  `tcw work tags add` in a child that has no `work.tags` of its own writes
  that entry first:

    ```yaml
    # .tcw/tcw-config.yaml in a child of lib
    work:
        tags:
            - inherit: true
            - mobile
    ```

- **`null` removes an inherited value.** In a project's shared file,
  `work.tags: null`, or `null` at any key under `work.jira`, means the key has
  no value from any parent; where TCW has a default for that key, the default
  applies. `null` in a personal file is refused.

## When a parent is not on this machine

A parent that passes `config` may not be on this machine, for example in a
fresh clone of a child. A command stops only when it reads a setting that
missing parent could have given and that no later project decides; it exits
with code 7, before it writes anything or contacts Jira, and names the key and
the parent:

```text
tcw work tags list: 'app' inherits its configuration (work.tags) from project 'lib', which is not on this machine: <folder>/.tcw/tcw-manifest.yaml places it at <parent folder>/lib, from https://example.com/lib.git; fetch it with 'tcw project provision lib'
```

There are two remedies:

- **fetch the parent**: `tcw project provision lib` when a manifest entry says
  where it comes from, as the message says, or add it to a manifest when it is
  already on this machine somewhere TCW does not look;
- **leave `config` out of that link's `inherit`**, such as
  `inherit: [taxonomy, capabilities]`, when the project should not take its
  configuration from that parent; it then sets its own `work.tags` and
  `work.jira`.

A project that sets `work.tags` itself, without `inherit: true`, has decided
its tags whatever its parents' state. What still works with a parent missing
depends on where the project keeps its items:

- **A filesystem project** lists, reads, creates, changes and moves its own
  items as usual. Only a command that applies, checks or lists tags stops:
  `tcw work tags list`, `tcw work tags add` and `tcw work tags rm`,
  `tcw work list --tag`, and `tcw work new` or `tcw work edit` given `--tag`.
- **A Jira-mode project whose link to the missing parent passes `config`**
  cannot open its work store at all, even when it sets some `work.jira` keys
  itself, since the parent could set any of the others. `tcw work list`,
  `tcw work show`, `tcw work advance`, `tcw work stage prompt` given an item
  and `tcw project config` all exit 7.

In either kind of project, five commands never stop on a missing parent,
because they read nothing it could give: `tcw work path`, `tcw work lifecycle`,
`tcw work docs`, and `tcw work stage prompt` and `tcw work procedure` given no
item. `tcw validate` never stops on it either: it reports the parent as
unresolved and exits 0.

## Whose problem a mistake is

A mistake is reported to whoever can fix it:

- **In your user-wide file**, it is your own: it is reported once, as an
  error, in every project you run a command in, and the command stops
  (exit 1).
- **In a parent's shared file**, it is that parent's. In a child, only a
  command that reads the broken inherited value stops, with exit 1 and the
  parent's file and key named; other commands run as usual. `tcw validate` in
  a child reports the broken inherited value as a warning at the parent's
  file, and fails only in the parent, where it is an error:

    ```text
    warning: <parent folder>/lib/.tcw/tcw-config.yaml: work.tags[1]: 12 is not a tag
    ```

- **In a child's file that cannot be read**, it is an error in the project
  that lists that child under `children:`.

## Stages and their bindings

Every work item moves through the same table of stages (`tcw work lifecycle`
prints it). Under `work.stages.<stage>`, a project can turn optional stages
off and attach three lists to a stage:

- `prompt`: the text `tcw work stage prompt <stage>` prints, the instructions
  an agent reads before working the stage;
- `pre`: checks that must pass before an item moves into the stage;
- `post`: what runs after an item has moved into the stage.

Each entry of those lists is a **binding**, a mapping naming one kind:

```yaml
work:
    stages:
        spec:
            prompt:
                - inherit: true
                - blob: "In this repository, specs name the options they rejected."
                - file: docs/lifecycle/spec-for-bugs.md
                  when: { tags: [bug] }
                - generate: ./bin/spec-notes.sh
        implement:
            pre:
                - command: test -f docs/plan-approved
        completed:
            post:
                - command: sh scripts/notify-team.sh
                - skill: release-notes
```

- `blob:` is text written in place; `file:` reads a file, relative to the
  project's root when the declaring file is in `.tcw/`, and otherwise to the
  folder of the file that declares it; `generate:` runs a script whose output
  is the text; `skill:` names an agent skill; `command:` runs a shell command,
  in a `pre` or `post` list only. Which kinds each list accepts is a table in
  [`work.md`](../../skills/configure/references/work.md#binding-kinds).
- `when:` limits a binding to items carrying any of its `tags` and none of its
  `not-tags`.
- `inherit: true` keeps the list from the layer below at that position. In
  `.tcw/tcw-config.yaml` that is TCW's own text for the stage, so a `prompt`
  list without it **replaces** TCW's instructions instead of adding to them.
  These lists are each project's own: a parent's stages never reach its
  children.

A `skill:` in a `post` list is reported for the agent to run, never run by
TCW. A `skill:` in a `pre` list is refused: a check that is only reported would
always pass.

**Procedures** are TCW's instructions that are not stages, such as
`documentation-sync` and `search`; `tcw work procedure <id>` prints one.
`work.procedures.<id>` takes the same text bindings as a stage's `prompt`,
composed the same way; the ids are listed in
[`work.md`](../../skills/configure/references/work.md#workprocedures).

## How hooks run

A **hook** is a `command` binding in a `pre` or `post` list.
`tcw work advance` runs them when it moves an item:

- **`pre` hooks run only for the target stage**, after TCW's own checks for
  that stage, in the order written.
- **A failing `pre` hook refuses the move** (exit code 3), unless the move is
  forced with `--force` and `--reason`, which runs every check, moves anyway,
  and records what failed in the trace comment.
- **`pre` hooks may run again for the same move.** `--dry-run` runs them, and
  in Jira mode the Jira workflow can refuse a move after they ran, so the next
  attempt runs them again. Write them so that running twice does no harm.
- **`post` hooks run after the move.** A failure keeps the move, stops the
  remaining `post` hooks, names the file that declared the failed one, and
  makes `advance` exit with code 6.
- **They run from the project's root folder**, through the shell, with no
  input; what they print goes to TCW's standard error.
- **They get these environment variables:** `TCW_SLUG` (the item's **full
  identifier**, its project, component and folder, such as
  `app.work/2026-10-24-add-login`; "slug" is a nickname for the full
  identifier), `TCW_STAGE` (the stage being moved into),
  `TCW_FROM_STAGE`, `TCW_ITEM_PATH` (the item's folder), `TCW_PROJECT_ROOT`,
  `TCW_CONFIG_DIR` (the folder a `file:` binding in the declaring file is read
  from, so the project's root for a file in `.tcw/`), and, on a
  forced move, `TCW_FORCED` and `TCW_REASON`.
- **A `generate:` script gets the same variables**, except that `TCW_STAGE`
  is the stage whose prompt is being composed and `TCW_FROM_STAGE`,
  `TCW_FORCED` and `TCW_REASON` are absent, plus `TCW_HOOK_ROLE`,
  `TCW_HOOK_KIND`, `TCW_HOOK_ID` and `TCW_HOOK_PHASE`. On standard input it
  reads one JSON object, `{"schema": 2, "item": …, "request": …, "hook": {…}}`.
- **Text can carry the item's request.** The pair
  `{{tcw:request}}…{{/tcw:request}}` in any prompt text is replaced by the
  item's request, or by the text between the markers when there is none.
- **Each has limits:** a hook or script that runs longer than
  `work.hooks.timeout` (300 seconds by default) is stopped and fails, and a
  script that prints more than `work.hooks.output-cap` (64 KiB by default)
  contributes nothing.

The full rules, with every variable and the stdin object, are in
[`work.md`](../../skills/configure/references/work.md#how-hooks-run).

## Declaring which documents track which changes

A project can list the documents that must move with its code, so the
lifecycle puts them in front of the agent instead of hoping it goes looking:

```yaml
# .tcw/tcw-config.yaml
work:
    documentation:
        - path: README.md
          trigger: Public-API
          description: >-
              Public-facing overview and CLI usage. Update when the public
              surface or user-facing behavior changes.
        - path: docs/changelogs/upcoming/<folder>.md
          trigger: Any-Code-Change
          description: >-
              Developer changelog; technical, grouped by category. One file
              per work item, named after the item's folder name, never its
              full identifier, whose `/` would make a path.
```

Three keys per entry, all required. `tcw validate` checks their shape: a blank
field, an absolute path, a path that leaves the project, whitespace inside a
trigger, and the same path declared twice under the _same_ trigger. It
deliberately does **not** check that `path` exists (an entry routinely names a
file you intend to create, or a pattern such as
`docs/changelogs/upcoming/<folder>.md`, where each change adds its own file
named after its work item's folder) or that `trigger` is one of the common
names (the names are yours to extend).

One file may appear in several entries as long as their triggers differ, which
is how a large document whose sections answer to different changes is
expressed: a `README.md` entry under `Public-CLI-API` for its command
reference, and a second `README.md` entry under `Validation-Rules` for the
section listing what the validator rejects. Each trigger is evaluated on its
own, so a change that touches only one of them updates only that entry's
material.

`tcw work docs` prints them; `--json` adds `source`, which is `config` when you
have declared entries and `agent-guide` when you have not:

```sh
tcw work docs                          # path, trigger, and what to write
tcw work docs --json                   # {"schema", "source", "entries"}
```

`tcw work stage prompt plan` and `tcw work stage prompt implement` include the
entries inline, so checking the documentation is part of the stage's
instructions rather than a convention an agent has to remember. A project that
declares nothing gets the stages' own wording, and the `documentation-sync`
skill reads a `## Documentation Sync` section from the agent guide instead.
The rules are in
[`docs-sync.md`](../../skills/configure/references/docs-sync.md).

## Example: keeping git in step with each stage change (something your project adds)

TCW never changes git state: it writes an item's files and leaves recording
them to you. This example is one way a project can keep git in step with its
work items, using only a stage's `prompt` text and a `post` hook. It behaves
the same under Claude Code and Codex, and with either backend.

### The commit hook

The hook is a short script. TCW's repository ships it as
[`docs/guide/examples/commit-item-after-move.sh`](examples/commit-item-after-move.sh);
copy it into your own repository, for example as
`scripts/tcw-commit-item.sh`. It commits whatever is in the item's folder when
the hook runs, including a document that is only half written, so it suits a
project that moves an item on only when the stage's work is in the folder. An
item nested in the moved item's folder is left out: its files are committed
when that item is moved.

```sh
#!/bin/sh
# Commit this work item's files after TCW moves it to a new stage.
# An opt-in example: TCW itself never changes git state.
set -eu
cd "$TCW_ITEM_PATH"
# Items nested in this one's folder are theirs to commit, so each folder
# below holding tcw-work-item.yaml is left out. The search skips what TCW
# never looks in for items: hidden folders, resources/, comments/ and the
# stage folders, whose names are the stages of STAGES in tcw/work/model.py.
# A folder it cannot read stops the hook before anything is staged.
found=$(find . \( -type d ! -path . \( -name '.*' -o -name resources \
    -o -name comments -o -name inbox -o -name request -o -name spec \
    -o -name plan -o -name implement -o -name review -o -name qa \
    -o -name completed -o -name discarded -o -name postmortem \) -prune \) \
    -o \( -type f -name tcw-work-item.yaml ! -path ./tcw-work-item.yaml -print \))
set -- .
while IFS= read -r state; do
    if [ -n "$state" ]; then
        set -- "$@" ":(exclude)${state%/tcw-work-item.yaml}"
    fi
done <<FOUND
$found
FOUND
git add -A -- "$@"
if git diff --cached --quiet -- "$@"; then
    exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
fi
git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- "$@"
```

- **It works from the item's folder, `TCW_ITEM_PATH`**, not the project root
  that hooks start in. A work store kept in another repository has to be
  committed in that repository, and git finds the repository from the current
  folder, so changing to the item's folder first makes the script right in
  both layouts.
- **The commit message names the project as well as the item**, because
  `TCW_SLUG` is the item's full identifier, such as
  `app.work/2026-10-24-add-login`.
- **It commits only the item's folder.** `-- .` limits both the staging and the
  commit to that folder, so your other changes, staged or not, are left alone.
- **It succeeds without a commit when nothing in the folder changed**, which is
  the usual case in Jira mode, where a move changes the ticket rather than a
  file.

### The configuration

Pulling is **prompt text**, an instruction to the agent rather than a hook, so
a failed pull never blocks a move. The instruction pulls the project's own
checkout and, when the work store is kept in another repository, that
repository too, since the project's checkout does not contain it:

```yaml
work:
    stages:
        request:
            prompt: &pull-first
                - blob: >-
                      Before you start, bring this checkout up to date with
                      `git pull --ff-only`. If the folder that
                      `tcw work path <item>` prints is inside a different
                      git repository, also run
                      `git -C <that folder> pull --ff-only`. If either
                      pull fails, tell the user and carry on with what
                      you have.
                - inherit: true
            post: &commit-after-move
                - command: sh scripts/tcw-commit-item.sh
        spec: { prompt: *pull-first, post: *commit-after-move }
        plan: { prompt: *pull-first, post: *commit-after-move }
        implement: { prompt: *pull-first, post: *commit-after-move }
        review: { prompt: *pull-first, post: *commit-after-move }
        qa: { prompt: *pull-first, post: *commit-after-move }
        completed: { post: *commit-after-move }
        discarded: { post: *commit-after-move }
        postmortem: { prompt: *pull-first }
```

- `&pull-first` and `*pull-first` are a YAML **anchor** and **alias**: the
  list is written once, under `request`, and reused by name. TCW's own edits to
  `.tcw/tcw-config.yaml`, such as `tcw work tags add`, keep them intact, or
  refuse and say what to change by hand.
- `- inherit: true` keeps TCW's own instructions after the pull instruction.
  Without it, the stage would print only the pull instruction.
- `postmortem` has no `post`, because nothing ever moves into it.
- Leave out the lines for any stage your project has turned off.
- In Jira mode, each stage also carries its `status`, as
  [`jira.md`](../../skills/configure/references/jira.md#stages-and-statuses)
  describes.
- A work store kept in another repository is brought up to date **only** by
  this instruction, when an agent starts a stage. Nothing refreshes it between
  stages, and `tcw project provision` never updates a copy that already exists.

### Pushing, if you want it

Pushing is an optional second `post` entry:

```yaml
post: &commit-and-push
    - command: sh scripts/tcw-commit-item.sh
    - command: git -C "$TCW_ITEM_PATH" push --quiet
```

A failed push, for example when you are offline, makes `tcw work advance` exit
with code 6: the item has moved, the commit is local, and your next push
carries it.

### What the example does not do

- **It does not commit a new item when it is created.** Creating an item is
  not a move, so `tcw work new` runs no hooks,
  and a new item's folder stays uncommitted until the item's first move, when
  the example commits it along with that move's changes. Adopting a Jira
  ticket is different: `tcw work tickets adopt` runs the `request` stage's
  `post` hooks, so the example commits an adopted item's folder straight away.
- **It does not commit a rename in full.** `tcw work rename` is not a move
  either, so it runs no hooks. At the item's next move, the example commits
  the files in the item's new folder only, since it commits nothing outside
  that folder. The old folder's removal, and the `parent` and `blocked-by`
  lines the rename rewrote in other items, are left uncommitted, and until you
  commit them the repository's history holds both the old folder and the new
  one. Commit the rest of a rename yourself.
- **It does not get past your own git hooks.** A check your repository runs on
  every commit can fail the commit. That is a failed `post` hook: `advance`
  exits with code 6, and the move stands.

### Keeping it to yourself

`prompt` and `post` may be set in personal configuration, so one person can
put the same bindings in `.tcw/tcw-config.local.yaml` without changing
anything for the team. A personal `post` list replaces the team's `post` list for that
stage, so write `- inherit: true` in it to keep the team's hooks as well; `pre`
hooks cannot be changed personally:

```yaml
# .tcw/tcw-config.local.yaml
work:
    stages:
        plan:
            prompt:
                - blob: Before you start, run `git pull --ff-only`.
                - inherit: true
            post:
                - inherit: true
                - command: sh scripts/tcw-commit-item.sh
```

[`personal.md`](../../skills/configure/references/personal.md) has the rules
for personal files.
