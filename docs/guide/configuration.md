# Configuration

`tcw-config.yaml`, in the project's root folder, is the project's
configuration: its ID, where its stores live, the projects it is connected to,
its tags, how its stages behave, and its documentation entries. It is a file in
your own repository, trusted exactly as much as any other file there: the
commands it names run with your permissions. This is not a sandbox.

This guide explains how the parts fit together, with short examples. Every key
is described once, with its exact rules, in the `configure` skill's reference
documents, which this guide links to:

- [`work.md`](../../skills/configure/references/work.md): stages, bindings,
  hooks, procedures and tags;
- [`jira.md`](../../skills/configure/references/jira.md): the Jira backend;
- [`stores.md`](../../skills/configure/references/stores.md): where stores live;
- [`projects.md`](../../skills/configure/references/projects.md): connected
  projects and inheritance;
- [`docs-sync.md`](../../skills/configure/references/docs-sync.md):
  documentation entries;
- [`personal.md`](../../skills/configure/references/personal.md): personal
  configuration, and one table of every key with who may set it.

See also [The Work component](work.md) and
[Working across repositories](multi-repo.md). After any change, run
`tcw validate`; `tcw config show --origin` prints the configuration commands
actually use, and where each value came from.

## Layers: the team's file and your own

A command reads its configuration in layers, each overriding the one below:
TCW's own defaults, then `tcw-config.yaml` (the team's), then a user-wide file
of your own, then `tcw-config.local.yaml` beside `tcw-config.yaml`, which is
yours for this project and is never tracked. Your files may set only a few
keys: your name, the names of the variables holding your Jira credentials, a
stage's `prompt` and `post` lists, and procedures. A personal `post` list for a
stage **replaces** the team's `post` hooks for that stage unless it holds
`inherit: true`, so you can drop a team hook for yourself; `pre` hooks are
shared, so the team's checks always run. The layers, the merge rules and the
full table are in
[`personal.md`](../../skills/configure/references/personal.md).

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
  folder of the file that declares it; `generate:` runs a script whose output
  is the text; `skill:` names an agent skill; `command:` runs a shell command,
  in a `pre` or `post` list only. Which kinds each list accepts is a table in
  [`work.md`](../../skills/configure/references/work.md#binding-kinds).
- `when:` limits a binding to items carrying any of its `tags` and none of its
  `not_tags`.
- `inherit: true` keeps the list from the layer below at that position. In
  `tcw-config.yaml` that is TCW's own text for the stage, so a `prompt` list
  without it **replaces** TCW's instructions instead of adding to them.

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
- **They get these environment variables:** `TCW_SLUG` (the item's full slug,
  `project/folder`), `TCW_STAGE` (the stage being moved into),
  `TCW_FROM_STAGE`, `TCW_ITEM_PATH` (the item's folder), `TCW_PROJECT_ROOT`,
  `TCW_CONFIG_DIR` (the folder of the file that declared the hook), and, on a
  forced move, `TCW_FORCED` and `TCW_REASON`.
- **A `generate:` script gets the same variables**, except that `TCW_STAGE`
  is the stage whose prompt is being composed and `TCW_FROM_STAGE`,
  `TCW_FORCED` and `TCW_REASON` are absent, plus `TCW_HOOK_ROLE`,
  `TCW_HOOK_KIND`, `TCW_HOOK_ID` and `TCW_HOOK_PHASE`. On standard input it
  reads one JSON object, `{"schema": 1, "item": …, "request": …, "hook": {…}}`.
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
# tcw-config.yaml
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
              per work item, named after the item's folder name, never the
              full slug, whose `/` would make a path.
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
project that moves an item on only when the stage's work is in the folder.

```sh
#!/bin/sh
# Commit this work item's files after TCW moves it to a new stage.
# An opt-in example: TCW itself never changes git state.
set -eu
cd "$TCW_ITEM_PATH"
git add -A -- .
if git diff --cached --quiet -- .; then
    exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
fi
git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- .
```

- **It works from the item's folder, `TCW_ITEM_PATH`**, not the project root
  that hooks start in. A work store kept in another repository has to be
  committed in that repository, and git finds the repository from the current
  folder, so changing to the item's folder first makes the script right in
  both layouts.
- **The commit message names the project as well as the item**, because
  `TCW_SLUG` is the full slug, `project/folder`.
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
  `tcw-config.yaml`, such as `tcw work tags add`, keep them intact, or refuse
  and say what to change by hand.
- `- inherit: true` keeps TCW's own instructions after the pull instruction.
  Without it, the stage would print only the pull instruction.
- `postmortem` has no `post`, because nothing ever moves into it.
- Leave out the lines for any stage your project has turned off.
- In Jira mode, each stage also carries its `status`, as
  [`jira.md`](../../skills/configure/references/jira.md#stages-and-statuses)
  describes.
- A work store kept in another repository is brought up to date **only** by
  this instruction, when an agent starts a stage. Nothing refreshes it between
  stages, and `tcw provision` never updates a copy that already exists.

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
  not a move, so `tcw work new`, in this project or another, runs no hooks,
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
put the same bindings in `tcw-config.local.yaml` without changing anything for
the team. A personal `post` list replaces the team's `post` list for that
stage, so write `- inherit: true` in it to keep the team's hooks as well; `pre`
hooks cannot be changed personally:

```yaml
# tcw-config.local.yaml
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
