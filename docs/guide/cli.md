# The command line: output and exit codes

Every `tcw` command follows the same rules about what it prints, where it
prints it, and the number it exits with. This guide describes those rules, so
that a script, a hook or an agent can rely on them without reading each
command's code. Each command's own options are in its `--help`; what the
commands do is in the guides for [work](work.md),
[taxonomy and capabilities](taxonomy-and-capabilities.md) and
[validation](linking-and-validation.md).

## How commands are named

A command is written `tcw <noun> [<child noun>] <verb>`: `tcw work new`,
`tcw work tags add`, `tcw work stage prompt`, `tcw config show`. Four
commands act on the whole project and are verbs on their own: `tcw init`,
`tcw provision`, `tcw validate` and `tcw serve`.

`--help` works at every level. On a group, such as `tcw work --help`, it lists
the commands inside it. On a single command it says what the command is for,
then two lines, `Prints:` (what it puts on standard output) and `Writes:`
(what it changes on disk or in Jira), then a few example command lines.
`tcw --help` ends with the exit-code table below. A mistyped command name is
answered with a suggestion, such as ``did you mean `tcw work list`?``.

## Standard output carries only the result

A program has two output streams: **standard output** (stdout), which a script
reads or a pipe passes on, and **standard error** (stderr), which a terminal
shows to a person. `tcw` puts only the command's result on stdout, so that
`$(tcw …)` in a script captures exactly that and nothing else.

The result is one name per line, where a command has names to give: a work
item's full slug (`project/folder`), a Jira ticket key, a qualified path of a
taxonomy entry or capability, or a project ID. More detail is available only
through `--json`, on the commands that offer it.

| Command                                                          | Standard output                                                                       |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `tcw work new`                                                   | the new item's full slug; a ticket key when TCW stopped after creating a ticket       |
| `tcw work list`                                                  | one full slug per line                                                                |
| `tcw work show`                                                  | the item's properties, its request and its comments, newest first                     |
| `tcw work path`                                                  | one path                                                                              |
| `tcw work advance`, `tcw work discard`                           | the stage the item is at after the move; with `--dry-run`, the stage it would move to |
| `tcw work rename`                                                | one `<old> -> <new>` line per identifier it changed                                   |
| `tcw work stage prompt`, `tcw work procedure`                    | the composed instructions                                                             |
| `tcw work lifecycle`                                             | every stage, its kind, whether it is turned on, and its bindings                      |
| `tcw work docs`                                                  | the project's documentation entries                                                   |
| `tcw work tags list`                                             | one tag per line                                                                      |
| `tcw work tickets list`                                          | one Jira ticket key per line                                                          |
| `tcw work tickets adopt`                                         | the new item's full slug                                                              |
| `tcw taxonomy list`, `tcw capabilities list`, and their `search` | one qualified path per line                                                           |
| `tcw taxonomy add`, `tcw capabilities add`                       | the new record's qualified path                                                       |
| `tcw taxonomy show`, `tcw capabilities show`                     | the record                                                                            |
| `tcw taxonomy path`, `tcw capabilities path`                     | the store's folder                                                                    |
| `tcw capabilities drift`                                         | one finding per line, `<kind>: <path>: <message>`; nothing when there is none         |
| `tcw validate`                                                   | one finding per line, `<severity>: <where>: <message>`; nothing when there is none    |
| `tcw projects list`                                              | one project ID per line, this project first                                           |
| `tcw config show`                                                | the configuration in effect, as YAML                                                  |
| `tcw serve`                                                      | the address the web viewer is served at                                               |

Every other command, such as `tcw work edit`, `tcw work comment`,
`tcw init` and `tcw provision`, prints nothing on stdout.

Two of these deserve a note. `tcw work tickets list` prints only keys; each
ticket's key, summary, status, creation time, reporter, web address and
description are in `--json`.
`tcw validate --remote` prints findings only, never a list of what passed, and
a check it could not make, such as a move between two stages it had no ticket
to try, is itself a finding.

**`--json`** prints exactly one JSON object whose first key is `"schema": 1`,
the version of its shape. `tcw work list --json` holds the items under
`items`, `tcw work show --json` holds `item`, `request` and `comments`, and
each command's `--help` names its keys.

## Standard error carries everything said to a person

Narration goes to stderr: progress, warnings (lines starting `warning:`),
notes (lines starting `note:`), and errors. Every file a command writes or
removes is named there, one line each, as `wrote <path>`, `removed <path>` or
`created <folder>/`, with the path relative to the current folder when it is
inside it. A script that wants to know which files changed reads stderr; a
script that wants the result reads stdout.

A failure is reported as one line that starts with the command's name, such
as `tcw work show: no work item demo/support-sso`, followed by the exit code
below. A usage error found while reading the command line, such as a missing
argument, prints the command's usage summary first, then the line
`<command>: error: <message>`, and exits with code 2. When a command fails after it had already created something, such as
a Jira ticket made before a later step failed, the name of what it created is
still printed on stdout, exactly as success would print it, so the caller
knows it exists.

## Commands never ask questions

No `tcw` command stops to ask for confirmation or for a value. Everything it
needs is given as an argument or an option, or read from a file. This is what
lets an agent or a hook run any command unattended.

## Long text is read from standard input

Text too long for a command line is piped in on stdin:

- `tcw work new` reads the item's request, what it asks for;
- `tcw work comment` reads the comment;
- `tcw taxonomy add` reads the entry's description;
- `tcw capabilities add` reads the capability's body.

```sh
tcw work new "Refund a payment" < request.md
tcw work comment demo/2026-10-15-refund-a-payment < note.md
```

A command waits only a short time for piped text to start arriving (two
seconds, or the number of seconds in the environment variable
`TCW_STDIN_TIMEOUT`) and then carries on without it, saying so on stderr. Text
that starts and then stops before it ends is refused, rather than stored half
written.

## Naming a work item

Wherever a command takes a work item, it accepts:

- the **full slug**, `project/folder`, such as `demo/2026-10-15-refund-a-payment`;
- the **folder name alone**, for an item in the project the command is run in;
- in a Jira-mode project, the **ticket key**, such as `TCW-42`.

The name must match exactly. A shortened name, such as `refund-a-payment`
without its date, is not completed for you: it is reported as not found, exit
code 4. A full slug can name an item in another connected project, which a
command may read; a command that would change it is refused (exit code 3) and
asks you to run it in that project.

## Exit codes

Every command exits with one of these codes. The numbers live in
`tcw/exit.py`. Inside TCW, each kind of failure is an exception class in
`tcw/errors.py` that carries its code; a script needs only the numbers.

| Code | Meaning                                                                      | Examples                                                                                                                                                                                                                                                                               |
| ---- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | Success.                                                                     | The command did what it was asked; `tcw validate` found no errors (it may still have printed warnings).                                                                                                                                                                                |
| 1    | An error: the backend or TCW itself failed.                                  | `tcw-config.yaml` has a problem every command refuses on; a file could not be written; `tcw validate` found an error; no identity is configured for `--mine` or `--assign-me`.                                                                                                         |
| 2    | A usage error: the command was asked for something that cannot be asked.     | An unknown stage or option; `--force` without `--reason`; a malformed slug. Nothing was read or changed.                                                                                                                                                                               |
| 3    | Refused: a legal request that a rule or a gate turned down. Nothing changed. | A failing `pre` hook or built-in gate; a move that skips a stage without `--force`; a name already taken; creating an item in a project that is read-only from here, in a project nothing here declares, or in a project that is not on this machine; changing another project's item. |
| 4    | Not found.                                                                   | No such item, taxonomy entry, capability, tag or ticket; a slug naming a project nothing here declares.                                                                                                                                                                                |
| 5    | Unreachable.                                                                 | Jira could not be reached; a command had to read a connected project that is not on this machine (the manifest entry that places it says where it should be).                                                                                                                          |
| 6    | The item moved, but something after the move failed.                         | A `post` hook failed; the trace comment that records why the item moved could not be written. The move stands.                                                                                                                                                                         |
| 7    | Something this project inherits is not available here.                       | A project it inherits from is not on this machine, or that project's parent links could not be read, and the command needs what it passes down.                                                                                                                                        |

Creating an item in another project (in 3.x, through the `--project` option
of `tcw work new`, removed in 4.0, where an item for another project is made
there with `tcw -C <folder> work new`) shows how the codes fit together. TCW creates the item only in a project that is on this
machine and that this project may write into (a Jira-mode project gets a ticket
in its Jira inbox), prints its name and exits 0. Every case where the target
cannot be written to (it is read-only from here, nothing here declares it, or it
is not on this machine) is refused with exit code 3, as the table says.

## Using the rules from a script

Capture a new item's slug and keep working on it:

```sh
SLUG=$(tcw work new "Refund a payment" --priority high < request.md) || exit 1
tcw work edit "$SLUG" --tag billing
tcw work path "$SLUG" spec
```

Act on how a move went:

```sh
tcw work advance "$SLUG"
case $? in
    0) echo "moved" ;;
    3) echo "refused; the reason is on stderr above" ;;
    6) echo "moved, but a post hook failed; see stderr" ;;
    *) echo "failed" ; exit 1 ;;
esac
```
