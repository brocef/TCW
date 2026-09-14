# Connect an external tracker

A node connects to an external tracker for `tcw work tracker list` and `show`,
which read tickets, and for `import` and `link`, which claim a ticket through the
workflow transition named in `transitions.claim`. What those commands do, which
file a tracker problem names, and what a malformed block does at runtime is in the
`tcw-work` skill's `commands.md`. This document is how to set the connection up,
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
            claim: Start Progress
        timeout-seconds: 15
```

Configured under `work.tracker` in the node sentinel: `provider` (only
`jira-cloud`), `base-url`, `candidate-query`, `credentials.email-env`,
`credentials.token-env`, `transitions.claim`, and optional `timeout-seconds`
(default 15). All but the last are required once the node's block is merged with
its ancestors' blocks (below), so a node can set only the keys that differ from its
parent's. Unknown keys are reported rather than
ignored, so a config written for a later release complains instead of silently doing
less.

**Credentials are named, never stored** — the config holds two environment variable
names, read at request time. Set those two variables in the shell that runs `tcw`;
never write the email address or the token into `tcw-config.yaml`.

`transitions.claim` is the name of the tracker's workflow transition that starts
a ticket, exactly as the tracker spells it. `tcw` cannot tell a wrong name from a
ticket that simply does not offer it yet, so copy it from the project's workflow.

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
            claim: Start Progress
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
