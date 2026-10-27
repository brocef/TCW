# Command reference

Every `tcw work` command, from `tcw work --help` and each command's own
`--help`, which is the authority when this page and the CLI disagree. Standard
output carries only what a command produces, one identifier per line, with
details through `--json`; everything said to a person goes to standard error.

| Goal                                     | Command                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item                           | `tcw work new "<title>" [--priority <p>] [--effort <e>] [--complexity <c>] [--tag <t> ...] [--assignee <name> \| --assign-me] [--parent <slug> --nest] [--blocked-by <slug> ...]`, with what it asks for on stdin. It starts at request; `--stage inbox` starts it as an arrival (filesystem only). `--nest` puts the folder inside the parent's. Prints the new item's full identifier |
| a part for another project               | `tcw -C <folder> work new "<title>" --parent <full id>`, where `<folder>` is the folder `tcw project path <id>` prints, or `tcw://<id>.path/`; the part's folder is made at the top of that project's work folder                                                                                                                                                                       |
| list unfinished items                    | `tcw work list [--stage <s> ...] [--tag <t> ...] [--parent <slug>] [--assignee <name> \| --mine] [--all] [--scope own\|up\|down\|all] [--project <id>] [--json]`; each repeated flag matches any of its values; `--all` adds completed and discarded items; `--scope` adds related projects (`own`, the default, is this project alone) and `--project` keeps one of them               |
| read an item                             | `tcw work show <slug> [--scope own\|up\|down\|all] [--json]`: its properties, its request, then its comments, newest first; another project's item is read from that project                                                                                                                                                                                                            |
| a path                                   | `tcw work path` (the store) · `tcw work path <slug>` (the item's folder) · `tcw work path <slug> <stage>` (a stage's document or folder) · `--next` (the stage's next round) · `--handoff` (a new handoff file). Exits 3 for a stage the backend keeps                                                                                                                                  |
| move an item                             | `tcw work advance <slug> [--to <stage>] [--dry-run]`; prints the stage it is at after the move                                                                                                                                                                                                                                                                                          |
| move past a refusing gate                | `tcw work advance <slug> --force --reason "<why>"`                                                                                                                                                                                                                                                                                                                                      |
| abandon an item                          | `tcw work discard <slug> --reason "<why>"`                                                                                                                                                                                                                                                                                                                                              |
| add a comment                            | `tcw work comment <slug>`, with the text on stdin                                                                                                                                                                                                                                                                                                                                       |
| change properties                        | `tcw work edit <slug> [--title <t>] [--priority <p>] [--effort <e>] [--complexity <c>] [--tag <t>] [--untag <t>] [--assignee <name> \| --assign-me] [--parent <slug>] [--blocked-by <slug>] [--unblocked-by <slug>]`; an empty value clears a single-valued property. A parent or blocker may be another project's item, named by its full identifier                                   |
| rename the folder                        | `tcw work rename <slug> <new-name>`, the words after the date; the items nested in it move with it. Prints one `<old> -> <new>` line per changed identifier                                                                                                                                                                                                                             |
| move the folder                          | `tcw work move <slug> --into <id-path>` · `tcw work move <slug> --top`; the items nested in it move with it, and the `parent` field is not changed. Prints one `<old> -> <new>` line per changed identifier                                                                                                                                                                             |
| a stage's instructions                   | `tcw work stage prompt <stage> [<slug>] [--no-exec]`; runs no checks                                                                                                                                                                                                                                                                                                                    |
| a procedure                              | `tcw work procedure <id> [<slug>] [--no-exec]`, one of `documentation-sync`, `create-work`, `audit-backlog`, `search`, `triage-issues`, `unattended-work`, `pause-work`. Outside a TCW project, TCW's own text                                                                                                                                                                          |
| the stage table and bindings             | `tcw work lifecycle [--stage <s>] [--json]`                                                                                                                                                                                                                                                                                                                                             |
| documentation entries                    | `tcw work docs [--json]`: the documents this project keeps in step with its code                                                                                                                                                                                                                                                                                                        |
| tags                                     | `tcw work tags list` · `tcw work tags add <tag> ...` · `tcw work tags rm <tag> ...`; see [`tags.md`](tags.md)                                                                                                                                                                                                                                                                           |
| Jira arrivals                            | `tcw work tickets list [--json]` (tickets not yet items; `--json` carries summary, status, reporter, link and description) · `tcw work tickets adopt <KEY>` (make one an item at request)                                                                                                                                                                                               |
| check the project                        | `tcw validate` · `tcw validate --remote` (a Jira-mode project against Jira)                                                                                                                                                                                                                                                                                                             |
| obtain what is declared but missing here | `tcw project provision [<id>] [--component <axis>] [--dry-run]`: fetches the stores this project declares and the projects its family names that are not on this machine; with `<id>`, only that project and the projects it inherits from; where it may place each copy is in the skill's exit 5 rule                                                                                  |
| the projects this one is connected to    | `tcw project list [--json]`: this project first, then the projects it is connected to · `tcw project path [<id>]`: the folder a project is in on this machine                                                                                                                                                                                                                           |

## Exit codes

| Code | Meaning                                                                                                                                                                            |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | done                                                                                                                                                                               |
| 1    | the backend or TCW failed; the folder holds a TCW 3.x project, which every command refuses until `tcw migrate` moves it over; a full identifier names a project nothing here knows |
| 2    | a malformed command or value                                                                                                                                                       |
| 3    | refused: a gate, a name collision, a record that depends on this one, or a change to an object another project owns (the message names the `tcw -C` to run there)                  |
| 4    | not found: no such item, term, capability, tag or ticket                                                                                                                           |
| 5    | unreachable: Jira, or a related project the command had to read is not on this machine                                                                                             |
| 6    | the item moved, but something after the move failed                                                                                                                                |
| 7    | something this project inherits is not available here: a project it inherits from is not on this machine, or that project's parent links could not be read                         |

On exit 3 from `advance`, read standard error: it names the gate and why. Do
not reach for `--force` to get past a gate you have not understood; it needs a
reason because a person will read it.

## Addressing an item

An item's **full identifier** is `<project>.work/<id-path>`: the ID of the
project that owns it, its work store, and its id-path, the path of its folder
in that store. The folder is `<date>-<words>`, and a part nested in its
epic's folder has the id-path `<epic folder>/<part folder>`. TCW's help calls
the name `slug`, a nickname for the full identifier. Wherever a command takes
an item, it accepts:

- the full identifier, such as `app.work/2026-10-24-epic`, which can name an
  item of any project TCW can find;
- its address, the full identifier written after `tcw://`;
- the bare id-path, meaning the item at that path in the project the command
  runs in; a nested item needs its whole id-path, not its own folder alone;
- in Jira mode, a tracker key, such as `TCW-120` for this project's item
  carrying it, or `<project id>.work/TCW-120` for another project's.

The name must match exactly; a shortened one is not found (exit 4). Output
always prints the full identifier. Another project's item can be read by its
full identifier; a change to it is refused (exit 3) and the message names the
`tcw -C` that runs the command in its own project. Report full identifiers
when they cross projects: an id-path from another project names nothing here.

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

## Renaming and moving an item

`tcw work rename <slug> <new-name>` changes the words after the date, keeping
the date. `tcw work move <slug> --into <id-path>` puts the item's folder inside
another item's folder, or an organising folder it makes when missing (never
one named like a tracker key, such as `TCW-1`: that is refused with exit 2),
and `--top` puts it back at the top of the work folder; a move leaves the `parent`
field as it was, and a folder inside an item that is not its parent draws a
warning. Either way the items nested in the folder move with it, and every
reference to a moved item in this project's records and links is updated; it
prints one `<old> -> <new>` line per identifier, and lists the prose it did not
change. References in other projects are not rewritten: pass the printed lines
on, and `tcw validate` in each such project reports the old names. The title is
separate: `tcw work edit <slug> --title "<title>"`.

## Documentation entries

`tcw work docs` prints the documents this project keeps in step with its code,
each with the kind of change that should update it. The plan and implement
stage prompts include them, so a plan names a task for every entry it expects
to fire, and implement checks each once the change is finished.
