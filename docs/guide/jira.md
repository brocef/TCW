# Using TCW with Jira

A project whose `.tcw/tcw-config.yaml` sets `work.backend: jira` keeps its
work items on Jira tickets. This guide is for both sides of that arrangement:
the people outside engineering who write and follow tickets in Jira, and the
engineers and agents who work the items with `tcw`. It is also where every
change a `tcw` command makes to a ticket is described. Everything about items
that does not depend on the backend, such as the stages, the item folder,
nested items and moving an item, is in [the work guide](work.md).

An item's **full identifier** is its name everywhere: the project's ID,
`.work/`, and the item's **id-path**, which is its folder's path inside the
work store, such as `shop.work/SHOP-42-refund-a-payment`. How full
identifiers are written, and the other forms a command accepts, are in
[Linking and validation](linking-and-validation.md) and
[the command line](cli.md).

## Who owns what

Each fact about an item has one home, and nothing is copied between the two:

| Jira owns                                      | The repository owns                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------ |
| the request (the ticket's description)         | the spec, the plan and every round                                                         |
| the status, which is the item's stage          | handoffs for the stages worked in the repository                                           |
| the assignee                                   | the item's declared record changes, `capabilities.yaml`                                    |
| priority, effort and complexity                | the taxonomy and the capabilities                                                          |
| labels, which are the item's tags              | a parent or blocker Jira cannot link (see [below](#parents-and-blockers-jira-cannot-link)) |
| the parent, and "blocks" links between tickets |                                                                                            |
| comments                                       |                                                                                            |

In the repository, each item still has a folder in the work store, named with
the ticket's key and then the title's words, `SHOP-42-refund-a-payment`. The
folder may sit at the top of the work store or inside another item's folder
(a **nested** item); TCW finds a key-named folder at any depth. The folder's
state file, `tcw-work-item.yaml`, holds the line naming the TCW version that
wrote it, the ticket's address, and any parent or blocker Jira cannot link;
everything else in the folder is the technical record. The taxonomy and
capabilities are never stored in Jira: they describe the product, and they
live and change with its code.

## For people outside engineering

### Writing a ticket

A ticket is written in plain language, by anyone. Its description is the
item's **request**, and the request has five sections:

- **What and why**: the change, and the reason for it.
- **Product changes**: what users will be able to do differently. "None" is a
  valid answer.
- **Out of scope**: what is deliberately left out.
- **Constraints**: deadlines, compatibility, anything that limits the answer.
- **References**: links, each with a line on why it matters.

`tcw work stage prompt request` prints the full template, with what the agent
does when a section is missing: it comments on the ticket, listing what is
missing and proposing wording, and does not rewrite the description on its own.

The requester decides when the request is ready to be worked on. They can move
the ticket on in Jira themselves, or tell the agent they are working with to do
it. When told, the agent puts any wording the requester adopted into the
description (or asks them to paste it in, if it cannot edit Jira), checks it,
and moves the item with `tcw work advance`, which posts a comment naming who
asked for the move. Moving it that way also runs any checks and hooks the
project attached to the move, which a move made in Jira does not.

### Following progress

The ticket's status is the item's stage: when the item moves, the ticket
moves. When the spec is written, a comment whose first line is `QA plan`
appears on the ticket, describing in plain language how the change will be
checked; a revised spec posts a new one.

### Accepting or rejecting the work

QA happens on the ticket. When the item reaches the QA status, a person
decides:

- **Accept** by moving the ticket on to its finished status.
- **Reject** by moving it back to the implementation status, **with a comment
  saying why**: that comment is what the engineer reads next.

Or tell the agent that ran the checks: "accepted", or "rejected, because …".
It records the decision by moving the ticket, with a comment naming you and
your reason. The agent never decides the verdict itself, and does not take an
instruction given before you saw its findings as one.

### A ticket that will not be worked on

A ticket waiting in the inbox may be turned down, as a duplicate or for
another reason. The agent sorting the inbox comments on it with the reason,
and a person closes it in Jira; TCW has no command that closes a ticket.

### What the request missed

After an item is finished, a project can ask for a postmortem comment: a note
on the ticket, written in the request's own language, saying what the request
missed. A project turns it on in its own instructions for the `postmortem`
stage.

## Setting up

A minimal configuration, with the status names TCW's own Jira project uses:
every optional stage turned on, `spec` at `Specifying`, `plan` at `Planning`
and `qa` at `In QA`.

```yaml
# .tcw/tcw-config.yaml
tcw-version: 4.0.0
id: shop
work:
    backend: jira
    jira:
        site: https://example.atlassian.net
        project: SHOP
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_TOKEN
        fields:
            project: TCW Project
            item: TCW Item
    stages:
        inbox: { status: Inbox }
        request: { status: Request }
        spec: { status: Specifying }
        plan: { status: Planning }
        implement: { status: In Progress }
        review: { status: In Review }
        qa: { status: In QA }
        completed: { status: Done }
        discarded: { status: Discarded }
```

- **Credentials are named, never written.** `email-env` and `token-env` name
  two environment variables, and TCW reads their values only when it sends a
  request. Set them in the shell that runs `tcw`:

    ```sh
    export TCW_JIRA_EMAIL=you@example.com
    export TCW_JIRA_TOKEN=<your Jira API token>
    ```

    When they are not set, a command that needs Jira stops with exit code 1
    and names them:

    ```
    tcw work list: Jira credentials are not set: TCW_JIRA_EMAIL, TCW_JIRA_TOKEN. Export them, or correct work.jira.credentials in .tcw/tcw-config.yaml.
    ```

- **Two custom fields** tie a ticket to an item: a text field holding the TCW
  project's ID (`TCW Project`) and one holding the item's full identifier
  (`TCW Item`), nested id-path included, such as
  `shop.work/SHOP-40-payments/SHOP-42-refund-a-payment` for an item whose
  folder is inside its parent's. They must be on both the issue type's create
  screen and its edit screen.

Every key, its default and its rules are in the configure skill's
[`jira.md`](../../skills/configure/references/jira.md). The `setup` skill
walks through a first setup.

### Settings a parent passes down

A project may take its Jira settings from a parent: a project it names under
`parents:` whose link passes `config` (how parent links work is in
[Related projects](multi-repo.md)). Its `work.jira` is then merged key by key
with what the parents pass: a key the project sets itself wins, and every key
it leaves out comes from its parents (when several set one, the load order
[Related projects](multi-repo.md) describes decides which). So a family of
projects can keep one site, one set of credential names and one pair of
field names in a shared parent, and each child sets only `project` when its
tickets are in another Jira project. `tcw project config --origin` names the
project and file each value came from.

Two things are always the project's own and never come from a parent:
`work.backend: jira`, which each Jira-mode project writes in its own
`.tcw/tcw-config.yaml`, and the stages with their Jira statuses
(`work.stages`). A child of a Jira-mode parent that does not write
`work.backend: jira` keeps its items in files.

A credential variable's name may also come from an override variable, such
as `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__SHOP=SHOP_EMAIL`, which makes the
project `shop` read its email from `SHOP_EMAIL`. How these variables are named,
and the other layers, are in [Configuration](configuration.md).

When a parent that could pass `work.jira` is not on this machine, TCW cannot
tell which Jira settings apply, so a Jira-mode project cannot open its work
items: `tcw work list` and every other command that reads or changes an item
stop with exit code 7, naming the setting and the parent, before any request
is sent:

```
tcw work list: 'shop' inherits its configuration (work.jira) from project 'org', which is not on this machine: …
```

`tcw work lifecycle`, `tcw work docs`, `tcw work stage prompt <stage>` and
`tcw validate` still work; `tcw validate` reports the parent as
`unresolved`. [Related projects](multi-repo.md) says how to put the parent on
this machine.

## Stages and statuses

Each stage that is turned on maps to its own Jira status. `postmortem` has
none, since nothing ever moves into it.

To move an item, TCW applies a Jira **transition** (one of the moves the Jira
workflow offers from the ticket's current status) into the target stage's
status, and picks it this way:

1. When the ticket offers exactly one transition to that status, TCW uses it.
2. When it offers several, TCW uses the one whose screen asks for nothing
   except a comment.
3. When that still leaves none, or more than one, the move is refused with
   exit code 3, and the message lists the transitions it found.

TCW never fills in a transition screen's fields other than the comment.

A ticket can also be moved by hand in Jira. TCW reads the ticket's status as
the item's stage, so a move made by hand counts as a forced move with no
reason recorded. A ticket in a status that no stage maps to has **no stage**:
`tcw work list` still shows it, and moving it needs `--to`, `--force` and a
`--reason` (discarding it needs only the reason).

## Checking the workflow

`tcw validate` never contacts Jira. It checks the configuration's shape and
what the item folders hold on their own: each folder's name and
`tcw-work-item.yaml`, a ticket key used by two folders at any depth, a record
folder for a stage Jira keeps, the latest `review` round, each folder's
`capabilities.yaml` (reported when the file cannot be read or is malformed,
whatever the item's stage), and each parent or blocker recorded in a folder.
A recorded reference that names a ticket on this site is an error, since it
should be a Jira link, and the message gives the `tcw work edit` command that
makes it one. Whether the records `capabilities.yaml` declares have been
changed, and the other checks that need an item's properties, which Jira
holds, wait for `--remote`.

`tcw validate --remote` also reads Jira, and changes nothing there. It prints
findings only, one per line: a status that does not exist, a move between two
stages that no transition offers, a transition screen that asks for a field
other than the comment, a configured field missing from a create or edit
screen, an item folder whose ticket is missing or whose `TCW Item` names
another item, and each ticket that still holds a TCW 3.x `TCW Item` value
(see [Tickets that still hold a TCW 3.x value](#tickets-that-still-hold-a-tcw-3x-value)).
It then runs the work-item checks plain `tcw validate` runs in a
filesystem-mode project: a `parent` or `blocked-by` naming an item that does
not exist, an item whose stage is ahead of its documents, and the records each
unfinished item's `capabilities.yaml` declares (a file plain `tcw validate`
already reported as malformed is not reported again). A move it could not
check, such as one with no ticket at that status to try, is a finding too.
When Jira cannot be reached it exits with code 5.

Fixing the workflow is done in Jira, by someone allowed to change it. The
`setup` skill walks through it with you; TCW changes nothing in a Jira
workflow itself.

## Adopting tickets

A ticket written in Jira becomes an item when it is **adopted**.

`tcw work tickets list` prints the tickets waiting, one key per line, oldest
first; `--json` gives each one's key, summary, status, creation time,
reporter, web address and description. By default these are the tickets of
this Jira project at the inbox status with no `TCW Item` yet. A project can
offer more with its own Jira query,
[`work.jira.inbox-query`](../../skills/configure/references/jira.md#workjirainbox-query).
Either way, the list holds only tickets that adopting would accept: in this
Jira project, at the inbox or request status, and not already an item.

`tcw work tickets adopt <KEY>` makes one an item:

```sh
tcw work tickets list
tcw work tickets adopt SHOP-42      # prints shop.work/SHOP-42-refund-a-payment
```

It fills in the ticket's `TCW Project` and `TCW Item`, writes the item's
folder, and moves the ticket to the request status. A ticket further along
than the request status is refused: adopting it would skip stages with no
trace. Adopting runs the `request` stage's `post`
hooks, as a move into `request` would, and no `pre` hooks or gates; a
project's `post` hook, such as the
[git example](configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds),
therefore runs for an adopted item. Creating an item with `tcw work new` runs
no hooks.

## QA on the ticket

The `qa` stage's record is kept in Jira: the decision is the ticket's next
status, not a file. So a bare `tcw work advance` from `qa` is refused, because
TCW cannot read a verdict Jira keeps. Moving on names the target and gives a
reason, which is recorded as a comment on the ticket:

```sh
tcw work advance SHOP-42 --to completed --reason "accepted by Dana: every QA plan scenario passes"
tcw work advance SHOP-42 --to implement --reason "rejected by Dana: refunds over 30 days still fail"
```

A rejection's reason is the comment the implementation reads next.

## What each command changes on a ticket

- **`tcw work new "<title>"`** creates the ticket, with its summary, request,
  properties, `TCW Project` and `TCW Item`, then writes the item's folder.
  With `--parent <item> --nest`, the folder is made inside the parent's, and
  `TCW Item` holds the nested full identifier. Standard output is the new
  item's full identifier, or the ticket's key when TCW stopped after creating
  the ticket.
- **`tcw work edit <item>`** changes the ticket's summary, priority, effort,
  complexity, labels and assignee, and its Jira parent and "blocks" links.
- **`tcw work advance <item>`** and **`tcw work discard <item>`** apply a
  transition, and post a comment when the move carries a reason.
- **`tcw work comment <item>`** posts a comment.
- **`tcw work tickets adopt <KEY>`** fills in `TCW Project` and `TCW Item` and
  moves the ticket to the request status.
- **`tcw work move <item>`** and **`tcw work rename <item> <new-name>`** edit the
  `TCW Item` of the item's ticket and of the ticket of every item nested in
  it, then move or rename the folder. They change no other field.

### Moving and renaming an item

A move or rename changes an item's full identifier, so it changes the
`TCW Item` of every ticket whose item's folder moves: the item's own and those
of the items nested in it. TCW first reads each of those tickets, and stops
before any edit when one is missing, or holds a value that is neither the old
full identifier nor the new one. A ticket still holding a TCW 3.x value stops
it with exit code 3, `<KEY> still holds a TCW 3.x TCW Item; run 'tcw migrate'
in this project first`. It then sets each ticket, and moves or renames the
folder last. A rename keeps the key at the front of the folder's name.

When Jira refuses an edit, or cannot be reached part way, the command stops
with exit code 1 or 5, leaves the folder where it was, and names the tickets
it set and those `still to be set`, ending with `run the same command again
to finish the move` and the command. Running it again skips each ticket that
already names the new full identifier and finishes the rest. On success it
prints one `<old full id> -> <new full id>` line per identifier it changed,
as in filesystem mode ([the work guide](work.md) describes moving and
renaming).

## Parents and blockers Jira cannot link

Jira links only tickets on one site. A parent or blocker given to
`tcw work new` or `tcw work edit` becomes a Jira link when it is an item of
this project, or an item of another Jira-mode project whose tickets are on the
same site. Anything else, such as an item of a filesystem-mode project, or of
a project whose tickets are on another site, is **recorded** in the item's
`tcw-work-item.yaml` instead, and the command says so:

```
shop.work/SHOP-42-refund-a-payment's blocker app.work/2026-10-01-checkout is not a ticket on https://example.atlassian.net, so it is recorded in docs/work/SHOP-42-refund-a-payment/tcw-work-item.yaml and Jira shows no link for it
```

**Jira does not show a recorded reference**: a person reading the ticket in
Jira sees no parent or "blocks" link for it. TCW reads it from the folder as
the item's parent or blocker, so `tcw work show` lists it with the item's
other references, and `tcw validate` checks it without contacting Jira.
Setting the parent to a ticket on this site later removes the recorded one;
`--parent ''` removes both. The web viewer's create form accepts a blocker or parent in another
project the same way, and shows the same sentence as a warning.

## Working on another project's items

A command changes only the project it is run in. An item of another project,
Jira-mode or not, is changed by running the command in that project with the
global option `-C`, which runs `tcw` as if it had been started in that folder:

```sh
tcw project path app                           # prints app's folder
tcw -C <folder> work new "Support refunds"
tcw -C tcw://app.path/ work edit app.work/2026-10-01-checkout --priority high
```

`tcw://app.path/` is the address of the project `app`'s folder on this
machine. The command then reads that project's own `.tcw/tcw-config.yaml`
and uses that project's Jira settings, never this one's. Naming another
project's item to a command that changes it, from here, is refused with exit
code 3, and the message gives the `tcw -C` to run instead:

```
tcw work edit: app.work/2026-10-01-checkout belongs to project 'app'; run the command there: tcw -C <folder> …
```

In 3.x, a project's entry for another project could carry a `jira` block,
used to create tickets in that project from here; in 4.0 there is no such
block, and `tcw migrate` drops it from the configuration and reports it (the
[migration guide](../migration-guide-3.X-to-4.0.0.md) has the details). The
item is made in that project, with `tcw -C`.

`-C` works only for a project on this machine. Reading another project's
items (`tcw work show`, or `tcw work list` with `--scope`) works from here.
[Related projects](multi-repo.md) covers parent links and finding a project's
folder, and [the command line](cli.md) covers `-C` and `--scope`.

## Several projects in one Jira project

Several TCW projects may keep their tickets in one Jira project; each ticket's
`TCW Project` field says which TCW project it belongs to. When one command
reads several projects, such as `tcw work list --scope down` in a parent,
projects that share one Jira site and Jira project, one account (the same
email and the same token) and one stage mapping (the same status for each
stage) are read with one search, and each ticket is given to the project its
`TCW Project` names. Projects that differ in any of these are read with a
search each. A search is kept only for the rest of that command, or, in the
web viewer, for the rest of one request; a write to Jira in the same command
or request makes the next search ask Jira again, so it sees the write.

## Tickets that still hold a TCW 3.x value

In 3.x, `TCW Item` held the project's ID and the folder name joined by a
slash, such as `shop/SHOP-42-refund-a-payment`; in 4.0 it holds the full
identifier. `tcw migrate`, which moves a 3.x project to 4.0, converts the
files first and then edits the `TCW Item` of each ticket in the project's Jira
project whose `TCW Project` names it and that still holds a 3.x value,
whatever its status. It changes no other field of any ticket. Each edit is a
line on standard error, `edit <KEY>: C17 TCW Item: <old> -> <new>`, and
`--dry-run` prints the same lines starting `would` and changes nothing.

Until those edits are made, such tickets are left out of `tcw work list` with
one warning that names their keys and `tcw migrate`, and `tcw validate
--remote` reports each one as an error. That happens between a
`tcw migrate --no-jira` run, which converts the files only and never
contacts Jira, and the run that finishes; and after a run that stopped part
way through the tickets, which says `run 'tcw migrate' again to finish`.
Running `tcw migrate` again edits the tickets still left. The
[migration guide](../migration-guide-3.X-to-4.0.0.md) walks through the whole
move.

## What needs the network

Every command that reads or changes an item asks Jira: `new`, `list`, `show`,
`edit`, `advance`, `discard`, `comment`, `move`, `rename`, `tickets`, and
`stage prompt` or `path` for a named item. When Jira cannot be reached they
exit with code 5. When `work.jira.site` names a host that answers but is not
a Jira site, so Jira answers "not found" for something every site has, they
exit with code 1 and ask you to check that `work.jira.site` names your Jira
site; a ticket or project that does not exist is still exit code 4.

A move whose transition has no screen records its note as a separate
comment, after the move. If the connection fails while that comment is being
posted, TCW reads the ticket's newest comments to see whether Jira received
it, and says nothing if it did. Otherwise the move stands and the command
exits with code 6: either the note was not posted, or, when the comments
cannot be read either, it may have been, and you should read them with
`tcw work show <item>` before adding it with `tcw work comment`.

These work offline: `tcw validate` without `--remote`, which never calls Jira;
`tcw work lifecycle`, `tcw work docs` and `tcw work tags`; and
`tcw work stage prompt <stage>` with no item. A `tcw://` link to a work item is
checked offline too, by whether the item's folder exists.

## Names of people

`tcw work show` prints display names for the assignee and for each comment's
author. `--json` carries Jira account IDs instead, which do not change when a
person changes their name.

## Limits

- **Jira Cloud only.** Self-hosted Jira (Server and Data Center) is not
  supported.
- **Two people adopting the same ticket at the same moment** are not kept
  apart: TCW takes no lock in Jira. Agree who sorts the inbox, and check the
  ticket with `tcw work show` afterwards if you are unsure.
- **Team-managed Jira projects** may have no priority field. Items then have
  no priority, and `tcw work show` prints it empty.
- **Transition screens.** TCW fills in only the comment on a transition's
  screen; a transition whose screen requires anything else cannot be used by
  TCW.
- **One issue type and one status per stage.** A Jira-mode project creates
  tickets of one issue type, and every enabled stage maps to its own status
  of that type's workflow, so `tcw work advance` always moves the ticket.
  Only `spec`, `plan`, `review`, `qa` and `postmortem` can be turned off, and
  a turned-off stage is skipped, not kept in files. There is no way to keep
  some stages local while the ticket stays where people left it, to map
  stages differently for different issue types, or to have a
  filesystem-mode item take its request from a ticket or comment on it.
  A team whose workflows cannot change keeps its projects in filesystem
  mode, and records the ticket's key in the item's request (and copies what
  the ticket needs back by hand). The two TCW fields are needed only in Jira
  mode. Loosening these limits belongs to the work-system overhaul planned
  for TCW 5.0; 4.0 keeps the requirements 3.x had.
