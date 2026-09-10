# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Reporting a problem to TCW no longer means publishing your project's names

The TCW issue tracker is public. The project you are reporting from often is not
— and a bug report written the obvious way carries its names into the open:
the repository and branch you were on, the directory you ran the command in, the
names you gave your own work items, and the wording of your own product
descriptions. Once an issue is filed, none of that can be taken back.

So a report now starts from a generic example that mirrors your setup instead of
from the real thing. The parts a maintainer actually needs all survive the swap:
the command you ran with its real flags, the error with its real type and
message, and the sequence that produced it. Only the names change. What a report
is allowed to contain is still entirely your call — this is a default worth
having, not a rule, and you can leave a real detail in when you want it there.

Two smaller things come with it. Reproducing the problem on a clean install and a
scratch project is worth a try, because those steps are generic already and they
show the problem is not something local to your machine; a report is perfectly
welcome without them. And that reproduction does not have to run in your own
checkout — it can be handed to a subagent working in a temporary directory.

## Search your work items by describing what you want

Describe what you are looking for and get back the matching items as a table:
`/tcw-work-search blocked CLI items, ignore the docs ones, highest priority first`.
You can say what to look for, what to ignore, and how to sort it, in your own
words.

The answer carries the same columns the board prints — the item's name, where it
is in the lifecycle, its priority, title, tags, and the blockers, owner, and
ready-to-close state a board row shows when they apply. It is copied from the
board rather than worked out again, so the table cannot tell you something the
board would not.

The search covers your live board and reaches closed work when you ask for it,
so "have we done this before" finds the finished item instead of missing it. It
spans connected projects when your question does, and keeps each item's full
address so every row is one you can act on. It tells you how it read your
request, and says plainly when nothing matched. Nothing is changed by searching.

## Getting TCW into a cloud session

The README now shows how to make `tcw` available in a throwaway agent
environment — Claude Code on the web, a container, a CI job — where anything you
install by hand is gone by the next session. It is a short script in your own
repository, wired to run when a session starts, with the three rules that decide
whether such a script helps or wastes the session. If your board lives in
another repository, it also covers the one command that fetches it.
