As a user whose project lets TCW delete its resolved work items, I bind my own
command to the moment just before an item is removed, so I can keep a copy
wherever I want one — an object store, another folder, anywhere my command can
reach. TCW knows nothing about where that is.

The binding goes under `work.lifecycle.auto-delete` in `tcw-config.yaml`, with
`pre` and `post`, exactly as the other transitions take them. My command runs
from the project root with the item's location and its resolution in the
environment alongside the variables every hook already gets, so a one-line script
can archive the item without deriving anything: the location is the store's own
answer, which matters because my work store may live in a different repository
than my code.

**If my `pre` command fails, the item is not deleted.** It stays in its resolved
folder, already committed and already recorded in the graveyard, and the command
that was resolving it exits non-zero and tells me which binding failed. Nothing
is lost because my upload was. When I have fixed it, `tcw work delete <slug>`
runs the same bindings and finishes the deletion. A `post` command runs after the
removal is committed, and its failure does not undo it.

A command that moves the item away itself is supported rather than merely
tolerated: the deletion treats an item that is already gone as done.

Two things this does not promise. TCW cannot tell whether my command really
archived anything — a command that exits zero satisfies it completely. And a
`skill:` binding here is named for my agent to invoke rather than run, so
anything I need guaranteed belongs in a `command:`.

`tcw serve` runs no hooks, so it does not perform the deletion either: an item
resolved through the web UI waits in its resolved folder for a CLI
`tcw work delete`, rather than being removed without my archive running.

Planning doc: 2026-09-03-an-auto-delete-step-with-hooks-so-a-consumer-can-archive-an-item-before-it-is-removed
