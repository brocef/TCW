# The command line: output and exit codes

Every `tcw` command follows the same rules about what it prints, where it
prints it, which projects it reads, and the number it exits with. This guide
describes those rules, so that a script, a hook or an agent can rely on them
without reading each command's code. Each command's own options are in its
`--help`; what the commands do is in the guides for [work](work.md),
[taxonomy and capabilities](taxonomy-and-capabilities.md) and
[validation](linking-and-validation.md).

## How commands are named

A command is written `tcw <noun> [<child noun>] <verb>`: `tcw work new`,
`tcw work tags add`, `tcw work stage prompt`, `tcw project config`. Three
commands are verbs on their own: `tcw validate`, `tcw serve` and
`tcw migrate`. Everything about the project itself, as opposed to its
taxonomy, capabilities and work, is under `tcw project`: `tcw project new`
makes a project, `tcw project info` and `tcw project path` describe it,
`tcw project list` lists it and its related projects, `tcw project config`
prints its configuration, and `tcw project provision` fetches the related
projects it needs onto this machine.

`--help` works at every level. On a group, such as `tcw work --help`, it lists
the commands inside it. On a single command it says what the command is for,
then two lines, `Prints:` (what it puts on standard output) and `Writes:`
(what it changes on disk or in Jira), then a few example command lines.
`tcw --help` ends with the exit-code table below.

## A mistyped or removed command gets a suggestion

A command name `tcw` does not know is a usage error (exit code 2), and the
last line of the error suggests what was probably meant. Mistyping list after
`tcw work` is answered with ``did you mean `tcw work list`?``. Typing new
straight after tcw, with no noun, is answered with
``did you mean `tcw work new` or `tcw project new`?``, because both exist.
Typing list straight after tcw suggests
``did you mean one of `tcw taxonomy list`, `tcw capabilities list`, `tcw work list`?``,
and no project command, since listing projects is a question about the
project rather than one of its three axes.

Four commands of TCW 3.x are gone in 4.0, and each is answered with the
command that replaces it. The
[3.x-to-4.0 migration guide](../migration-guide-3.X-to-4.0.0.md) lists the
exact line each one prints.

| The verb of a 3.x command 4.0 removed | Its replacement in 4.0  |
| ------------------------------------- | ----------------------- |
| `init`                                | `tcw project new`       |
| `projects`                            | `tcw project list`      |
| `config`                              | `tcw project config`    |
| `provision`                           | `tcw project provision` |

## Running a command in another project's folder: `-C`

The option `-C`, given straight after `tcw` and before the command, runs any
command as if `tcw` had been started in another folder, such as
`tcw -C <folder> work list`.
The command then runs as the project in that folder, with that project's own
configuration, personal settings, stages, checks and hooks, and a relative
path given to the command, or printed by it, is relative to that folder.

The folder can be given in two ways:

- as a path, relative to the current folder or absolute, such as
  `tcw -C ../core work list`; a path that is not an existing folder is a usage
  error (exit code 2), `cannot run in ../nope: no such folder`;
- as a folder address, `tcw -C tcw://core.path/ work list`, which names a
  project by its ID and lets TCW find that project's folder the way it finds
  any related project (the [related projects guide](multi-repo.md) says how).
  The command then runs as that project.

`-C` can be repeated, and each one is read from the folder the one before it
chose, so `tcw -C tcw://core.path/ -C tcw://other.path/ project info` runs in
`other`'s folder as found from `core`'s.

`-C` reaches only folders on this machine. A project that is not here cannot
be run in: `tcw -C tcw://core.path/ work list`, when `core` is not on this
machine, exits 5 with a line saying so and where TCW looked. Finding folders
is about where projects sit on this machine; the parent links, full
identifiers, ownership, inheritance and `--scope` described below are what
every project keeps, whatever store holds it.

A command changes only objects that belong to the project it runs as. When
one is asked to change another project's object, it refuses (exit code 3) and,
when that project is on this machine, names the folder to give `tcw -C` to
run it there instead.

## Standard output carries only the result

A program has two output streams: **standard output** (stdout), which a script
reads or a pipe passes on, and **standard error** (stderr), which a terminal
shows to a person. `tcw` puts only the command's result on stdout, so that
`$(tcw …)` in a script captures exactly that and nothing else.

The result is one name per line, where a command has names to give: a work
item's, taxonomy entry's or capability's full identifier (see
[Naming an object](#naming-an-object)), a Jira ticket key, or a project ID.
More detail is available only through `--json`, on the commands that offer
it.

| Command                                                                                        | Standard output                                                                       |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `tcw work new`                                                                                 | the new item's full identifier; a ticket key when TCW stopped after creating a ticket |
| `tcw work list`                                                                                | one full identifier per line                                                          |
| `tcw work show`                                                                                | the item's properties, its request and its comments, newest first                     |
| `tcw work path`                                                                                | one path                                                                              |
| `tcw work advance`, `tcw work discard`                                                         | the stage the item is at after the move; with `--dry-run`, the stage it would move to |
| `tcw work rename`, `tcw work move`                                                             | one `<old full id> -> <new full id>` line per identifier it changed, the item first   |
| `tcw work stage prompt`, `tcw work procedure`                                                  | the composed instructions                                                             |
| `tcw work lifecycle`                                                                           | every stage, its kind, whether it is turned on, and its bindings                      |
| `tcw work docs`                                                                                | the project's documentation entries                                                   |
| `tcw work tags list`                                                                           | one tag per line                                                                      |
| `tcw work tickets list`                                                                        | one Jira ticket key per line                                                          |
| `tcw work tickets adopt`                                                                       | the new item's full identifier                                                        |
| `tcw taxonomy list`, `tcw capabilities list`, and their `search`                               | one full identifier per line                                                          |
| `tcw taxonomy add`, `tcw capabilities add`                                                     | the new record's full identifier                                                      |
| `tcw taxonomy show`, `tcw capabilities show`                                                   | the record                                                                            |
| `tcw taxonomy rename`, `tcw taxonomy move`, `tcw capabilities rename`, `tcw capabilities move` | one `<old full id> -> <new full id>` line per identifier it changed, the record first |
| `tcw taxonomy path`, `tcw capabilities path`                                                   | the store's folder                                                                    |
| `tcw capabilities drift`                                                                       | one finding per line, `<kind>: <path>: <message>`; nothing when there is none         |
| `tcw validate`                                                                                 | one finding per line, `<severity>: <where>: <message>`; nothing when there is none    |
| `tcw project list`                                                                             | one project ID per line, this project first                                           |
| `tcw project info`                                                                             | one fact about the project per line                                                   |
| `tcw project path`                                                                             | the project's root folder, the one holding its `.tcw/` folder                         |
| `tcw project config`                                                                           | the configuration in effect, as YAML                                                  |
| `tcw serve`                                                                                    | the address the web viewer is served at                                               |

Every other command, such as `tcw work edit`, `tcw work comment`,
`tcw capabilities set`, `tcw project new`, `tcw project provision` and
`tcw migrate`, prints nothing on stdout.

Three of these deserve a note. `tcw work tickets list` prints only keys; each
ticket's key, summary, status, creation time, reporter, web address and
description are in `--json`.
`tcw validate --remote` prints findings only, never a list of what passed, and
a check it could not make, such as a move between two stages it had no ticket
to try, is itself a finding.
A listing stays one full identifier per line whatever `--scope` covers; which
project each object belongs to is in the identifier itself.

## Which projects a command covers: `--scope` and `--project`

A project can have parents, the projects it inherits taxonomy, capabilities
and settings from, and children, the projects that name it as a parent (the
[related projects guide](multi-repo.md) describes them). Eight commands can
cover more than the project they run in: `tcw work list`, `tcw work show`,
`tcw taxonomy list`, `tcw taxonomy search`, `tcw taxonomy show`,
`tcw capabilities list`, `tcw capabilities search` and
`tcw capabilities show`. Each takes two options.

**`--scope`** says which projects to cover, and is one of four values:

- `own`, the default: this project's own objects only;
- `up`: this project and its ancestors, its parents and their parents;
- `down`: this project and its descendants, its children and their children;
- `all`: both.

A scope never covers a sibling, a project that shares a parent with this one
but is neither its ancestor nor its descendant. So `tcw work list --scope down`
run in `core` lists the items of `core` and of every project below it.

Under `own`, an object this project inherits from a parent and does not
replace is not listed; `tcw capabilities show billing/charge` in `app`, whose
parent `core` has that capability, answers
`no such capability: 'billing/charge'; 'app' inherits core.capabilities/billing/charge there: add --scope up, or name it by that full identifier`
(exit code 4). Where several covered projects have an object at the same path,
a listing shows it once, as the project the command runs in sees it, or, when
that project has nothing there, as the covered project that the others'
objects replace; its record says what each project makes of it (the
`statuses` and `overridden-by` keys below). `tcw capabilities show billing/refund --scope down`, run in `core`
whose child `app` sets its own status, prints:

```text
full-id: core.capabilities/billing/refund
owner: core
overridden by: app.capabilities/billing/refund
name: Refund a payment
Status: Missing
status by project:
  Missing: core, other (inherited)
  Supported: app
```

**`--project <id>`** keeps only one covered project's own objects, such as
`tcw capabilities list --scope down --project app`. Its results are never
grouped: each record is that project's own object as that project sees it, and
carries no `statuses` and no `overridden-by`. The ID must be one the scope
covers; any other is a usage error (exit code 2) that names what the scope
does cover and then ends in one of three ways, quoted from `tcw/scope.py` and
`tcw/store/project.py`:

- `; --scope <wider scope> covers it`, when a wider scope would;
- `; no project with ID '<id>' is known or found near this one; check the spelling`,
  when no project has that ID;
- `; it is neither an ancestor nor a descendant of '<this project>'`, when it
  is a project TCW knows but no scope reaches, such as a sibling.

For example, `tcw work list --project core`, run in `app`, whose parent is
`core`, exits 2 with this line after the command's name:
`--project core: 'core' is not covered by --scope own in 'app', which covers app; --scope up covers it`.

A covered project that cannot be read, because it is not on this machine or
its files cannot be read, has one of two outcomes, depending on whether the
command needs that project's content.

- **When it does not, the project is left out.** One warning line on stderr
  says what that leaves out and why, and the command exits 0. A work listing
  is one such command, whichever scope covers the missing project, and so is
  any `--scope down` view whose missing project is a child (the reason is
  shortened here):

    ```text
    warning: 'core' is unavailable, so its work items are not listed: project 'core' is not on this machine: …
    ```

- **When the active project's own entries need it, the command stops with
  exit 7** and prints nothing on stdout. A project's own entries, under
  `--scope up`, include what it inherits, so `tcw taxonomy list`,
  `tcw taxonomy show`, `tcw capabilities list` and `tcw capabilities show`,
  each with `--scope up`, exit 7 when a parent that passes down that axis is
  missing, with a line naming the parent, such as
  `tcw capabilities list: 'app' inherits its capabilities from project 'core', which is not on this machine: …`.

The words after "so" say what was left out. A listing or search says "its
taxonomy entries are not listed" or "its capabilities are not listed";
`tcw taxonomy show` says "its taxonomy entries are not included",
`tcw capabilities show` "its status is not shown", and `tcw work show` "its
items are not counted in children and blocks"; `tcw work list --project <id>`
says the same of a covered project it does not keep, which it reads only for
those counts.

The project the command runs in is different. When something it inherits
cannot be read, such as a parent's capabilities, a listing under the default
`--scope own` shows only its own declarations with a warning (and marks them
`partial`, below); under `--scope up` it stops with exit code 7, as does a
command that needs an inherited setting.

## Output records: `--json`

**`--json`** prints exactly one JSON object whose first key is `"schema": 2`,
the version of its shape, which is the same for every JSON document TCW
prints. `tcw work list --json`
holds the items under `items`, `tcw work show --json` holds `item`, `request`
and `comments`, `tcw capabilities list --json` holds `capabilities`, and
`tcw taxonomy list --json` holds `terms`; each command's `--help` names its
keys.

Every record of a work item, taxonomy entry or capability starts with two
keys:

- `full-id`, the object's full identifier;
- `owner`, the ID of the project it belongs to.

A taxonomy or capability record then carries `parent` (the full identifier of
the record it sits under, or `null`) and `overrides` (the full identifier of
the inherited object it replaces, or `null`). Four keys appear only where they
apply:

- **`projects`**, at the top level, when `--scope` is not `own`: every covered
  project in order, with its `relation` to this one (`current`, `ancestor`,
  `descendant`), and `unavailable` with the reason for each that could not be
  read;
- **`statuses`**, on a capability that more than one covered project sees: one
  entry per project, with the status it gives, whether it `inherited` that
  status, and the `full-id` of the object the status comes from;
- **`overridden-by`**, on an object that covered projects below replace with
  their own: the full identifiers of those objects;
- **`partial`**, set to `true` in place of `overrides`, on a record of this
  project read from its own declaration alone because what it inherits could
  not be read, so whether it overrides anything is not known.

`tcw capabilities list --scope down --json`, run in `core`, whose children are
`app` (which sets its own status) and `other` (which does not):

```json
{
    "schema": 2,
    "capabilities": [
        {
            "full-id": "core.capabilities/billing/refund",
            "owner": "core",
            "parent": null,
            "overrides": null,
            "name": "Refund a payment",
            "status": "Missing",
            "statuses": [
                {
                    "project": "core",
                    "status": "Missing",
                    "inherited": false,
                    "full-id": "core.capabilities/billing/refund"
                },
                {
                    "project": "app",
                    "status": "Supported",
                    "inherited": false,
                    "full-id": "app.capabilities/billing/refund"
                },
                {
                    "project": "other",
                    "status": "Missing",
                    "inherited": true,
                    "full-id": "core.capabilities/billing/refund"
                }
            ],
            "overridden-by": ["app.capabilities/billing/refund"]
        }
    ],
    "projects": [
        { "id": "core", "relation": "current" },
        { "id": "app", "relation": "descendant" },
        { "id": "other", "relation": "descendant" }
    ]
}
```

The same command with `--project app` lists `app`'s own record alone, with
no `statuses` and no `overridden-by`:

```json
{
    "full-id": "app.capabilities/billing/refund",
    "owner": "app",
    "parent": null,
    "overrides": "core.capabilities/billing/refund",
    "name": "Refund a payment",
    "status": "Supported"
}
```

And `tcw capabilities list --json` in `app` when `core` is not on this machine
gives `app`'s record from its own declaration alone:

```json
{
    "full-id": "app.capabilities/billing/refund",
    "owner": "app",
    "parent": null,
    "partial": true,
    "name": "Refund",
    "status": "Supported"
}
```

A work item's record also carries `parent`, `blocked-by`, `blocks` and
`children` as full identifiers, and `path`, the item's folder on this machine.

## Standard error carries everything said to a person

Narration goes to stderr: progress, warnings (lines starting `warning:`),
notes (lines starting `note:`), and errors. Every file a command writes or
removes is named there, one line each, as `wrote <path>`, `removed <path>` or
`created <folder>/`, with the path relative to the current folder when it is
inside it. A script that wants to know which files changed reads stderr; a
script that wants the result reads stdout.

A failure is reported as one line that starts with the command's name, such
as `tcw work show: no work item app.work/2026-10-24-nope`, followed by the
exit code below. A usage error found while reading the command line, such as
a missing argument, prints the command's usage summary first, then the line
`<command>: error: <message>`, and exits with code 2. When a command fails
after it had already created something, such as a Jira ticket made before a
later step failed, the name of what it created is still printed on stdout,
exactly as success would print it, so the caller knows it exists.

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
tcw work comment app.work/2026-10-15-refund-a-payment < note.md
```

A command waits only a short time for piped text to start arriving (two
seconds, or the number of seconds in the environment variable
`TCW_STDIN_TIMEOUT`) and then carries on without it, saying so on stderr. Text
that starts and then stops before it ends is refused, rather than stored half
written.

## Where a child's folder goes: `--parent` and `--flat`

`--parent` on `tcw work new`, `tcw taxonomy add` and `tcw capabilities add`
records the new object's parent and, when the parent is one of this project's
own objects, puts the new folder inside the parent's folder. A new work item's
id-path (its folder's path in the work store) then becomes
`<epic folder>/<new folder>`:

```text
$ tcw work new 'A part' --parent 2026-10-24-app-epic < request.md
app.work/2026-10-24-app-epic/2026-10-24-a-part
```

A capability's path is read inside the parent's folder, unless it already
starts with the parent's path and a `/`, in which case it is used as given.
With parent `billing/invoices`, `bulk` makes `billing/invoices/bulk`,
`extra/bulk` makes `billing/invoices/extra/bulk` (with `extra/` an organising
folder), and `billing/invoices/bulk` makes `billing/invoices/bulk`.

`--flat` keeps the folder where it would be without a parent: the top of the
work or taxonomy store, or, for a capability, the path read as without
`--parent`, namespace folder first. The `parent` field is recorded all the
same; it, not the folder, is what makes the object a child. `--flat` without
`--parent` is a usage error (exit code 2).

When the parent is not this project's own, because it is inherited or belongs
to another project, its folder cannot hold the new one: the command behaves as
with `--flat` and a `not nested:` line on stderr says so. A capability's path
is then read as given, so it must name its namespace folder. The
[work guide](work.md) describes nested items.

## Naming an object

Every object TCW keeps, a work item, a taxonomy entry or a capability, has a
**full identifier**: the ID of the project that owns it, the store it is in,
and its id-path, the path of its folder within that store, written
`<project>.<store>/<id-path>`, such as `app.work/2026-10-24-app-epic`,
`core.capabilities/billing/refund` or `core.taxonomy/invoice`. Some messages
and argument names call a work item's full identifier its **slug**; that word
is only a nickname for the full identifier. The
[linking and validation guide](linking-and-validation.md) describes full
identifiers and the links built from them.

Wherever a command takes an object, it accepts:

- the **full identifier**, such as `core.work/2026-10-24-shared-epic`, which
  can name an object of any project TCW can find;
- its **address**, the full identifier written after `tcw://`, such as
  `tcw://app.work/2026-10-24-app-epic`;
- for a work item, a **tracker key** such as `TCW-120`, meaning the item of
  this project that carries that key, or written after a project's work store,
  `<project>.work/TCW-120`, meaning that project's item with that key;
- a bare **id-path**, such as `2026-10-24-app-epic` or
  `2026-10-24-app-epic/2026-10-24-a-part`, meaning the object at that path in
  the project the command runs in. An object it inherits and does not
  replace is named by its full identifier, or found by its id-path with
  `--scope up`.

Output always prints the full identifier, whichever form was given.

The name must match exactly. A shortened name, such as `app-epic` without its
date, or a nested item's last folder alone, is not completed for you: it is
reported as not found, exit code 4. A tracker key no item carries is not found
too, with `no work item in project 'app' carries the key TCW-120`. A text that
is none of these forms, or a full identifier of the wrong store (a taxonomy
entry given to `tcw work show`), is a usage error, exit code 2.

A full identifier can name an object of a related project. A command may read
it, when that project is on this machine; a command that would change it is
refused (exit code 3) and names the `tcw -C` that runs it in that project.

## Exit codes

Every command exits with one of these codes. The numbers live in
`tcw/exit.py`. Inside TCW, each kind of failure is an exception class in
`tcw/errors.py` that carries its code; a script needs only the numbers.

| Code | Meaning                                                                      | Examples                                                                                                                                                                                                                                                                                                                                               |
| ---- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0    | Success.                                                                     | The command did what it was asked; `tcw validate` found no errors (it may still have printed warnings); a covered project that could not be read was left out with a warning.                                                                                                                                                                          |
| 1    | An error: TCW, the backend, or something it was told to read failed, such as a configuration problem or an unknown project ID. | `.tcw/tcw-config.yaml` has a problem every command refuses on; the folder holds a 3.x project, which every command refuses and asks to be moved over with `tcw migrate`; a full identifier names a project ID nothing here knows; a file could not be written; `tcw validate` found an error; no identity is configured for `--mine` or `--assign-me`. |
| 2    | A usage error: the command was asked for something that cannot be asked.     | An unknown command, stage or option; `--force` without `--reason`; a malformed name; a `--project` the scope does not cover; a `-C` folder that does not exist. Nothing was read or changed.                                                                                                                                                           |
| 3    | Refused: a legal request that a rule or a check turned down. Nothing changed. | A failing `pre` hook (a command a stage runs before an item moves into it) or a failing built-in check of a move (a gate, in [the work guide](work.md#built-in-gates)); a move that skips a stage without `--force`; a name already taken; removing a record another one depends on; changing an object that belongs to another project, whether or not that project is on this machine.                                                                                                |
| 4    | Not found.                                                                   | No such item, taxonomy entry, capability, tag or ticket; a tracker key no item carries.                                                                                                                                                                                                                                                                |
| 5    | Unreachable.                                                                 | Jira could not be reached; a command had to read a project that is not on this machine, named by a full identifier or a `tcw -C` address (the message says where TCW looked, and how to fetch it when a manifest entry gives its repository).                                                                                                          |
| 6    | The item moved, but something after the move failed.                         | A `post` hook failed; the trace comment that records why the item moved could not be written. The move stands.                                                                                                                                                                                                                                         |
| 7    | Something this project inherits is not available here.                       | A parent it inherits from is not on this machine, or that parent's own parent links could not be read, and the command needs what it passes down, such as `tcw project config` reading an inherited setting.                                                                                                                                           |

A request about another project's work item shows how the codes fit
together. Run in `app`, `tcw work show core.work/2026-10-24-shared-epic` prints
the item and exits 0 when `core` is on this machine, exits 5 when it is not,
and exits 1 when no project with the ID `core` is known at all.
`tcw work edit core.work/2026-10-24-shared-epic --priority high` is refused
with exit code 3 in every case, because a command changes only the project it
runs as; where `core` is on this machine, the message names the folder to
give `tcw -C` to make the change there, and a new item for `core` is
made the same way, with `tcw -C <folder> work new`. A TCW 3.x project could
file an item into another project from its own folder; the
[migration guide](../migration-guide-3.X-to-4.0.0.md) says what replaces that
in 4.0.

## Using the rules from a script

Capture a new item's full identifier and keep working on it:

```sh
ITEM=$(tcw work new "Refund a payment" --priority high < request.md) || exit 1
tcw work edit "$ITEM" --tag billing
tcw work path "$ITEM" spec
```

Act on how a move went:

```sh
tcw work advance "$ITEM"
case $? in
    0) echo "moved" ;;
    3) echo "refused; the reason is on stderr above" ;;
    6) echo "moved, but a post hook failed; see stderr" ;;
    *) echo "failed" ; exit 1 ;;
esac
```
