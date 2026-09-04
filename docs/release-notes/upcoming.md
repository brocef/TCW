# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## A checkout with only some of your repositories now works

If your projects are connected across more than one repository, a checkout that
has only some of them used to refuse every command — including the ones that had
no need of the missing project. That is fixed. A project TCW cannot find is left
out of the picture and everything else carries on.

You still hear about it. Every `tcw validate` run names each connected project it
could not find, and where it expected it, so a project you thought you had does
not go unnoticed. (A connection is declared from both sides, so a project the
other side did find is not reported.) And when a command really does need the
missing project, it now says which one and where you declared it, instead of
telling you the project was never registered.

This is what makes TCW usable in a fresh clone or a cloud coding session that
starts with one repository on disk.

## Say where a connected project comes from, and fetch it

A project you connect to can now record which repository it lives in, exactly as
a work store already could. On a machine that has the project nothing changes and
nothing is contacted; on one that does not, `tcw provision` fetches it.

It follows the trail: a project fetched this way may point at others, and those
are fetched too, so your own configuration only ever has to name its own
neighbours. Every repository is printed before it is contacted, and `--dry-run`
shows you the whole plan without going near the network. A project this checkout
can already reach is never fetched, whichever side declared where it comes from,
so declaring a connection on both sides costs you nothing.

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
parent is one of these grouping projects — or one whose board this machine has
not fetched — instead of calling you the top of the graph. It also lists every
project you registered as a child, saying which ones keep no board and which ones
this machine has not fetched, instead of leaving them out and making you look
like a leaf.

## Choose what happens to finished work

Until now a completed or discarded item was left on your disk and kept out of
git, which meant it never reached anybody else — a fresh clone of a project has
no finished work in it at all.

You can now say what you want instead, per status, in `tcw-config.yaml`. Leave it
alone and nothing changes. Ask for finished work to be deleted and TCW commits
the item first and removes it second, so the documents stay in the repository's
history and `tcw work show` tells you which commit to fetch them from. Nothing is
ever deleted unless you asked for it, and a typo in the setting is reported
rather than treated as a yes.

One thing to know before turning it on: it cannot be combined with the ignore
rules that scaffolding writes, because git would remove the item before it was
ever recorded. TCW refuses that combination and tells you which rules to drop.

## Keep your own copy before finished work is deleted

If you have asked TCW to delete finished work, you can now have it hand the item
to your own archive first — an object store, another folder, anything a command
of yours can reach. It runs while the item is still there and already committed,
and it gets the item's location and how it was resolved in the environment.

If your archive fails, nothing is deleted. The item stays exactly where it is and
TCW tells you to run `tcw work delete` once you have fixed it. Note that TCW
cannot check whether your command really archived anything, and that the web UI
does not run commands at all — an item resolved there waits for you to finish the
removal from the command line.

## Extending a project that keeps its trees somewhere else

If a project you extend has moved its taxonomy or capabilities out of the default
folder, extending it works now. It used to report that the project had no such
tree at all — naming a folder you had never chosen — and if the tree was one you
had yet to fetch, it said the same thing rather than telling you to fetch it.

## Finishing an epic from a checkout that cannot see all of it

Slices of an epic often live in other projects. If your checkout does not have
one of them, TCW can no longer see whether that project's slices are finished —
and it used to read "cannot see" as "nothing left", so completing the epic
quietly closed it over work that was still open.

It now stops and tells you which projects are missing, so you can complete the
epic from a checkout that has them, or fetch them, or override it deliberately
with `--force`.

For the same reason, running a `tcw` command in a folder that is not a TCW
project tells you so again, instead of behaving as though it were an empty one.

## Extending a chain of projects

Extending a project that itself extends another now works when any of them keeps
its taxonomy or capabilities somewhere other than the default folder — the chain
used to break one link past the first such project. Long chains are also much
faster, and a loop of projects extending each other is now reported by
`tcw taxonomy check` and `tcw capabilities check` instead of silently giving each
side a different view.

