As a user, I run `tcw work list` to list my project's work items, one full
identifier (`<project>.work/<folder>`) per line, so a script can read it. It shows unfinished work — inbox items and
items with no readable stage included — and hides finished items, `completed`
and `discarded`; `--all` shows everything.

I narrow it with `--stage <stage>` (repeatable), `--tag <tag>` (repeatable;
an item carrying any of them matches), `--parent <item>`, `--assignee
<name>` and `--mine`, the items assigned to me
(`tcw://C/work/tell-tcw-who-i-am`). `--stage` and `--all` together are refused, since they ask for two
different sets. `--json` prints each item's full record, the same one
`tcw work show --json` gives.

A folder in the work store that is not an item, or a plain file, is ignored.
An item whose `item.yaml` cannot be read makes `list` exit 1 naming the file,
because a list that silently left it out would read as complete.

In a project that keeps its items in Jira, a ticket whose `TCW Item` field
still holds a TCW 3.x value is left out, and one warning on standard error says
how many were, names their keys, and names tcw migrate.

Items are listed at any depth of the work store, each by its id-path.

`--scope` chooses which projects the board covers ([Choose which projects a list or show command covers](tcw://C/cli/choose-which-projects-a-list-or-show-command-covers)): `own`, the default, is my project alone; `up` adds each ancestor's own items, `down` each descendant's, and `all` both, each project with its own items, in scope order. `--project <id>` keeps one covered project's items. `--parent <item>` finds an epic's parts filed in any covered project, and `children` and `blocks` in each record are computed across the scope. A project the scope covers that is not on this machine, or cannot be read, is named on standard error as `warning: '<id>' is unavailable, so …`, with its reason, and in the `--json` document's `projects`; the command still exits 0.
