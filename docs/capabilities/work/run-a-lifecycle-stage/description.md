As a user or agent, I run `tcw work stage <id> <ref>` to find out what to do at a
lifecycle stage. TCW checks the stage makes sense for where the item is, runs
whatever `pre` checks the project configured, resolves the stage's prompt
bindings, and prints the instructions.

**With nothing configured for a stage, the instructions are TCW's own.** TCW
ships defaults for the six lifecycle stages that run against an existing item —
`request`, `spec`, `plan`, `implement`, `verify`, and `postmortem` — so the
command is useful on a project that has never written a line of lifecycle
configuration. `inbox` has none: it runs before an item exists. A stage my
project does configure replaces them outright; writing `builtin: true` in that
stage's `prompt:` list puts them back, composed with my own in the order I
declared them.

**The shipped instructions name my item's own body, not a fixed filename.** The
`spec` and `plan` instructions resolve it the same way `tcw work show` does —
`initial-request.md` once the `request` stage has written one, and the
`intake.md` the item arrived as otherwise — so an item created from a pipe or
adopted from the inbox is never sent after a document nobody wrote. On an item
with neither, they name no file at all rather than inventing one, and the `spec`
instructions say to read a raw intake as the request instead of drawing
conclusions from the request that is missing.

They come out on **stdout alone**, so I can pipe them straight into an agent.
Every check's own output, and every error, goes to stderr — and any failure
prints *nothing* on stdout, so a pipeline receives the whole instruction or none
of it rather than a fragment.

**It writes nothing**: no lifecycle document, no draft, no status change, no
field. Running it purely to read the instructions is safe, which is what makes it
usable — reaching a stage should not mean weighing whether asking what to do will
change something.

A stage that makes no sense for the item's current status is refused **before any
hook runs**: `implement` on a backlog item, or `spec` on one already closed.
`verify` is legal from `active` as well as `review`, because an item can be
closed without ever having been submitted. `postmortem` is the out-of-band
exception, legal in review and after completion — but not on a discarded item,
which was closed without shipping. `tcw work stage inbox` is refused too, and
says why: `inbox` runs before an item exists, so there is no item to resolve a
stage against.

`--no-exec` runs nothing at all — not the checks, not the `generate:` scripts,
and it will not even read a `file:` binding — printing what it *would* have run
to stderr instead. What resolves without running anything still prints, so it is
a dry run rather than a no-op. It is how I read an unfamiliar project's lifecycle
before triggering any part of it.

A project-qualified reference resolves against the owning node, so I can ask
about a descendant's item from the enclosing project.
