# Using TCW with Jira

A project whose `tcw-config.yaml` sets `work.backend: jira` keeps its work items
on Jira tickets. This guide is for both sides of that arrangement: the people
outside engineering who write and follow tickets in Jira, and the engineers
and agents who work the items with `tcw`. Everything about items that does not
depend on the backend, such as the stages, the item folder and moving an
item, is in [the work guide](work.md).

## Who owns what

Each fact about an item has one home, and nothing is copied between the two:

| Jira owns | The repository owns |
| --- | --- |
| the request (the ticket's description) | the spec, the plan and every round |
| the status, which is the item's stage | handoffs for the stages worked in the repository |
| the assignee | the item's declared record changes, `capabilities.yaml` |
| priority, effort and complexity | the taxonomy and the capabilities |
| labels, which are the item's tags | |
| the parent, and "blocks" links | |
| comments | |

In the repository, each item still has a folder in the work store, named with
the ticket's key, `TCW-42-refund-a-payment`. Its `item.yaml` holds only the
ticket's address; everything else in the folder is the technical record. The
taxonomy and capabilities are never stored in Jira: they describe the product,
and they live and change with its code.

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
missing and proposing wording, and never rewrites the description itself.

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

- **Two custom fields** tie a ticket to an item: a text field holding the TCW
  project's ID (`TCW Project`) and one holding the item's slug (`TCW Item`).
  They must be on both the issue type's create screen and its edit screen.

Every key, its default and its rules are in the configure skill's
[`jira.md`](../../skills/configure/references/jira.md). Each project states its
own `work.jira` block; nothing is inherited from another project. The `setup`
skill walks through a first setup.

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
what the item folders hold on their own: each folder's name and `item.yaml`, a
ticket key used by two folders, a record folder for a stage Jira keeps, and
the latest `review` round. The checks that need an item's properties, which
Jira holds, wait for `--remote`.

`tcw validate --remote` also reads Jira, and changes nothing there. It prints
findings only, one per line: a status that does not exist, a move between two
stages that no transition offers, a transition screen that asks for a field
other than the comment, a configured field missing from a create or edit
screen, and an item folder whose ticket is missing or names another item. It
then runs the work-item checks plain `tcw validate` runs in a filesystem-mode
project: a `parent` or `blocked-by` naming an item that does not exist, an
item whose stage is ahead of its documents, and each unfinished item's
`capabilities.yaml`. A move it could not check, such as one with no ticket at
that status to try, is a finding too. When Jira cannot be reached it exits
with code 5.

Fixing the workflow is done in Jira, by someone allowed to change it. The
`setup` skill walks through it with you; TCW changes nothing in a Jira
workflow itself.

## Adopting tickets

A ticket written in Jira becomes an item when it is **adopted**.

`tcw work tickets list` prints the tickets waiting, one key per line, oldest
first; `--json` gives each one's key, summary, status, creation time,
reporter, web address and description. By
default these are the tickets of this Jira project at the inbox status with no
`TCW Item` yet. A project can offer more with its own Jira query,
[`work.jira.inbox-query`](../../skills/configure/references/jira.md#workjirainbox-query).
Either way, the list holds only tickets that adopting would accept: in this
Jira project, at the inbox or request status, and not already an item.

`tcw work tickets adopt <KEY>` makes one an item:

```sh
tcw work tickets list
tcw work tickets adopt SHOP-42      # prints shop/SHOP-42-refund-a-payment
```

It fills in the ticket's `TCW Project` and `TCW Item`, writes the item's
folder, and moves the ticket to the request status. A ticket further along
than the request status is refused: adopting it would skip stages with no
trace. Adopting runs the `request` stage's `post` hooks, as a move into
`request` would, and no `pre` hooks or gates; a project's `post` hook, such as
the [git example](configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds),
therefore runs for an adopted item. Creating an item with `tcw work new`, and
creating one in another project, run no hooks.

## QA on the ticket

The `qa` stage's record is kept in Jira: the decision is the ticket's next
status, not a file. So a bare `tcw work advance` from `qa` is refused, because
TCW cannot read a verdict Jira keeps. Moving on names the target and gives a
reason, which is recorded as a comment on the ticket:

```sh
tcw work advance SHOP-42 --to completed --reason "Checked every QA plan scenario; all pass"
tcw work advance SHOP-42 --to implement --reason "Refunds over 30 days still fail"
```

A rejection's reason is the comment the implementation reads next.

## Creating an item in another project

`tcw work new "<title>" --project <id>` creates an item in another connected
project's inbox. Standard output is the new item's slug, or the ticket's key
when TCW stopped after creating the ticket. When the target is on this
machine, TCW reads its own `tcw-config.yaml` and uses that project's Jira
settings, never this one's. When it is declared but is not on this machine:

- with a `jira` block in this project's entry for it, TCW creates the ticket in
  that project's Jira inbox, prints the ticket's key and exits 0;
- without one, the request is refused with exit code 3.

Creating an item in an upstream project is refused with exit code 3. The
configure skill's
[`projects.md`](../../skills/configure/references/projects.md#creating-an-item-in-another-project)
describes the `jira` block, and
[Working across repositories](multi-repo.md) walks through every case.

## What needs the network

Every command that reads or changes an item asks Jira: `new`, `list`, `show`,
`edit`, `advance`, `discard`, `comment`, `rename`, `tickets`, and
`stage prompt` or `path` for a named item. When Jira cannot be reached they
exit with code 5.

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
