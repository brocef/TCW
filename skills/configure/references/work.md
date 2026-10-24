# Configure the work axis

Everything under `work:` in `tcw-config.yaml` is described here, except two
keys that have their own documents: the Jira connection, `work.jira`, is in
`jira.md`, and documentation entries, `work.documentation`, are in
`docs-sync.md`.

Each key below has its own heading, and the first line under the heading says
who may set it:

- **Shared** keys are the team's, set in `tcw-config.yaml` only.
- **Overridable** keys may also be set by one person in their personal
  configuration, a file that is never shared (see `personal.md`).

`tcw-config.yaml` is a file in the user's own repository, and TCW trusts it
exactly as much as any other file there: the commands it names run with the
user's permissions. This is not a sandbox.

After any change here, run `tcw validate`. It reports every key it does not
know, every value of the wrong shape, and which file each problem came from.
`tcw work lifecycle` then prints the stages and what is bound to each, and
`tcw project config --origin` prints the configuration every command actually
uses, with the layer each value came from.

## Where the work store lives

### `work.path`

Shared: personal configuration cannot set it.

The folder holding the work items, by default `docs/work` inside the project.
A relative path is read from the project's own folder; an absolute path and a
symbolic link are both accepted. The folder may be inside another repository.
Changing the path moves nothing: items already in the old folder stay there
and TCW does not read them. `stores.md` has the rules shared by all three stores.

```yaml
work:
    path: ../planning/docs/work/my-project
```

### `work.repository`

Shared: personal configuration cannot set it.

Where the work store comes from when it is not on this machine: a repository
`url`, and optionally `ref`, the `path` of the store inside the repository,
and a local `checkout` folder. `tcw project provision` makes the copy. A store that is
already here always wins. The block is the same for all three stores and is
described in `stores.md`.

## The backend

### `work.backend`

Shared: personal configuration cannot set it.

Where an item's properties, stage, request and comments are kept: `filesystem`
(the default) keeps them in files in the item's folder, and `jira` keeps them
on a Jira ticket. In both, the item's documents (stage documents, rounds,
handoffs and declared record changes) are files in the item's folder.

```yaml
work:
    backend: jira
```

With `jira`, `work.jira` is required and every enabled stage needs a `status`;
both are described in `jira.md`. Changing the backend moves no items: a
command reads only the backend that is configured.

## Tags

### `work.tags`

Shared: personal configuration cannot set it.

The tags this project has registered, as a list. An item may carry only
registered tags. Tags are compared in lower case, so `CLI` and `cli` are the
same tag. Add and remove them with `tcw work tags add <tag>` and
`tcw work tags rm <tag>`, which change only this list in `tcw-config.yaml`.

```yaml
work:
    tags: [auth, billing, docs]
```

## Stages

An item moves through a fixed table of stages: `inbox`, `request`, `spec`,
`plan`, `implement`, `review`, `qa`, then `completed` or `discarded`. One more
stage, `postmortem`, is a side stage: it is worked on beside a finished item,
and nothing ever moves into it. `tcw work lifecycle` prints the table. A
project cannot add a stage or rename one; it can turn some off, map them to
Jira statuses, and bind text and commands to each, under
`work.stages.<stage>`.

```yaml
work:
    stages:
        spec:
            enabled: false
        implement:
            prompt:
                - inherit: true
                - blob: Run the full test suite before you stop.
            pre:
                - command: test -f docs/plan-approved
        completed:
            post:
                - command: sh scripts/notify-team.sh
```

A side stage takes only `enabled` and `prompt`.

### `work.stages.*.enabled`

Shared: personal configuration cannot set it.

`true` or `false`, `true` by default. Only `spec`, `plan`, `review`, `qa` and
`postmortem` can be turned off; turning off any other stage is reported. A
turned-off stage is skipped when an item moves on, and an item cannot be moved
into it.

### `work.stages.*.status`

Shared: personal configuration cannot set it.

The Jira status a stage maps to. It is read only with `backend: jira`, where
every enabled stage except the side stage needs one, and each stage needs its
own. With the filesystem backend a `status` is reported as a problem. `jira.md` describes how statuses are chosen.

### `work.stages.*.prompt`

Overridable: personal configuration may set it.

The text `tcw work stage prompt <stage>` prints: the instructions an agent
reads before it works the stage. It is a list of text bindings (see "Binding
kinds" below), composed in order and joined by a blank line.

TCW's own text for the stage is the list's starting value. A list written in
`tcw-config.yaml` **replaces** it, unless the list holds an `inherit: true`
entry, which stands for TCW's own text at that position. Most projects want
`inherit: true`:

```yaml
work:
    stages:
        plan:
            prompt:
                - file: docs/lifecycle/planning-rules.md
                - inherit: true
```

`completed` and `discarded` have no text of their own.

### `work.stages.*.pre`

Shared: personal configuration cannot set it.

Checks that must pass before an item moves into this stage, as a list of
`command` bindings. They are part of the team's rules, so a person cannot
change them for themselves. How they run is under "How hooks run" below.

### `work.stages.*.post`

Overridable: personal configuration may set it.

What runs after an item has moved into this stage, as a list of `command`
bindings (run by TCW) or `skill` bindings (reported for the agent to run).
How they run is under "How hooks run" below. A person's own `post` list for a
stage replaces the team's for that stage unless it holds `inherit: true`.

## Binding kinds

Every entry of a `prompt`, `pre`, `post` or procedure list is a **binding**: a
mapping that names exactly one kind, plus an optional `when:`. A bare string
is refused, never guessed at.

| Kind | Its value | `prompt` and procedures | `pre` | `post` |
| --- | --- | --- | --- | --- |
| `blob` | text, used as written; an empty `blob` says nothing | yes | no | no |
| `file` | a path to a text file, read from the folder of the file that declares it, and never outside that folder | yes | no | no |
| `generate` | a shell command whose output is the text | yes | no | no |
| `skill` | a skill name (`plugin:skill` is allowed); prints "Invoke the … skill." | yes | no | yes: reported, never run |
| `command` | a shell command | no: use `generate` | yes | yes |

A `skill` is refused in a `pre` list: TCW cannot run a skill, so a check that
is only reported would always pass. A `skill:` value is checked for its shape
(no spaces or path separators), never for whether the skill is installed.

TCW's own text is written by TCW itself, and `tcw project config` displays it as
a built-in entry. A file never writes that entry; it writes `inherit: true`.

### Conditions: `when:`

A binding with `when:` applies only to some items:

```yaml
- file: docs/lifecycle/spec-bug.md
  when: { tags: [bug], not_tags: [docs] }
```

It applies to an item that carries any of the `tags` and none of the
`not_tags`. Both are lists, and tags are read in lower case. One string
holding several tags (`"cli,docs"`) is reported, since it could never match.
When no item is named, a `when:` that lists `tags` never matches.

### Keeping the layer below: `inherit: true`

A `prompt`, `pre` or `post` list, and a procedure's list, starts from what
the layer below set: TCW's own text, for `tcw-config.yaml`, and the team's
list, for a personal file. A list that is written replaces it. The entry
`- inherit: true` keeps it, at that position. A list holds at most one such
entry, the entry has no other key, and it is accepted only in those lists.
The same entry written twice in one list is reported.

## How hooks run

A **hook** is a `command` binding in a `pre` or `post` list. `tcw work advance`
runs them when it moves an item:

1. TCW's own checks for the target stage run first: the records check on any
   move into the stage after `implement` (`review`, or the next stage turned
   on), and the completion check on the move into `completed`.
2. Then the target stage's `pre` hooks run, in order. Only the target's run,
   never those of a stage the move skips. The first one that fails (exits
   with any code but 0) refuses the move, with exit code 3. A forced move
   (`--force` with `--reason`) runs every check and moves anyway, recording
   what failed in the trace comment.
3. The item moves.
4. The target stage's `post` hooks run, in order. A `skill` binding is
   printed for the agent to act on. The first `command` that fails stops the
   rest; the move stands, the failure names the file that declared the hook,
   and `advance` exits with code 6.

**`pre` hooks must be safe to run again for the same move.**
`tcw work advance --dry-run` runs them, and in Jira mode the Jira workflow can
still refuse a move after they have run, so the next attempt runs them again.

Adopting a Jira ticket with `tcw work tickets adopt` runs the `request`
stage's `post` hooks, and no `pre` hooks. Creating an item with
`tcw work new`, in this project or in another, runs no hooks.

Each hook runs through the shell, from the project's root folder, with no
input, and anything it prints goes to TCW's standard error. It gets these
environment variables:

| Variable | Value |
| --- | --- |
| `TCW_SLUG` | the item's full slug, `project/folder` |
| `TCW_STAGE` | the stage the item is moving into |
| `TCW_FROM_STAGE` | the stage it is moving from (empty when it had none) |
| `TCW_ITEM_PATH` | the item's folder |
| `TCW_PROJECT_ROOT` | the project's root folder |
| `TCW_CONFIG_DIR` | the folder of the file that declared the hook, so a personal hook can reach its own script |
| `TCW_FORCED` | `1`, on a forced move only |
| `TCW_REASON` | the `--reason` text, on a forced move only |

A hook that runs longer than `work.hooks.timeout` is stopped and counts as
failed.

## What a `generate:` binding gets

A `generate:` binding runs its command through the shell, from the project's
root folder, when the text is composed. What it prints on standard output
becomes the text. It gets:

- `TCW_STAGE` (the stage whose prompt is being composed; absent for a
  procedure), and, when an item is named, `TCW_SLUG`, `TCW_ITEM_PATH`;
  always `TCW_PROJECT_ROOT` and `TCW_CONFIG_DIR`. `TCW_FROM_STAGE`,
  `TCW_FORCED` and `TCW_REASON` are absent: nothing is moving.
- Four more variables, so a short script needs no JSON reader:
  `TCW_HOOK_ROLE` (`prompt` or `procedure`), `TCW_HOOK_KIND` (`generate`),
  `TCW_HOOK_ID` (the stage or procedure name) and `TCW_HOOK_PHASE` (`prompt`).
- On standard input, one JSON object:

  ```json
  {"schema": 1, "item": {"slug": "my-app/2026-10-01-add-login", "title": "Add login", "...": "..."}, "request": "the item's request text", "hook": {"role": "prompt", "kind": "generate", "id": "spec", "phase": "prompt", "body_truncated": false}}
  ```

  `item` is the item's properties (`slug`, `title`, `stage`, `created`,
  `priority`, `effort`, `complexity`, `tags`, `assignee`, `parent`,
  `blocked-by`, `blocks`, `children`, `path`, `untracked`), or `null` with no
  item.
  `request` is the item's request, cut to 64 KiB, in which case
  `body_truncated` is `true`, or `null`.

A script that runs longer than `work.hooks.timeout`, or prints more than
`work.hooks.output-cap` bytes, is stopped, and nothing it printed is used. A
script that exits with any code but 0 has its output thrown away too. In each
case the whole prompt or procedure fails with a message naming the script,
rather than being printed without that part.

## The request in a prompt: `{{tcw:request}}…{{/tcw:request}}`

Text from any binding may hold the pair `{{tcw:request}}…{{/tcw:request}}`.
When the text is composed for an item, the whole span is replaced by the
item's request. When the item has no request, or no item is named, the span
is replaced by the text between the two markers, so that text is the
fallback:

```yaml
- blob: "The request: {{tcw:request}}(none was given){{/tcw:request}}"
```

An opening marker with no closing one is left as written.

## Hook limits

### `work.hooks.timeout`

Shared: personal configuration cannot set it.

How many seconds a hook or a `generate:` script may run before it is stopped:
a positive number, 300 by default.

### `work.hooks.output-cap`

Shared: personal configuration cannot set it.

The most a `generate:` script may print, in bytes: a positive whole number,
65536 (64 KiB) by default. It is separate from the 64 KiB limit on the
request the script receives.

```yaml
work:
    hooks:
        timeout: 120
        output-cap: 32768
```

## Procedures

### `work.procedures.*`

Overridable: personal configuration may set it.

Some of TCW's instructions are not stages: they are **procedures**, printed
by `tcw work procedure <id>`. Their ids are `unattended-work`,
`triage-issues`, `documentation-sync`, `create-work`, `audit-backlog`,
`search` and `pause-work`. A project cannot add its own.

Each id holds a list of text bindings, composed exactly as a stage's
`prompt` is: TCW's own text is the starting value, a written list replaces
it, and `inherit: true` keeps it.

```yaml
work:
    procedures:
        documentation-sync:
            - inherit: true
            - blob: Also update docs/guide/ when a command's options change.
        search:
            - file: docs/procedures/search.md
```

An empty list makes the procedure print nothing. An unknown id is reported,
and so is an id TCW has removed, with where its text went. Check the result
with `tcw work procedure <id>`, or `tcw work procedure <id> --no-exec` to see
which bindings would be used without running any.
