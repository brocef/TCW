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
