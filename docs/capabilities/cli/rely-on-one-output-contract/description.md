As a user or a script, I can rely on every `tcw` command, on all three axes,
behaving the same way at its edges, so I learn the rules once.

**Standard output carries only what the command produces.** A list prints one
identifier per line — the full identifier of a work item, term or capability,
`<project>.<namespace>/<id-path>`, or a project ID — and nothing else, so I can
pipe it into another command. A command that offers `--json` prints exactly one
JSON object with `"schema": 2` at the top, with any list under a named key
(`"items"`, `"terms"`, `"capabilities"`, `"projects"`). Every JSON record of a
work item, term or capability carries `full-id`, its full identifier, and
`owner`, the ID of the project that holds it. A command that produces nothing,
such as `tcw work edit` or `tcw taxonomy rm`, prints nothing on standard output.

**Standard error carries everything said to a person**: what happened, warnings
(lines starting `warning: `), what to do next, and every file the command wrote
or removed, one line each, as `wrote <path>` or `removed <path>` (`created
<path>/` for a folder made empty, `moved <old> to <new>` for a work item folder
renamed). An error is one line starting with the command's own words, for
example `tcw work advance: …`; when the command line itself is malformed — an
unknown option, a missing argument — the argument parser first prints a
`usage:` block, then that error line. No command ever stops to
ask me a question; long text — a work item's request, a comment, a term's
description, a capability's body — is read from standard input.

**One set of exit codes**, the same for every command, and listed at the end of
`tcw --help`:

| Code | Meaning                                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | it worked (including `tcw validate` with only warnings)                                                                                                    |
| 1    | an error: TCW, its configuration or the work backend failed                                                                                                |
| 2    | a usage error: a malformed command, option or value                                                                                                        |
| 3    | refused: a gate, a name already taken, or a record something else still depends on                                                                         |
| 4    | not found: no such item, term, capability, tag or ticket                                                                                                   |
| 5    | unreachable: Jira, or a declared project that is not on this machine                                                                                       |
| 6    | the work item moved, but something after the move failed                                                                                                   |
| 7    | something this project inherits is not available here: a project it inherits from is not on this machine, or that project's parent links could not be read |

A command that fails after it has already created or renamed something still
prints that thing's name on standard output, as success would, so I never lose
track of what now exists.

**I name an object the same way everywhere**: by its full identifier, by its
`tcw://` address (`tcw://<project>.<namespace>/<id-path>`), or, for an object of
the project I am in, by its id-path alone — a work item's folder name, a term's
or capability's path. A work item can also be named by its ticket key when its
project keeps its items in Jira, bare or as `<project>.work/<KEY>`. The match is
exact — no prefixes, no old names and no other letter case — and every
identifier TCW prints is the full one. The TCW 3.x forms, `<project-id>/<folder>`
and an alias prefix such as `core/term`, are read as id-paths and so are not
found (exit 4); when the first part is a project TCW can locate, the message
says how to write the full identifier.

**Every command explains itself.** `tcw <command> --help` ends its description
with a `Prints:` line (what goes to standard output) and a `Writes:` line (what
files it changes, or `nothing`), and closes with examples I can copy. Every
option has one long spelling; a repeatable option takes one value each time it
is given.

Taxonomy and capability records carry `parent`, after `owner`: the full identifier of the object they belong under, or null.

**A document that covers more than one project says which.** A list or show run with `--scope up`, `down` or `all` carries `projects`: each project the scope covers, in scope order, as `{"id": …, "relation": …}`, and with `"unavailable"`, the reason, for one that is not on this machine or could not be read. Under the default scope, `own`, it carries none.
