# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## A checkout with only some of your repositories now works

If your projects are connected across more than one repository, a checkout that
has only some of them used to refuse every command — including the ones that had
no need of the missing project. That is fixed. A project TCW cannot find is left
out of the picture and everything else carries on.

You still hear about it. Every `tcw validate` run lists the connections it could
not follow, naming the project and where it was expected, so a genuine typo in a
path is still easy to spot. And when a command really does need the missing
project, it now says which one and where you declared it, instead of telling you
the project was never registered.

This is what makes TCW usable in a fresh clone or a cloud coding session that
starts with one repository on disk.
