As a user or a script, I can rely on every `tcw` command, on all three axes,
behaving the same way at its edges, so I learn the rules once.

**Standard output carries only what the command produces.** A list prints one
identifier per line — a full item slug, a qualified term or capability path, a
project ID — and nothing else, so I can pipe it into another command. A command
that offers `--json` prints exactly one JSON object with `"schema": 1` at the
top, with any list under a named key (`"items"`, `"terms"`, `"capabilities"`,
`"projects"`). A command that produces nothing, such as `tcw work edit` or
`tcw taxonomy rm`, prints nothing on standard output.

**Standard error carries everything said to a person**: what happened, warnings
(lines starting `warning: `), what to do next, and every file the command wrote
or removed, one line each, as `wrote <path>` or `removed <path>` (`created
<path>/` for a folder made empty). An error is one line starting with the
command's own words, for example `tcw work advance: …`. No command ever stops to
ask me a question; long text — a work item's request, a comment, a term's
description, a capability's body — is read from standard input.

**One set of exit codes**, the same for every command, and listed at the end of
`tcw --help`:

| Code | Meaning |
| --- | --- |
| 0 | it worked (including `tcw validate` with only warnings) |
| 1 | an error: TCW, its configuration or the work backend failed |
| 2 | a usage error: a malformed command, option or value |
| 3 | refused: a gate, a name already taken, or a record something else still depends on |
| 4 | not found: no such item, term, capability, tag or ticket |
| 5 | unreachable: Jira, or a declared project that is not on this machine |
| 6 | the work item moved, but something after the move failed |

A command that fails after it has already created or renamed something still
prints that thing's name on standard output, as success would, so I never lose
track of what now exists.

**I name a work item the same way everywhere**: by its full slug
(`<project-id>/<folder>`), by its folder name alone, or, when the project keeps
its items in Jira, by its ticket key. The match is exact — no prefixes and no old
names — and every slug TCW prints is the full form.

**Every command explains itself.** `tcw <command> --help` ends its description
with a `Prints:` line (what goes to standard output) and a `Writes:` line (what
files it changes, or `nothing`), and closes with examples I can copy. Every
option has one long spelling; a repeatable option takes one value each time it
is given.
