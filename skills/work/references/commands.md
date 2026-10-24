# Command reference

Every `tcw work` command, from `tcw work --help` and each command's own
`--help`, which is the authority when this page and the CLI disagree. Standard
output carries only what a command produces, one identifier per line, with
details through `--json`; everything said to a person goes to standard error.

| Goal                                     | Command                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item                           | `tcw work new "<title>" [--priority <p>] [--effort <e>] [--complexity <c>] [--tag <t> ...] [--assignee <name> \| --assign-me] [--parent <slug>] [--blocked-by <slug> ...]`, with what it asks for on stdin. It starts at request; `--stage inbox` starts it as an arrival (filesystem only). Prints the new slug |
| a part for another project               | `tcw -C <folder> work new "<title>" --parent <slug>`, where `<folder>` is its folder or `tcw://<id>.path/`                                                                                                                                                                                                   |
| list unfinished items                    | `tcw work list [--stage <s> ...] [--tag <t> ...] [--parent <slug>] [--assignee <name> \| --mine] [--all] [--json]`; each repeated flag matches any of its values; `--all` adds completed and discarded items                                                                                                     |
| read an item                             | `tcw work show <slug> [--json]`: its properties, its request, then its comments, newest first                                                                                                                                                                                                                    |
| a path                                   | `tcw work path` (the store) · `tcw work path <slug>` (the item's folder) · `tcw work path <slug> <stage>` (a stage's document or folder) · `--next` (the stage's next round) · `--handoff` (a new handoff file). Exits 3 for a stage the backend keeps                                                           |
| move an item                             | `tcw work advance <slug> [--to <stage>] [--dry-run]`; prints the stage it is at after the move                                                                                                                                                                                                                   |
| move past a refusing gate                | `tcw work advance <slug> --force --reason "<why>"`                                                                                                                                                                                                                                                               |
| abandon an item                          | `tcw work discard <slug> --reason "<why>"`                                                                                                                                                                                                                                                                       |
| add a comment                            | `tcw work comment <slug>`, with the text on stdin                                                                                                                                                                                                                                                                |
| change properties                        | `tcw work edit <slug> [--title <t>] [--priority <p>] [--effort <e>] [--complexity <c>] [--tag <t>] [--untag <t>] [--assignee <name> \| --assign-me] [--parent <slug>] [--blocked-by <slug>] [--unblocked-by <slug>]`; an empty value clears a single-valued property                           |
| rename the folder                        | `tcw work rename <slug> <new-name>`, the words after the date; prints the new slug                                                                                                                                                                                                                               |
| a stage's instructions                   | `tcw work stage prompt <stage> [<slug>] [--no-exec]`; runs no checks                                                                                                                                                                                                                                             |
| a procedure                              | `tcw work procedure <id> [<slug>] [--no-exec]`, one of `documentation-sync`, `create-work`, `audit-backlog`, `search`, `triage-issues`, `unattended-work`, `pause-work`. Outside a TCW project, TCW's own text                                                                                                   |
| the stage table and bindings             | `tcw work lifecycle [--stage <s>] [--json]`                                                                                                                                                                                                                                                                      |
| documentation entries                    | `tcw work docs [--json]`: the documents this project keeps in step with its code                                                                                                                                                                                                                                 |
| tags                                     | `tcw work tags list` · `tcw work tags add <tag> ...` · `tcw work tags rm <tag> ...`; see [`tags.md`](tags.md)                                                                                                                                                                                                    |
| Jira arrivals                            | `tcw work tickets list [--json]` (tickets not yet items; `--json` carries summary, status, reporter, link and description) · `tcw work tickets adopt <KEY>` (make one an item at request)                                                                                                                        |
| check the project                        | `tcw validate` · `tcw validate --remote` (a Jira-mode project against Jira)                                                                                                                                                                                                                                      |
| obtain what is declared but missing here | `tcw provision [--component <axis>] [--dry-run]`                                                                                                                                                                                                                                                                 |
| the projects this one declares           | `tcw projects list`                                                                                                                                                                                                                                                                                              |

## Exit codes

| Code | Meaning                                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | done                                                                                                                                                       |
| 1    | the backend or TCW failed                                                                                                                                  |
| 2    | a malformed command or value                                                                                                                               |
| 3    | refused: a gate, a name collision, or a record that depends on this one                                                                                    |
| 4    | not found: no such item, term, capability, tag or ticket                                                                                                   |
| 5    | unreachable: Jira, or a declared project not on this machine                                                                                               |
| 6    | the item moved, but something after the move failed                                                                                                        |
| 7    | something this project inherits is not available here: a project it inherits from is not on this machine, or that project's parent links could not be read |

On exit 3 from `advance`, read standard error: it names the gate and why. Do
not reach for `--force` to get past a gate you have not understood; it needs a
reason because a person will read it.

## Addressing an item

An item's full slug is `<project>/<folder>`, where the folder is
`<date>-<words>`. Inside its own project the folder name alone is enough.
Another project's slug opens that project for reading; writes to another
project's item are refused, so run them in that project. In Jira mode a ticket
key is accepted wherever a slug is, for an item that has one. Report slugs in
full when they cross projects: a bare folder name from another project
addresses nothing.

## What an item holds

The item's folder, `tcw work path <slug>`, holds one folder per stage it has
reached that writes something: a document (`request`, `spec`, `plan`,
`postmortem`) or numbered rounds (`implement`, `review`, `qa`). Handoffs sit in
the stage's folder beside them. `capabilities.yaml` sits in the item's folder
itself. Always get a path from `tcw work path`; the layout is TCW's to change.

**Rounds.** Each pass through implement, review or qa writes the next
`round-N.md`, from `tcw work path <slug> <stage> --next`. Review and qa rounds
open with front matter:

```yaml
---
verdict: accepted # or rejected
judges: 3 # the newest implement round
---
```

A verdict whose `judges` is not the newest implement round's number is stale,
and a stale verdict lets nothing through.

**Comments.** `tcw work comment` adds one; `tcw work show` reads them. A move
writes one too, carrying its reason. A comment whose first line is `QA plan`
is the item's QA plan; one whose first line is `Handoff` is a handoff for a
stage the backend keeps.

## Piping text in

`tcw work new` and `tcw work comment` read their text from stdin; so do
`tcw taxonomy add` and `tcw capabilities add`. Reading is bounded: with nothing
piped the command goes on without text and warns, so a script that leaves its
own stdin open cannot hang it. A stream that starts and then stalls is refused
(exit 1, nothing written) rather than stored cut short. `TCW_STDIN_TIMEOUT`
sets the bound in seconds; `0` never waits. Use a quoted heredoc
(`<<'MD'`) so the shell expands nothing in the text.

## Amending a request

Something that changes what an item asks for after it was written up is an
amendment. Add it under a dated `## Added <YYYY-MM-DD>` heading saying where it
came from, and never rewrite what is there. Where the request is a file, that
is the document `tcw work path <slug> request` names. Where the backend keeps
the request (in Jira, the ticket's description), post the amendment as a
comment instead, first line `Added <YYYY-MM-DD>`.

## Renaming an item

`tcw work rename <slug> <new-name>` changes the words after the date, keeping
the date. Every item in this project that names it as its parent or as a
blocker is updated to the new slug; text that names the old slug is not. The title is separate:
`tcw work edit <slug> --title "<title>"`.

## Documentation entries

`tcw work docs` prints the documents this project keeps in step with its code,
each with the kind of change that should update it. The plan and implement
stage prompts include them, so a plan names a task for every entry it expects
to fire, and implement checks each once the change is finished.
