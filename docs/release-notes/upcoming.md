# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Blockers you can actually remove

Clearing a blocker used to fail silently: you would run
`tcw work edit <item> --unblocked-by "…"`, see `edited <item>`, and find the
blocker still there. Three things were wrong, and all three are fixed.

- **Removing a blocker that isn't there is now an error.** The command tells you
  `no such blocker on <item>: <ref>` and stops, instead of reporting success.
- **You can copy the blocker straight off the board.** Items list their blockers
  as `external: waiting on vendor`, and that exact string is now accepted by
  `--blocked-by` and `--unblocked-by`. The bare text still works too.
- **Blocker text can contain commas.** `--blocked-by` and `--unblocked-by` are now
  repeatable — use the flag once per blocker instead of separating them with
  commas.

**If you use commas today, update your commands.** `--blocked-by "a,b"` used to
record two blockers; it now records a single blocker called `a,b`. Write
`--blocked-by a --blocked-by b` instead. (`--blocks` is unchanged.)

One more improvement: if you combine adding and removing blockers in one command
and the removal fails, nothing is applied at all — you no longer end up with a
half-finished edit.

## Link work items in any connected project

Referring to an item in another project used to work in one direction only: you
could point at a project below you, but never at the one above. That made a
common setup impossible to write down — when a large piece of work is split up,
each sub-project's slice wants to link back to the overall item in the parent
project, and that link was rejected as if the item didn't exist.

Now `<project-id>/<item>` reaches **any** project you're connected to — above,
below, or alongside. It works both for commands
(`tcw work show parent-project/some-item` from a sub-project) and for links you
write in your documents. Projects still have to be properly connected to each
other; nothing new is reachable that wasn't already registered.

Two things to know:

- Because you can now address items in a parent project, a command like
  `tcw work start parent-project/some-item` will act on that project. That is
  intentional, and it already worked that way in the downward direction.
- The local web app still shows your project and the ones beneath it. A link
  pointing upward is valid and passes `tcw validate`, but you can't open it from
  the sub-project's web view.

If you get a project name wrong, the error now says so plainly —
`no such project in this graph: <name>` — instead of the old, misleading
"no such work item".
