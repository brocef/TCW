As a project that plans its work in Jira, I set `work.backend: jira` and a `work.jira` block in `.tcw/tcw-config.yaml`: the site, the Jira project key, the names of the two environment variables that hold my email address and API token, and, optionally, the display names of the TCW Project and TCW Item fields, given together, and of an effort and a complexity field. Jira then keeps each item's stage, request, comments, assignee, priority, estimates, labels, parent and blocking links, and the repository keeps the technical record: specs, plans and rounds, in one folder per item named `<KEY>-<title words>`, whose `tcw-work-item.yaml` holds the version of TCW that wrote it, the link to the ticket, and any parent or blocker Jira cannot link.

Each stage maps to one Jira status (`work.stages.<stage>.status`), and `tcw work advance` makes exactly one workflow transition into the target stage's status, recording any reason as a comment on the ticket in the same request. QA happens on the ticket: leaving qa takes a reason, and the stage keeps no files. `tcw work new` creates the ticket first and the folder second; `tcw work list --tag <tag>` asks Jira for tickets carrying that label. The `work.jira` block may come from a parent whose link passes `config`, key by key, so projects that share one Jira project write it once; `work.backend: jira` and the stage statuses are always written in the project itself. When a parent the block could come from is not on this machine, every command that opens the Jira-mode store stops with exit 7 before any request is made. A ticket key typed where an item is named (`tcw work show TCW-67`) finds the item whose folder carries that key. When a `--scope` covers several projects that keep their items in one Jira project on one site, sign in as the same account and map their stages to the same statuses, they are read with one search, and each project keeps the tickets its `TCW Project` field names, or, without the TCW fields, the tickets its own item folders name. TCW never changes git state, and plain `tcw validate` never reads Jira.

The TCW Item field, when configured, holds the item's full identifier,
`<project>.work/<folder>`. Without the TCW fields, the item folders are the
only record of which tickets are this project's items, and TCW never reads
or writes either field.

A parent or blocker that is a ticket on the same Jira site is a Jira link,
when it is in the same project or both projects have the TCW fields.
One that is not, such as an item of a project that keeps its items in files or
a ticket on another Jira site, is recorded in the item's state file by its full
identifier, and TCW says that Jira will not show it; `tcw validate` checks
those values without reading Jira. With the TCW fields, a rename or move sets the `TCW Item` of
every ticket whose folder moved, reading each ticket again just before its
edit, and never sets one back: one that stops can be finished by running the
same command again.

In Jira mode the item folder holds `tcw-work-item.yaml`; a ticket's key is found at any depth of the work store; and a full identifier never exceeds the 255 characters of the `TCW Item` field.
