# Add the stage-entry verb

Child **C4** of the initiative
[`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`][epic].

## Product changes

`tcw work stage <id> [ref]` is how an agent finds out what to do at a lifecycle
stage. It checks the stage is legal for the item's status, runs the stage's
`pre` checks, resolves its prompt bindings, and prints the resulting instructions
on stdout.

That is the whole point of the initiative made reachable: C3 made a node's own
instructions expressible, and this is the command that hands them over. A node
that has configured nothing gets TCW's built-in default (C6's content); a node
that has configured its own gets its own.

**It writes nothing.** Not an artifact, not a draft, not a status change, not a
field. Running it purely to read the instructions is safe, and that is what makes
it usable — an agent reaching a stage should not have to weigh whether asking
what to do will change anything.

`--no-exec` prints what *would* run — every check, every `generate` script — and
runs none of it. It is how you read an unfamiliar repository's lifecycle before
triggering it.

## Technical changes

Thin: C3 already ships the resolution library, the condition filter, and plan
mode. C4 is legality, ordering, stream discipline, and the CLI surface.

- **Stage/status legality.** `implement` from `backlog` and `spec` after
  completion are nonsense; `postmortem` is legal in `review` and after
  completion, because it is out-of-band. Checked before any hook runs.
- **Stream discipline.** stdout carries resolved prompt text and nothing else —
  every check's stdout and stderr goes to stderr — so `tcw work stage spec` can
  be piped.
- **`inbox` is rejected**, with that reason: it runs before an item exists, so
  there is no item to resolve a stage against.

## Meta changes

**Blocked by C3**, which shipped the resolution library this calls, including the
`execute=False` plan mode `--no-exec` needs.

**Parallel with C5 and C6** — none of the three blocks another. The initiative
assigns the stage/status legality table to C5 with C4 consuming it; whichever
lands first owns it, and the other consumes.

[epic]: ../../active/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/initial-request.md
