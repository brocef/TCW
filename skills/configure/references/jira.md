# Configure the Jira backend

With `work.backend: jira`, each work item's properties, stage, request and
comments live on a Jira ticket, and its documents stay as files in the item's
folder. This document describes the keys that connect a project to Jira: the
`work.jira` block, and the `status` each stage maps to. Walking a user through
a first Jira setup, and fixing their Jira workflow with them, is the `setup`
skill's Jira reference. What each key does once items move is in the Jira
guide, `docs/guide/jira.md`, in the TCW repository.

A project may take its `work.jira` settings from a parent whose link passes
`config` (`projects.md`). They merge key by key: a key the project sets in its
own `.tcw/tcw-config.yaml` wins, and every key it leaves out comes from its
parents, so a family can keep one site, one pair of credential names and one
pair of field names in a shared parent while each child sets only `project`.
Two things are always the project's own: `work.backend: jira`, which each
Jira-mode project writes itself, and the stages with their statuses. When a
parent that could pass `work.jira` is not on this machine, a Jira-mode
project's `tcw work` commands that read or change items stop with exit code 7,
naming the setting and the parent. The guide [Using TCW with Jira](../../../docs/guide/jira.md)
says more.

```yaml
work:
    backend: jira
    jira:
        site: https://example.atlassian.net
        project: TCW
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_TOKEN
        fields:
            project: TCW Project
            item: TCW Item
            effort: Effort
            complexity: Complexity
        issue-type: Task
        timeout: 15
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

`site`, `project` and `credentials` are required, each set in this project's
file or passed down by a parent; every other key has a default, and `fields`
may be left out (see [Custom fields](#custom-fields)). An unknown key is reported. With
any problem in the block, every `tcw work` command refuses until it is fixed,
and `tcw validate` names each problem by its key.

## The connection

### `work.jira.site`

Shared: personal configuration cannot set it.

The Jira Cloud site, written `https://<host>`, with an optional port and no
path or trailing `/`.

### `work.jira.project`

Shared: personal configuration cannot set it.

The key of the Jira project that holds this project's tickets: at least two
characters, capital letters, digits and `_`, starting with a letter, such as
`TCW`.

### `work.jira.issue-type`

Shared: personal configuration cannot set it.

The issue type of the tickets TCW creates, `Task` by default. It must be an
issue type of the Jira project.

### `work.jira.inbox-query`

Shared: personal configuration cannot set it.

Optional. A Jira query (JQL) for more tickets to offer for adoption. By
default, `tcw work tickets list` offers the tickets of this Jira project that
are at the inbox stage's status and have no TCW Item yet (without the TCW
fields, those with no folder named for their key here). With
`inbox-query`, it offers those and the tickets the query matches.

### `work.jira.timeout`

Shared: personal configuration cannot set it.

How many seconds one request to Jira may take before it counts as failed: a
positive number, 15 by default.

### `work.jira.priorities`

Shared: personal configuration cannot set it.

The Jira priority name for each of TCW's five priorities, `highest`, `high`,
`medium`, `low` and `lowest`. By default they are `Highest`, `High`,
`Medium`, `Low` and `Lowest`, Jira's own names; map only the ones this Jira
project names differently:

```yaml
work:
    jira:
        priorities:
            highest: Blocker
```

A Jira project with no priority field leaves every item's priority empty.

## Credentials

The configuration never holds a credential. It names two environment
variables, and TCW reads their values only when it sends a request. Set them
in the shell that runs `tcw`. A value that does not look like a variable's
name is reported without being shown, since it may be a token pasted into the
wrong place.

### `work.jira.credentials.email-env`

Overridable: personal configuration may set it.

The name of the environment variable that holds the Jira account's email
address. One person may name a different variable in their personal
configuration, or with an override variable such as
`TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ` for project `my-proj`
(`personal.md`); outside a Jira-mode project, a personal value is set aside.

### `work.jira.credentials.token-env`

Overridable: personal configuration may set it.

The name of the environment variable that holds that account's Jira API
token. One person may name a different variable in their personal
configuration, as for `email-env`.

## Custom fields

TCW finds its custom fields by their names on the create screen of the
configured issue type. Each name must match exactly one field there, or every
command refuses and names the field. The fields must be on the issue type's
edit screen too, since TCW fills them in on tickets that already exist, and
`tcw validate --remote` reports one missing from either screen.

`project` and `item` are optional, but given together or not at all: one
without the other is a configuration problem that names the missing one.
With them, Jira itself records which TCW project and item each ticket is.
Without them, for a site where new custom fields cannot be added, the item
folders alone say which tickets are items and TCW never reads or writes
either field; an adoption then reaches other copies of the repository only
through git, nothing in Jira names a ticket's item, and turning the fields on
later leaves existing tickets to be filled in by hand, which `tcw validate
--remote` reports. The [Jira guide](../../../docs/guide/jira.md#running-without-the-tcw-fields)
lists every difference.

### `work.jira.fields.project`

Shared: personal configuration cannot set it.

The name of a text field (for example `TCW Project`) that holds the TCW
project ID a ticket belongs to. Optional, with `item`.

### `work.jira.fields.item`

Shared: personal configuration cannot set it.

The name of a text field (for example `TCW Item`) that holds the item's full
identifier, such as `shop.work/SHOP-42-refund-a-payment`.
A ticket with this field empty is not an item yet; adopting it fills the
field. Optional, with `project`.

### `work.jira.fields.effort`

Shared: personal configuration cannot set it.

Optional. The name of a single-choice field whose options are `Low`,
`Medium`, `High` and `Very High`, holding an item's effort. Without it, items
have no effort.

### `work.jira.fields.complexity`

Shared: personal configuration cannot set it.

Optional. The name of a single-choice field with the same four options,
holding an item's complexity.

## Stages and statuses

Each enabled stage maps to its own Jira status, through its
[`work.stages.*.status`](work.md#workstagesstatus) key: two stages mapped to
one status are refused, because TCW could not tell from a ticket which stage
it is at. The side stage, `postmortem`, has no status. A ticket's status is
the item's stage.

To move an item, TCW applies a Jira transition into the target stage's
status. When the ticket offers exactly one, TCW uses it. When it offers
several, TCW uses the one whose screen asks for nothing but a comment. When
that still leaves none, or more than one, the move is refused with exit code
3, and the message names the transitions it found. TCW never fills in a
transition screen's fields other than the comment.

## Checking the configuration against Jira

`tcw validate` checks the shape of everything above and never contacts Jira.
`tcw validate --remote` also reads Jira, and changes nothing there. It prints
one finding per line: a status that does not exist, a move between two
stages that no transition offers, a transition screen that asks for a field
other than the comment, and a configured field missing from the create or
edit screen. A check it could not make, such as a move with no ticket to
sample, is a finding too, not a pass.
