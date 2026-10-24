# The Work component

A **work item** is one change to a project: to what its users can do, to its
machinery, or to the project itself. This guide explains what an item is,
the stages it moves through, the files it keeps, and the commands that create
and move it. It covers both backends, the **filesystem** backend, where
everything about an item is a file in your repository, and the **Jira**
backend, where Jira keeps what people outside engineering read and change; the
[Jira guide](jira.md) covers that side in depth.

See also [the command line](cli.md) for what every command prints and the exit
codes, [Configuration](configuration.md) for changing how stages behave, and
[Working across repositories](multi-repo.md) for items in other projects.

## What a work item is

An item is a **folder in the work store** (the folder `tcw work path` prints,
`docs/work/` unless the project says otherwise). The folder is created when the
item is created and **never moves**: an item's stage is a property recorded
about it, not where its folder sits. TCW never deletes an item's folder either;
an item that is abandoned is moved to the `discarded` stage and kept.

The folder's name is made from the item's title:

- filesystem backend: the creation date, then the title's words,
  `2026-10-15-refund-a-payment`;
- Jira backend: the ticket's key, then the title's words,
  `TCW-42-refund-a-payment`.

An item's **slug** is its name everywhere: the project's ID and the folder
name, `project/folder`, such as `demo/2026-10-15-refund-a-payment`. Inside the
project, the folder name alone is enough; in Jira mode, so is the ticket key.

Every item has the same **properties**, in either backend:

| Property | Values |
| --- | --- |
| title | any text |
| stage | one of the stages below |
| priority | `highest`, `high`, `medium` (the default), `low`, `lowest` |
| effort, complexity | `low`, `medium`, `high`, `very-high`, or empty |
| tags | tags registered for the project (`tcw work tags list`) |
| assignee | who is working on it, or empty |
| parent | the item it belongs under, or empty |
| blocked-by | items that must finish first |

`blocks` and `children` are not stored; `tcw work show` works them out from
the other items' `blocked-by` and `parent`.

Where the properties live depends on the backend:

- **Filesystem:** in `item.yaml` in the item's folder, a short YAML file you
  can read and edit like any other.
- **Jira:** on the item's ticket: its summary, status, priority, labels,
  assignee, parent and "blocks" links, and, when the project names them, custom
  fields for effort and complexity. The folder's `item.yaml` holds only the
  ticket's address.

Two things happen only in Jira mode, because a backend reports honestly what it
cannot map. An item's **priority can be empty** when the Jira project has no
priority field. And a parent or blocking ticket that has **no item** of its
own is not dropped: `tcw work show` lists its key as `untracked`.

## The stages

Every item moves through the same table of stages. `tcw work lifecycle`
prints it for your project, with which stages are turned on and what each one
runs.

| Stage | Kind | Writes | Can be turned off |
| --- | --- | --- | --- |
| `inbox` | flow | nothing | no |
| `request` | flow | one document, `request/request.md` | no |
| `spec` | flow | one document, `spec/spec.md` | yes |
| `plan` | flow | one document, `plan/plan.md` | yes |
| `implement` | flow | numbered rounds, `implement/round-N.md` | no |
| `review` | flow | numbered rounds, each with a verdict | yes |
| `qa` | flow | numbered rounds, each with a verdict | yes |
| `completed` | terminal | nothing | no |
| `discarded` | terminal | nothing | no |
| `postmortem` | side | one document, `postmortem/postmortem.md` | yes |

The columns mean:

- **Kind.** A **flow** stage is on the path an item takes from the inbox to the
  end, in the order of the table. A **terminal** stage is where an item ends:
  `completed` for finished work, `discarded` for abandoned work. The **side**
  stage, `postmortem`, is worked on alongside a finished item but never moved
  into; you write its document when a finished item is worth learning from.
- **Writes.** A **document** stage keeps one document, revised in place. A
  **rounds** stage keeps a new numbered file for each attempt, `round-1.md`,
  `round-2.md` and so on, so earlier attempts stay readable. `review` and
  `qa` rounds each carry a **verdict**, accepted or rejected (see below).
- **Can be turned off.** A project turns optional stages off in
  `tcw-config.yaml`
  ([`work.stages.*.enabled`](../../skills/configure/references/work.md#workstagesenabled));
  items then move straight past them. Every optional stage is on unless the
  project turns it off.

`completed` has a built-in check, the completion gate, and the stage after
`implement` has another, the records gate; both are described under
[Built-in gates](#built-in-gates). A rejected verdict in `review` or `qa`
sends the item back to `implement`.

## The item folder

```
docs/work/2026-10-15-refund-a-payment/
├── item.yaml                 the item's properties (filesystem mode)
├── capabilities.yaml         the product records this item changes
├── comments/                 comments, one file each (filesystem mode)
│   └── 20261015T190634Z.md
├── request/request.md        what the item asks for (filesystem mode)
├── spec/spec.md
├── plan/plan.md
├── implement/
│   ├── round-1.md
│   └── handoff-20261016T091500Z.md
└── review/round-1.md
```

### Stage documents and rounds

A stage's files sit in a folder named after the stage. `tcw work path` prints
where a file goes, so nobody has to assemble a path by hand:

```sh
tcw work path <slug>                      # the item's folder
tcw work path <slug> spec                 # spec/spec.md
tcw work path <slug> implement --next     # the next implement round to write
tcw work path <slug> implement --handoff  # a new handoff file for implement
```

### Verdicts, `judges`, and when a verdict is stale

A `review` or `qa` round records its verdict in **front matter**, a short block
of YAML between two `---` lines at the top of the file:

```markdown
---
verdict: accepted
judges: 2
---
The refund path works; tests in tests/test_refund.py pass.
```

- `verdict` is `accepted` or `rejected`.
- `judges` is the number of the `implement` round the verdict is about.

The **current verdict** of a stage is read from its latest round. It is
`stale` when that round judged an older implementation round than the latest
one: the work changed after the verdict was written. Only an `accepted`
verdict about the latest implementation lets an item go forward. A round with
no usable front matter counts as `invalid`, and a stage with no rounds yet as
`none`.

### Who records the qa verdict

In filesystem mode, by default, the agent working the `qa` stage judges the
result against the request and writes `qa/round-N.md` itself. A project that
wants a person to decide says so in its own
[`prompt` binding](../../skills/configure/references/work.md#workstagesprompt)
for `qa`. The agent then runs the checks, shows the person the evidence, asks
for accepted or rejected with a reason, and writes the round recording that
decision, with `decided-by: <name>` in its front matter beside `verdict` and
`judges`.

In Jira mode, qa happens on the ticket: a person accepts or rejects, by moving
it or by telling the agent, which then moves it with the person's reason, and
no round file is written. The [Jira guide](jira.md) describes it.

### Handoffs

A **handoff** is a note for whoever works on the stage next: what was done,
what is left, what to check first. It is a file named with the time it was
written, `<stage>/handoff-<time>.md`, at the path
`tcw work path <slug> <stage> --handoff` prints. The newest one is read when
the work resumes. In Jira mode, the `request` and `qa` stages are kept in Jira
and have no folder, so a handoff for them is a comment on the ticket whose
first line is `Handoff`.

### Comments

A comment is a short dated note on the item: a question, a decision, the
reason for a move. `tcw work comment <slug>` adds one, reading its text from
standard input, and `tcw work show <slug>` prints them all, newest first.
Filesystem mode keeps each in `comments/<time>.md`; Jira mode keeps them as
the ticket's comments.

### `capabilities.yaml`: the records an item changes

An item that changes the product says so in `capabilities.yaml` at the root of
its folder, naming the capabilities and taxonomy terms it adds, changes or
removes:

```yaml
new: [billing/refund-a-payment]
changed: [billing/view-a-payment]
removed: []
taxonomy:
    new: [refund]
```

The records themselves are changed during `implement`, in the same change as
the code. The records gate checks them when the item moves into the stage
after `implement`. How the chain runs from a request to the records is in
[Taxonomy and Capabilities](taxonomy-and-capabilities.md).

## Moving an item

Only one command changes an item's stage, `tcw work advance` (and
`tcw work discard`, which is a shorthand for it). It decides the target,
checks the rules, runs the target stage's checks, moves the item, and runs
what the target stage runs afterwards. On success it prints the item's new
stage.

### The next stage

A bare `tcw work advance <slug>` moves the item to the next stage that is
turned on. From `review` or `qa`, the next stage depends on the current
verdict: accepted goes forward, rejected goes back to `implement`, and anything
else (`none`, `invalid`, `stale`) is refused with a message saying which round
to write.

### `--to`: a stage of your choosing

`tcw work advance <slug> --to <stage>` names the target. Going back to an
earlier stage needs no `--force`, though the target stage's checks still run.
Going forward past a stage that is turned on is a **skip**, and needs
`--force` with a `--reason`. Moving forward out of `review` or `qa` without an
accepted verdict needs them too. Some moves need a `--reason` whatever their
direction: reopening an item that is `completed` or `discarded`, and, in a
Jira-mode project, leaving `qa`, whose verdict Jira keeps.

### `--force` and `--reason`

`--force` moves the item even when a check refuses; it requires `--reason`
saying why. Every check still runs, and what failed is recorded. Whenever a
move carries a reason, TCW records a **trace comment** on the item saying where
it moved from and to, whether it was forced, the reason, and any check it was
forced past:

```
Moved from implement to completed (forced).
Reason: agreed in the planning meeting
Gate failures overridden:
- completion gate: qa: the current verdict is none; …
```

### `--dry-run`

`--dry-run` answers whether the move would be allowed and prints the target,
without moving anything. It runs TCW's own checks and the target's `pre`
hooks, so those hooks must be safe to run twice. It answers only for TCW's
checks: in Jira mode, it can say yes to a move that the Jira workflow then does
not offer.

### Discarding, and reopening a finished item

`tcw work discard <slug> --reason "<why>"` moves an item to `discarded` from
any stage. A reason is required, and is recorded in the trace comment.

An item at `completed` or `discarded` is **finished**. Reopening it is a move
like any other, with `--to` naming the stage to go back to and a `--reason`.

### Built-in gates

A **gate** is a check that must pass before an item moves into a stage. TCW
has two of its own:

- **The records gate** runs on any move into the stage after `implement`
  (`review`, or whichever stage comes next in your project), whichever stage
  the item comes from. It checks the item's
  `capabilities.yaml` against the records: everything declared `new` or
  `changed` exists, a `new` capability's status is not still `Missing`,
  everything declared `removed` is gone, and the same for taxonomy terms. A
  declaration that cannot be checked counts as a failure.
- **The completion gate** runs on the move into `completed`. Every verdict
  stage TCW can read must have an accepted verdict about the latest
  implementation.

A project adds its own checks as `pre` hooks on the target stage. A failing
gate or `pre` hook refuses the move with exit code 3 and changes nothing.

No built-in gate checks that a stage's document was written: an item can
leave `spec` or `plan` with no `spec.md` or `plan.md`, because those stages
are optional and a project may decide a document is not needed. A project
that wants the check adds a `pre` hook on the next stage that fails when the
document is missing. TCW's own `tcw-config.yaml` does this, with a `pre` hook
on `plan` that requires `spec.md` and one on `implement` that requires both.
How to write one is in [Configuration](configuration.md#stages-and-their-bindings),
and how it runs in [How hooks run](configuration.md#how-hooks-run).

### After the move: `post` hooks, and exit code 6

Once the item has moved, the target stage's `post` hooks run: commands a
project attaches to a stage, such as notifying a channel or committing the
item's files. A failing `post` hook does not undo the move. `advance` reports
the failure, names the file that declared the hook, and exits with code 6:
**the item moved, but something after the move failed**. A trace comment that
could not be written is reported the same way.

How hooks run, the variables they receive, and their limits are in
[Configuration](configuration.md#how-hooks-run).

## Inbox items and tickets without an item

**Filesystem mode** keeps raw requests as items at the `inbox` stage, created
with `tcw work new "<title>" --stage inbox`. `tcw work stage prompt inbox`
prints the instructions for sorting them: each one is taken on (moved to
`request` with `tcw work advance`), merged into an item that already covers
it, or discarded with a reason.

**Jira mode** keeps no items at `inbox`. A raw request is a ticket in Jira,
written by anyone, and it becomes an item when it is adopted:
`tcw work tickets list` prints the tickets waiting, and
`tcw work tickets adopt <KEY>` makes one an item at `request`. The
[Jira guide](jira.md) describes both.

## Creating and changing items

```sh
tcw work new "Refund a payment" --priority high --tag billing < request.md
tcw work list --stage implement --tag billing
tcw work show demo/2026-10-15-refund-a-payment
tcw work edit demo/2026-10-15-refund-a-payment --assignee sam --effort medium
```

- **`tcw work new "<title>"`** creates an item at `request` (or at `inbox` with
  `--stage inbox`, filesystem mode only) and prints its slug. Text piped on
  standard input becomes its request. Properties can be set as it is created.
  An item for another project is made in that project, with
  `tcw -C <folder> work new` ([Working across repositories](multi-repo.md)).
- **`tcw work list`** prints the slugs of unfinished items, and of items with
  no stage the model knows. `--all` adds finished items. `--stage` limits it to
  the stages named, `--parent` to one item's children, `--assignee` or
  `--mine` to one person's items. **`--tag` can be repeated**, and an item is
  listed when it carries **any** of the tags given. In Jira mode, tags are the
  ticket's labels.
- **`tcw work show <slug>`** prints everything about one item: its properties,
  its request and its comments, newest first. `--json` prints the same as one
  JSON object.
- **`tcw work edit <slug>`** changes properties. A flag left out leaves the
  property alone, and an empty value clears it (`--assignee ''`). `--tag` and
  `--untag` add and remove tags; `--assign-me` assigns the item to you (your
  `user.name`, or your Jira account).
- **Tags** must be registered before an item can carry them:
  `tcw work tags add billing` registers one, `tcw work tags rm billing`
  unregisters it.
- **Blocking.** `--blocked-by <slug>` says an item must wait for another;
  `--unblocked-by` takes one off. The link is always written on the blocked
  item; the `--blocks` option of `tcw work edit`, which wrote it from the other
  side, is removed in 4.0.
- **Parents and epics.** `--parent <slug>` puts an item under another. An item
  with children is an **epic**; `tcw work show` lists its children, and
  `tcw work list --parent <slug>` prints them.
- **`tcw work rename <slug> <words>`** renames the item's folder, keeping its
  date (filesystem) or its ticket key (Jira), and rewrites the `parent` and
  `blocked-by` of every other item in the project that names it. It prints
  one `<old> -> <new>` line per identifier it changed. Items in other projects that name the old slug are not
  rewritten; `tcw validate` there reports them.
- **`tcw work comment <slug>`** adds a comment, reading its text from
  standard input.

## References, and what `tcw validate` reports

An item's `parent` and `blocked-by` are **references** to other items. They
may point into other projects. `tcw validate` checks them, and the item's
stage against its files. With the filesystem backend plain `tcw validate`
runs these checks; in a Jira-mode project the stage and references are kept
in Jira, so they run only under `tcw validate --remote`, which reads them
there ([the Jira guide](jira.md#checking-the-workflow) lists what plain
`tcw validate` checks in that mode):

- a reference to an item that does not exist is a **warning**;
- an item whose stage is ahead of its documents, such as an item at
  `implement` with nothing from `spec`, is a **warning** (it happens when an
  item was forced past a stage, and lasts until the item is finished);
- a reference into a project that cannot be reached from here is reported as
  **unresolved**, which is neither a warning nor an error: TCW cannot tell
  whether it is right.

A command that has to read a project that is declared but is not on this
machine stops with exit code 5 and says that `tcw project provision` obtains it. The
exit codes are listed in [the command-line guide](cli.md#exit-codes).

## Stage instructions and procedures

TCW ships the instructions an agent follows at each stage, and a project adds
its own:

- **`tcw work stage prompt <stage> [<slug>]`** prints the instructions for one
  stage, composed with this project's bindings, and for one item when a slug is
  given. It runs no checks. An agent runs it before working a stage.
- **`tcw work lifecycle`** prints the stage table for this project: each
  stage's kind, whether it is turned on, and what it runs before, at and after
  a move.
- **`tcw work procedure <id> [<slug>]`** prints one of TCW's **procedures**:
  instructions that are not a stage, such as `documentation-sync`, `search`
  or `audit-backlog`, composed with this project's text.
- **`tcw work docs`** prints the project's documentation entries: which
  documents must change with which kinds of change.

## TCW never changes git state

TCW writes an item's files and leaves recording them to you: it never stages,
commits, pulls, pushes, or switches a branch. It does **read** git where it
needs to: to find the repository a project or a work store sits in (which
`tcw project new` also does, to decide whether to add an ignore rule for your personal
configuration file), to check that a work store has no uncommitted changes
before creating an item in another project, to check whether git tracks
`tcw-config.local.yaml` (`tcw validate` warns when it does), to notice that it
is running in a linked git worktree, and, in `tcw project provision`, to check that a
folder already there is a clone of the declared repository. And
`tcw project provision` clones a store or project that is declared and missing, because
you asked it to. A project that wants each move committed adds it itself; the
[configuration guide's example](configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds)
shows one way, with a prompt and a `post` hook.

## Commands

| Command | What it does |
| --- | --- |
| `tcw work new "<title>"` | create an item; its request on standard input |
| `tcw work list` | list items |
| `tcw work show <slug>` | everything about one item |
| `tcw work path [<slug> [<stage>]]` | where a file goes |
| `tcw work edit <slug>` | change properties |
| `tcw work advance <slug>` | move an item to its next stage, or `--to` one |
| `tcw work discard <slug> --reason "<why>"` | abandon an item |
| `tcw work comment <slug>` | add a comment from standard input |
| `tcw work rename <slug> <words>` | rename the item's folder |
| `tcw work stage prompt <stage> [<slug>]` | a stage's instructions |
| `tcw work procedure <id> [<slug>]` | a procedure's instructions |
| `tcw work lifecycle` | the stage table and its bindings |
| `tcw work docs` | the documentation entries |
| `tcw work tags list` / `add` / `rm` | the tag registry |
| `tcw work tickets list` | Jira tickets waiting to become items |
| `tcw work tickets adopt <KEY>` | make a Jira ticket an item |

Every command's options are in its `--help`, and what each prints, with the
exit codes, is in [the command-line guide](cli.md).
