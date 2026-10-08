As a user, I run `tcw work list` to list my project's work items, one full slug
per line, so a script can read it. It shows unfinished work — inbox items and
items with no readable stage included — and hides finished items, `completed`
and `discarded`; `--all` shows everything.

I narrow it with `--stage <stage>` (repeatable), `--tag <tag>` (repeatable;
an item carrying any of them matches), `--parent <slug>` and `--assignee
<name>`. `--stage` and `--all` together are refused, since they ask for two
different sets. `--json` prints each item's full record, the same one
`tcw work show --json` gives.

A folder in the work store that is not an item, or a plain file, is ignored.
An item whose `item.yaml` cannot be read makes `list` exit 1 naming the file,
because a list that silently left it out would read as complete.
