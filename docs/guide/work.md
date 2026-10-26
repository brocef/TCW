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
[Related projects](multi-repo.md) for parent links and other projects' items.

## What a work item is

An item is a **folder in the work store** (the folder `tcw work path` prints,
`docs/work/` unless the project says otherwise) holding the file
`tcw-work-item.yaml`. The folder may sit at the top of the work store, inside
another item's folder (a **nested** item), or inside an **organising folder**,
a plain folder that holds items and is not one itself. An item's stage is a
property recorded about it, not where its folder sits: moving an item from one
stage to the next never moves its folder. The folder moves only when you ask,
with `tcw work move` or `tcw work rename` ([below](#creating-and-changing-items)).
TCW never deletes an item's folder either; an item that is abandoned is moved
to the `discarded` stage and kept.

The folder's name is made from the item's title:

- filesystem backend: the creation date, then the title's words,
  `2026-10-15-refund-a-payment`;
- Jira backend: the ticket's key, then the title's words,
  `TCW-42-refund-a-payment`.

An item's **full identifier** is its name everywhere: the project's ID,
`.work/`, and the item's **id-path**, which is its folder's path in the work
store, such as `demo.work/2026-10-15-refund-a-payment`, or
`demo.work/2026-10-01-payments/2026-10-15-refund-a-payment` for an item nested
in another's folder. Every command prints full identifiers. Inside the
project, the id-path alone is enough; in Jira mode, so is the ticket key. A
command's `--help` calls this argument `slug`, a nickname for the full
identifier, and this guide writes it `<item>`. Every form a command accepts is
in [the command line](cli.md), and full identifiers in other projects in
[Linking and validation](linking-and-validation.md).

Every item has the same **properties**, in either backend:

| Property           | Values                                                     |
| ------------------ | ---------------------------------------------------------- |
| title              | any text                                                   |
| stage              | one of the stages below                                    |
| priority           | `highest`, `high`, `medium` (the default), `low`, `lowest` |
| effort, complexity | `low`, `medium`, `high`, `very-high`, or empty             |
| tags               | tags registered for the project (`tcw work tags list`)     |
| assignee           | who is working on it, or empty                             |
| parent             | the item it belongs under, or empty                        |
| blocked-by         | items that must finish first                               |

`blocks` and `children` are not stored; `tcw work show` works them out from
the other items' `blocked-by` and `parent`.

Where the properties live depends on the backend:

- **Filesystem:** in `tcw-work-item.yaml` in the item's folder, a short YAML
  file you can read and edit like any other. Its first line names the TCW
  version that wrote it, `tcw-version: 4.0.0`.
- **Jira:** on the item's ticket: its summary, status, priority, labels,
  assignee, parent and "blocks" links, and, when the project names them, custom
  fields for effort and complexity. The folder's `tcw-work-item.yaml` holds
  only the version line, the ticket's address, and any parent or blocker Jira
  cannot link ([the Jira guide](jira.md) describes those).

Two things happen only in Jira mode, because a backend reports honestly what it
cannot map. An item's **priority can be empty** when the Jira project has no
priority field. And a parent or blocking ticket that has **no item** of its
own is not dropped: `tcw work show` lists its key as `untracked`.

## The stages

Every item moves through the same table of stages. `tcw work lifecycle`
prints it for your project, with which stages are turned on and what each one
runs.

| Stage        | Kind     | Writes                                   | Can be turned off |
| ------------ | -------- | ---------------------------------------- | ----------------- |
| `inbox`      | flow     | nothing                                  | no                |
| `request`    | flow     | one document, `request/request.md`       | no                |
| `spec`       | flow     | one document, `spec/spec.md`             | yes               |
| `plan`       | flow     | one document, `plan/plan.md`             | yes               |
| `implement`  | flow     | numbered rounds, `implement/round-N.md`  | no                |
| `review`     | flow     | numbered rounds, each with a verdict     | yes               |
| `qa`         | flow     | numbered rounds, each with a verdict     | yes               |
| `completed`  | terminal | nothing                                  | no                |
| `discarded`  | terminal | nothing                                  | no                |
| `postmortem` | side     | one document, `postmortem/postmortem.md` | yes               |

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
  `.tcw/tcw-config.yaml`
  ([`work.stages.*.enabled`](../../skills/configure/references/work.md#workstagesenabled));
  items then move straight past them. Every optional stage is on unless the
  project turns it off.

`completed` has a built-in check, the completion gate, and the stage after
`implement` has another, the records gate; both are described under
[Built-in gates](#built-in-gates). A rejected verdict in `review` or `qa`
sends the item back to `implement`.

## The item folder

```
docs/work/2026-10-01-payments/
├── tcw-work-item.yaml              the parent item's properties
└── 2026-10-15-refund-a-payment/    a child item, nested in its parent's folder
    ├── tcw-work-item.yaml          the item's properties (filesystem mode)
    ├── capabilities.yaml           the product records this item changes
    ├── comments/                   comments, one file each (filesystem mode)
    │   └── 20261015T190634Z.md
    ├── request/request.md          what the item asks for (filesystem mode)
    ├── spec/spec.md
    ├── plan/plan.md
    ├── implement/
    │   ├── round-1.md
    │   └── handoff-20261016T091500Z.md
    ├── review/round-1.md
    └── resources/                  anything else: designs, notes, images
        └── design.md
```

An item's folder holds a fixed set of things, and nothing else:

- its two files, `tcw-work-item.yaml` and `capabilities.yaml`;
- `comments/` and one folder per stage, named after the stage;
- the folders of the items nested in it, each holding its own
  `tcw-work-item.yaml`;
- one `resources/` folder for everything else.

`tcw validate` reports anything else as an error, with what to do:

```
error: docs/work/2026-10-15-refund-a-payment/design.md: is not one of demo.work/2026-10-15-refund-a-payment's files; move it into resources/
error: docs/work/2026-10-15-refund-a-payment/notes: is not a child object of demo.work/2026-10-15-refund-a-payment: it has no tcw-work-item.yaml; give it one, or move it into resources/
```

So a document that belongs to no stage, such as a long design too big for the
item's request or its ticket, goes in `resources/`. TCW does not look inside
`resources/`. The names `resources`, `comments` and the stage names, in any
letter case, are kept for these folders: `tcw work move` refuses one as an
organising folder's name with exit code 2 (`'Resources' in Resources is a
reserved name`). An organising folder that holds no item is reported as a
warning, `holds no TCW object`.

### Stage documents and rounds

A stage's files sit in a folder named after the stage. `tcw work path` prints
where a file goes, so nobody has to assemble a path by hand:

```sh
tcw work path <item>                      # the item's folder
tcw work path <item> spec                 # spec/spec.md
tcw work path <item> implement --next     # the next implement round to write
tcw work path <item> implement --handoff  # a new handoff file for implement
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
`tcw work path <item> <stage> --handoff` prints. The newest one is read when
the work resumes. In Jira mode, the `request` and `qa` stages are kept in Jira
and have no folder, so a handoff for them is a comment on the ticket whose
first line is `Handoff`.

### Comments

A comment is a short dated note on the item: a question, a decision, the
reason for a move. `tcw work comment <item>` adds one, reading its text from
standard input, and `tcw work show <item>` prints them all, newest first.
Filesystem mode keeps each in `comments/<time>.md`; Jira mode keeps them as
the ticket's comments.

### `capabilities.yaml`: the records an item changes

An item that changes the product says so in `capabilities.yaml` at the root of
its folder, naming the capabilities and taxonomy terms it adds, changes or
removes, each by its full identifier (the name that says which project owns
it, described in [the linking guide](linking-and-validation.md)):

```yaml
new: [app.capabilities/billing/refund-a-payment]
changed: [app.capabilities/billing/view-a-payment]
removed: []
taxonomy:
    new: [app.taxonomy/refund]
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

A bare `tcw work advance <item>` moves the item to the next stage that is
turned on. From `review` or `qa`, the next stage depends on the current
verdict: accepted goes forward, rejected goes back to `implement`, and anything
else (`none`, `invalid`, `stale`) is refused with a message saying which round
to write.

### `--to`: a stage of your choosing

`tcw work advance <item> --to <stage>` names the target. Going back to an
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

`tcw work discard <item> --reason "<why>"` moves an item to `discarded` from
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
document is missing. TCW's own project configuration does this, with a `pre`
hook on `plan` that requires `spec.md` and one on `implement` that requires both.
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
tcw work new "Partial refunds" --parent 2026-10-01-payments --nest
tcw work list --stage implement --tag billing
tcw work show demo.work/2026-10-15-refund-a-payment
tcw work edit demo.work/2026-10-15-refund-a-payment --assignee sam --effort medium
```

- **`tcw work new "<title>"`** creates an item at `request` (or at `inbox` with
  `--stage inbox`, filesystem mode only) and prints its full identifier. Text
  piped on standard input becomes its request. Properties can be set as it is
  created. The new folder is made at the top of the work store, unless
  `--nest` asks for it inside its parent's folder (see "Parents" below).
- **`tcw work list`** prints the full identifiers of unfinished items, and of
  items with no stage the model knows. `--all` adds finished items. `--stage`
  limits it to the stages named, `--parent` to one item's children,
  `--assignee` or `--mine` to one person's items. **`--tag` can be repeated**,
  and an item is listed when it carries **any** of the tags given. In Jira
  mode, tags are the ticket's labels. `--scope` adds the items of related
  projects ([the command line](cli.md) describes it).
- **`tcw work show <item>`** prints everything about one item: its properties,
  its request and its comments, newest first. `--json` prints the same as one
  JSON object.
- **`tcw work edit <item>`** changes properties. A flag left out leaves the
  property alone, and an empty value clears it (`--assignee ''`). `--tag` and
  `--untag` add and remove tags; `--assign-me` assigns the item to you (your
  `user.name`, or your Jira account).
- **Blocking.** `--blocked-by <item>` says an item must wait for another;
  `--unblocked-by` takes one off. The reference is always written on the
  blocked item, by `tcw work new` or `tcw work edit` run on that item;
  `tcw work show` of the other item lists it under `blocks`.
- **Parents.** `--parent <item>` puts an item under another. An item with
  children is an **epic**; `tcw work show` lists its children, and
  `tcw work list --parent <item>` prints them. The `parent` property is what
  makes an item a child, wherever its folder is. On `tcw work new`, `--nest`
  also makes the new folder inside the parent's folder, so the child's full
  identifier is the parent's with its own folder name added:
  `demo.work/2026-10-01-payments/2026-10-24-partial-refunds`. `--nest`
  without `--parent` is refused with exit code 2. When the parent belongs to
  another project, the folder is made at the top of this project's work store
  instead, and `tcw work new` says so in a line starting `not nested:`.
- **`tcw work move <item> --into <id-path>`** moves the item's folder into
  another item's folder, or into an organising folder, which is made when it
  is missing; **`tcw work move <item> --top`** moves it back to the top of
  the work store, and removes an organising folder the move leaves empty. The
  items nested in it move with it. A move changes no `parent`: an item moved
  into another's folder without that parent gets a warning, from the move and
  from `tcw validate`, saying `parent: decides`.
- **`tcw work rename <item> <words>`** renames the item's folder, keeping its
  date (filesystem) or its ticket key (Jira); the items nested in it are
  renamed with it, since their id-paths start with its folder's name.

`tcw work move` and `tcw work rename` change the full identifier of the item
and of every item nested in it, so both rewrite every reference to those
identifiers in this project, such as another item's `parent` or `blocked-by`
and a `tcw://` link in a document, and name each file they rewrote on
standard error. Each prints one `<old full id> -> <new full id>` line per
identifier it changed, the item first:

```
demo.work/2026-10-01-payments -> demo.work/2026-10-01-refunds
demo.work/2026-10-01-payments/2026-10-24-partial-refunds -> demo.work/2026-10-01-refunds/2026-10-24-partial-refunds
```

References in other projects are not rewritten: both commands end by saying
`references in other projects are not rewritten; tcw validate there reports
them: pass on the identifiers above`. In Jira mode they also edit each moved
ticket's `TCW Item` ([the Jira guide](jira.md) says how, and what happens when
Jira stops part way).

- **`tcw work comment <item>`** adds a comment, reading its text from
  standard input.
- **Tags** must be registered before an item can carry them:
  `tcw work tags add billing` registers one, `tcw work tags rm billing`
  unregisters it, and both write `work.tags` in `.tcw/tcw-config.yaml`. A
  project whose parent links pass `config` also has the tags its parents
  register ([Configuration](configuration.md) describes what is inherited).
  In such a child, `tcw work tags add` writes an `inherit: true` entry first,
  so the child keeps its parents' tags as well as its own:

    ```yaml
    work:
        tags:
            - inherit: true
            - mobile
    ```

    `tcw work tags rm` in a child removes only the child's own tags. A tag a
    parent registers is refused with exit code 3:

    ```
    tcw work tags rm: tag 'billing' is inherited from 'core'; to drop it, list this project's tags under work.tags in .tcw/tcw-config.yaml without an 'inherit: true' entry
    ```

    When a parent that passes `config` is not on this machine, the tag
    commands stop with exit code 7, since the tags cannot be known.

### Another project's items

A command changes only the project it is run in. To create or change an item
of another project, run the command in that project with the global option
`-C`, which runs `tcw` as if it had been started in that project's folder:
`tcw -C <folder> work new "<title>"`, or `tcw -C tcw://<id>.path/ work edit …`,
where `tcw://<id>.path/` is the address of that project's folder on this
machine and `tcw project path <id>` prints the folder. Naming another
project's item to a command that changes it, from here, is refused with exit
code 3, and the message gives the `tcw -C` to run. Reading another project's
items works from here, with `tcw work show` or `--scope`.
[Related projects](multi-repo.md) describes how projects are related and
found.

## References, and what `tcw validate` reports

An item's `parent` and `blocked-by` are **references** to other items, each
written as a full identifier. They may point into other projects. `tcw work
new` and `tcw work edit` refuse a reference to an item that does not exist
(exit code 4) or to a project TCW cannot find (exit code 1). `tcw validate`
checks the references already written, and each item's stage against its
files. With the filesystem backend plain `tcw validate` runs these checks; in
a Jira-mode project the stage and the references Jira links are kept in
Jira, so they run only under `tcw validate --remote`, which reads them there
([the Jira guide](jira.md#checking-the-workflow) lists what plain
`tcw validate` checks in that mode):

- a reference to an item that does not exist is a **warning**, such as
  `blocked-by references a missing item, core.work/2026-01-01-missing`;
- an item whose stage is ahead of its documents, such as an item at
  `implement` with nothing from `spec`, is a **warning** (it happens when an
  item was forced past a stage, and lasts until the item is finished);
- an item whose folder is inside another item's folder, and whose `parent` is
  not set or names another item, is a **warning** saying `parent: decides`;
- a reference into a project that is not on this machine is reported as
  **unresolved**, which is neither a warning nor an error: TCW cannot tell
  whether it is right. The finding says the reference `is in a project that
cannot be reached from here`.

A command that has to read a project that a manifest lists but that is not on
this machine, such as `tcw work show` of one of its items, stops with exit
code 5 and says where the manifest places it; when the entry names a
repository, the message ends `fetch it with 'tcw project provision <id>'`.
A project no manifest lists and no nearby folder declares is exit code 1,
`no project with ID '<id>' is known or found near this one; check the
spelling`. [Related projects](multi-repo.md) describes manifests and how a
project is found, and the exit codes are listed in
[the command-line guide](cli.md#exit-codes).

## Stage instructions and procedures

TCW ships the instructions an agent follows at each stage, and a project adds
its own:

- **`tcw work stage prompt <stage> [<item>]`** prints the instructions for one
  stage, composed with this project's bindings, and for one item when an item
  is given. It runs no checks. An agent runs it before working a stage.
- **`tcw work lifecycle`** prints the stage table for this project: each
  stage's kind, whether it is turned on, and what it runs before, at and after
  a move.
- **`tcw work procedure <id> [<item>]`** prints one of TCW's **procedures**:
  instructions that are not a stage, such as `documentation-sync`, `search`
  or `audit-backlog`, composed with this project's text.
- **`tcw work docs`** prints the project's documentation entries: which
  documents must change with which kinds of change.

## TCW never changes git state

TCW writes an item's files and leaves recording them to you: it never stages,
commits, pulls, pushes, or switches a branch. It does **read** git where it
needs to: to find the repository a project or a work store sits in (which
`tcw project new` also does, to decide whether to add an ignore rule for your
personal files), to check whether git tracks `.tcw/tcw-config.local.yaml` or
`.tcw/tcw-manifest.local.yaml` (`tcw validate` warns when it does), to notice
that it is running in a linked git worktree, and, in `tcw project provision`,
to check that a folder already there is a clone of the declared repository.
And `tcw project provision` clones a store or project that is declared and
missing, because you asked it to. A project that wants each move committed adds it itself; the
[configuration guide's example](configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds)
shows one way, with a prompt and a `post` hook.

## Commands

| Command                                    | What it does                                    |
| ------------------------------------------ | ----------------------------------------------- |
| `tcw work new "<title>"`                   | create an item; its request on standard input   |
| `tcw work list`                            | list items                                      |
| `tcw work show <item>`                     | everything about one item                       |
| `tcw work path [<item> [<stage>]]`         | where a file goes                               |
| `tcw work edit <item>`                     | change properties                               |
| `tcw work advance <item>`                  | move an item to its next stage, or `--to` one   |
| `tcw work discard <item> --reason "<why>"` | abandon an item                                 |
| `tcw work comment <item>`                  | add a comment from standard input               |
| `tcw work move <item> --into <id-path>`    | move the item's folder into another folder      |
| `tcw work move <item> --top`               | move the item's folder to the top of the store  |
| `tcw work rename <item> <words>`           | rename the item's folder and those nested in it |
| `tcw work stage prompt <stage> [<item>]`   | a stage's instructions                          |
| `tcw work procedure <id> [<item>]`         | a procedure's instructions                      |
| `tcw work lifecycle`                       | the stage table and its bindings                |
| `tcw work docs`                            | the documentation entries                       |
| `tcw work tags list` / `add` / `rm`        | the tag registry                                |
| `tcw work tickets list`                    | Jira tickets waiting to become items            |
| `tcw work tickets adopt <KEY>`             | make a Jira ticket an item                      |

Every command's options are in its `--help`, and what each prints, with the
exit codes, is in [the command-line guide](cli.md).
