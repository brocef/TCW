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

## Say where a connected project comes from, and fetch it

A project you connect to can now record which repository it lives in, exactly as
a work store already could. On a machine that has the project nothing changes and
nothing is contacted; on one that does not, `tcw provision` fetches it.

It follows the trail: a project fetched this way may point at others, and those
are fetched too, so your own configuration only ever has to name its own
neighbours. Every repository is printed before it is contacted, and `--dry-run`
shows you the whole plan without going near the network.

Together with the change above, this is what lets a session that starts with one
repository on disk read the taxonomy, capabilities and boards that live in the
others.

## A project that only groups other projects no longer hides their work

If you register a project purely to group others — a repository root whose
packages keep the boards — anything that had to reach across it used to stop
there without saying so. An epic one level further up simply looked like it did
not exist, and a rollup quietly stopped listing the work under it.

Those relationships now pass through. `tcw work escalate` reaches the nearest
project that actually keeps a board, and `tcw work nodes` tells you when your
parent is one of these grouping projects instead of calling you the top of the
graph.
