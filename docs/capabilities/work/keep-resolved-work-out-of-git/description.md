As a user, I keep my resolved work items on disk but out of the repository, by
gitignoring the status folders they land in. The record stays useful locally
while the tracked tree carries only work that is still live — which matters for
a project whose `docs/work/` history is internal detail rather than part of what
it ships.

I set it up once: add `docs/work/completed/` and `docs/work/discarded/` to
`.gitignore`, then run `git rm -r --cached` on both to drop what git already
tracks there — a `.gitignore` alone does not untrack a file git has already
seen, including the `.gitkeep` that `tcw work init` leaves behind.

After that, [completing](tcw://C/work/complete-a-work-item) or
[discarding](tcw://C/work/discard-a-work-item) an item works as it always did,
except that the transition commit **removes** the item from the repository
instead of recording a rename into the ignored folder. The files stay on disk,
my working tree is left clean, and the item still appears in
`tcw work list --all` and still opens with `tcw work show`.

Nothing about this is specific to `completed/` or `discarded/`: any transition
destination I have ignored behaves the same way, and a node that ignores nothing
sees no change whatsoever.

It changes only what happens from here on. Items resolved before I adopted the
ignore stay in the history that already recorded them; taking them out of past
commits is a history rewrite, and TCW does not do that for me.
