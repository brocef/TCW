As a user, I describe what I am looking for on the board — what to look for,
optionally what to ignore, and optionally how to sort it — and get back the
matching work items as a table. This is an assistant-driven read rather than a
`tcw` subcommand, because deciding whether an item is _about_ what I asked is
judgment a substring match cannot supply. I reach it by asking, or with
`/tcw-work-search` in Claude Code, and it works the same under either harness.

The search covers the live board by default and reaches closed work when my
description asks for it, so "have we done this before" finds the completed item
rather than silently missing it. It spans connected projects when I ask about
them, and keeps a descendant item's qualified `<project-id>/<slug>` address so
every row in the answer is one I can address.

The result carries the same columns the board prints — slug, status, lifecycle
stages, priority, title, tags, and the blockers, claimant, and ready-to-close
state a board row shows only when it applies — transcribed from the board rather
than recomputed, so the table cannot disagree with `tcw work list`. It tells me
how it read my description, and says plainly when nothing matched instead of
handing me an empty table. Nothing is changed by searching: no item moves, no
field is edited, no file is written.
