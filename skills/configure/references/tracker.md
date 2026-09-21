# Connect an external tracker

A node connects to an external tracker for `tcw work tracker list` and `show`,
which read tickets; for `import`, which claims a ticket through the workflow
transition named in `transitions.start`, and `link`, which only records a binding unless `--sync-status` asks it to bring the ticket up to date;
and for the lifecycle commands, which claim a bound item's ticket at `start` and
move it to the statuses under `statuses` as the item moves. What those commands do, which
file a tracker problem names, and what a malformed block does at runtime is in the
`work` skill's `commands.md`. This document is how to set the connection up,
in one node or shared from a parent node.

```yaml
work:
    tracker:
        provider: jira-cloud
        base-url: https://yourcompany.atlassian.net
        candidate-query: assignee = currentUser() AND status = "To Do"
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            start: Start Progress
        statuses:
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do
        timeout-seconds: 15
```

Configured under `work.tracker` in the node sentinel: `provider` (only
`jira-cloud`), `base-url`, `candidate-query`, `credentials.email-env`,
`credentials.token-env`, `transitions.start`, and optional `statuses`, `pre-backlog`,
`strict`, `comments`, `link`, `inbox-query`, `exclusive-claim-transition` and
`timeout-seconds` (default 15). All but the optional ones are required once the node's block is merged with
its ancestors' blocks (below), so a node can set only the keys that differ from its
parent's. Unknown keys are reported rather than
ignored, so a config written for a later release complains instead of silently doing
less.

`inbox-query` is optional JQL selecting tickets awaiting triage, which
`tcw work inbox list` reports beside raw intake; it is separate from
`candidate-query` (tickets ready to take). Blank or not a string is a problem, which
disables the whole block like any other; it inherits like every other scalar key.

**Credentials are named, never stored** — the config holds two environment variable
names, read at request time. Set those two variables in the shell that runs `tcw`;
never write the email address or the token into `tcw-config.yaml`.

`transitions.start` is the name of the tracker's workflow transition that starts
a ticket, exactly as the tracker spells it. `tcw` cannot tell a wrong name from a
ticket that simply does not offer it yet, so copy it from the project's workflow.

`transitions` also takes `submit`, `rework`, `complete` and `discard`, all optional.
Each names the transition that move should use, for a workflow where the target
status cannot identify one — two transitions ending in `Done`, one for finished work
and one for abandoned work, is the usual case, and without a name neither `complete`
nor a discard can sync at all. `discard` takes one name or one per discard resolution
(`wontfix`, `duplicate`, `superseded`), and unlike `statuses.discarded` under strict
mode it may be partial: it exists to disambiguate, so name only what is ambiguous.
A move with no entry keeps deriving its transition from the status. `start` is the
exception and is required: a start applies its transition through the claim rather
than deriving it from the status, so there is nothing for it to fall back to. A named
transition the ticket does not offer, or that matches twice, or that leads to a
status other than the mapped one, is refused rather than ignored. **Upgrade every
copy of `tcw` first:** version 2.3.0 and earlier report the four optional keys as
unknown and treat the whole tracker block as broken.

**`transitions.start` was called `transitions.claim` in version 2.3.0 and earlier**,
when claiming a ticket and starting one were the same act. The old spelling is not
accepted. Since it was a required key, every tracker-backed node has one to change —
one word, with the value left as it is. `tcw validate` reports it by name:

```
tcw-config.yaml: work.tracker.transitions.claim: renamed to
work.tracker.transitions.start, the transition the start move applies, alongside
submit, rework, complete and discard
tcw-config.yaml: work.tracker.transitions.start: required
```

It is reported against the file that wrote it, which in a shared workspace is the
parent node holding the settings, not the child being validated.

`exclusive-claim-transition` is optional, sits at the top level of `work.tracker`
rather than under `transitions`, and is the transition `tcw work tracker claim`
asserts through. **Leave it unset unless the project needs it.** Unset, a claim
applies no transition at all: it assigns the ticket, reads it back, and leaves the
status alone. Set, a claim applies the named transition before assigning, so that
on a workflow refusing a second claimant the second person is stopped before they
reach the assignment — and **the ticket moves**, which is the thing an unset claim
avoids. Name it only where the workflow really does exclude, and where that
guarantee is worth a status change on every claim.

It is not `transitions.start` under another name. That one is the transition a
`tcw work start` applies; this one is how a claim proves it is exclusive. Setting
either has no effect on the other. **Upgrade every copy of `tcw` first:** version
2.3.0 and earlier report this key as unknown and treat the whole tracker block as
broken, which disables every `tcw work tracker` command rather than just this.

`statuses` names the tracker **status** (not transition) a bound ticket should be in
for each local status: `active`, `review`, `completed`, `discarded`. Names match
ignoring case and extra spaces. Every key is optional and an unmapped status sends
nothing, but **`active` is required once any other key is set**, because each move
checks the ticket is where the previous status left it. `discarded` may instead map
discard resolutions to statuses —

```yaml
        statuses:
            active: In Progress
            discarded:
                wontfix: Won't Do
                duplicate: Duplicate   # superseded, unmapped, sends nothing
```

An unknown key, a blank or non-text name, a resolution other than `wontfix`,
`duplicate` or `superseded`, or a block without `active` is a problem `tcw validate`
reports, and the whole tracker block then reads as not configured. Like
`credentials` and `transitions`, `statuses` merges from ancestors key by key.

`create` says how to make a ticket for an item that has none, which is what
`tcw work tracker create` needs before it will run. `project` is required — every
other setting here finds tickets by *query*, and a query carries no project of
its own. `issue-type` names the type to make, `issue-types` overrides it for an
`epic` or a `bug` (epic wins), `components` is a list of component names, and
`on-new: true` makes filing an item create its ticket. An unknown key, a blank or
non-text name, a rule other than `epic` or `bug`, or a `create:` with nothing
under it is a problem `tcw validate` reports, and the whole tracker block then
reads as not configured.

```yaml
        statuses:
            backlog: To Do          # required before `create` will run
            active: In Progress
        create:
            project: EX
            issue-type: Task
            issue-types:
                epic: Epic
                bug: Bug
            components: [Platform]
            on-new: false
```

**`statuses.backlog` is where a created ticket is put, and `create` refuses
without it.** Jira decides which status a new issue starts in, and in a project
with a triage column that is usually the status `inbox-query` selects — so a
ticket left there comes back as new inbound work. A project that already sets
`statuses` has to add `backlog` before its first `tracker create`.

**`pre-backlog` maps each tracker status a ticket waits in before the backlog to
the transition name that takes it to the configured backlog** (tracker status →
transition name to `statuses.backlog`). Set it when tickets arrive in a triage
column the start transition is not offered from:

```yaml
        statuses:
            backlog: To Do          # required when pre-backlog is set
            active: In Progress
        pre-backlog:
            Triage: Accept
```

Anything that claims a ticket — `tracker import`, `inbox accept`, `start`,
`link --sync-status`, `sync` — then applies `Accept` first. `tcw validate` reports
a non-mapping, a blank status or transition, the same status listed twice
(compared ignoring case and spacing), a status that is also mapped under
`statuses`, and `pre-backlog` without `statuses.backlog`. It merges from ancestors
key by key, like `statuses`. Without it, TCW never takes a ticket out of triage, and
the refusal names the key. User-facing detail: `docs/guide/jira.md`, "Tickets
waiting in triage".

`strict: true` makes a claimed ticket required for local work (what it refuses is in
`commands.md`, "Strict mode"). It must be a boolean, and it needs `statuses.active`,
`statuses.completed`, and `statuses.discarded` as one status name or a mapping of all
three of `wontfix`, `duplicate` and `superseded` — otherwise `tcw validate` reports
the missing key. A block with problems does **not** turn strict mode off: gated
commands refuse until it is fixed. Turn strict mode off with `strict: false` or by
removing the key; it merges from ancestors like any other key.

**`strict: true` and `create.on-new: true` may both be set.** Strict mode refuses
`tcw work new` for everything except an epic, and creation-on-filing covers
epics, so the pair means "tasks come from tickets, epics filed here get theirs
made". Nothing else is filed, so nothing else gets a ticket this way.

```yaml
        strict: true
        statuses:
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do
```

`comments: true` posts a short progress comment on a bound ticket for each lifecycle
move (what is posted, and when, is in `commands.md`, "Progress comments"). It must
be a boolean and defaults to `false`, so mapping `statuses` alone never starts
commenting. `link` adds a URL to each comment. It must start `https://` or
`http://`, and its only placeholders are `{project}` (the TCW project id) and
`{slug}`, each percent-encoded. Any other placeholder is a problem `tcw validate`
reports. A `link` with comments off does nothing and is not a problem, so a child
node can set `comments: false` under a parent that sets both.

```yaml
        comments: true
        link: https://tcw.example.com/work/{slug}
```

- **Use a link that survives a move.** A team hosting `tcw serve` can link each
  item's page, as above. A link into a Git host's file tree breaks at the next move,
  because the item's folder is named by its status. The web app serves a child
  project's items under its path, not its id, so `{project}` does not rebuild that
  path; write the path into the template instead. An item removed by `work.retain`
  leaves a dead link.
- **Jira Service Management:** a comment may be visible to customers. Leave
  `comments` off there unless item titles may be seen.
- **Upgrade every copy of `tcw` first.** An older copy reports `comments` and `link`
  as unknown keys and treats the whole tracker block as broken. Its moves are then
  recorded as pending, and under strict mode it refuses gated commands.

## Sharing settings from a parent node

**Settings inherit from parent nodes, opt-in.** A node whose own `work.tracker` is a
non-empty mapping takes every key it leaves out from its ancestors (direct parent
first, all the way up, including nodes without a board). The nearest file wins each
key; `credentials` and `transitions` merge key by key; a nearer `null` lets the
farther value through. A node with no block, or `tracker: {}`, has no tracker and no
problems whatever its ancestors hold — there is no `tracker: none`. Rules to know:

- **`credentials` must come from the same file as `base-url`, or a nearer one.** A
  child that sets `base-url` — even to its parent's value — and inherits
  `credentials`, or either one of its keys, has no tracker, and `validate` says why.
- **A node with a board that holds shared settings is checked like any tracking
  node**, so it needs its own `candidate-query`. Keep shared settings in a node
  without a board instead.

A parent holding the shared settings, and a child that sets only its own query:

```yaml
# the parent's tcw-config.yaml (a node without a board)
work:
    tracker:
        provider: jira-cloud
        base-url: https://yourcompany.atlassian.net
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            start: Start Progress
```

```yaml
# the child's tcw-config.yaml
work:
    tracker:
        candidate-query: project = BILLING AND status = "To Do"
```

The parent must be connected to the child through `connected-projects` (see
`projects.md`); ancestors are found through that graph, not by folder.

**Turning an ancestor's tracker off for one node.** Leave `work.tracker` out of
that node, or write `tracker: {}`: the node then has no tracker at all. That
turns the tracker off only for the node that writes it: an ancestor's empty
block is skipped when blocks are merged, so that node's child projects still
inherit from farther up. A node
cannot keep its own tracker block while refusing a key an ancestor sets, because a
`null` lets the farther value through; to use different values, set them in the
node's own block, where the nearest file wins.

## After editing

Run `tcw validate` after editing the block. It checks the merged shape and names
each problem with the file its value came from, and it never contacts the tracker.
Then run `tcw work tracker list` to confirm the query and the credentials work.
