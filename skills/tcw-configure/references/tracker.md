# Connect an external tracker

A node can read tickets from an external tracker with `tcw work tracker list` and
`tcw work tracker show`. What those commands report, and what a malformed block
does at runtime, is in the `tcw-work` skill's `commands.md`. This document is how
to set the connection up.

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
(default 15). All but the last are required. Unknown keys are reported rather than
ignored, so a config written for a later release complains instead of silently doing
less.

**Credentials are named, never stored** — the config holds two environment variable
names, read at request time. Set those two variables in the shell that runs `tcw`;
never write the email address or the token into `tcw-config.yaml`.

`transitions.claim` is the name of the tracker's workflow transition that starts
a ticket, exactly as the tracker spells it. `tcw` cannot tell a wrong name from a
ticket that simply does not offer it yet, so copy it from the project's workflow.

Run `tcw validate` after editing the block. It checks the shape and names each
problem, and it never contacts the tracker. Then run `tcw work tracker list` to
confirm the query and the credentials work.
