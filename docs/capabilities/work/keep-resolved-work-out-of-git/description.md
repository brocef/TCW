As a user, I keep my resolved work items on disk but out of the repository, by
gitignoring the status folders they land in. The record stays useful locally
while the tracked tree carries only work that is still live — which matters for
a project whose `docs/work/` history is internal detail rather than part of what
it ships.

This is the default: [scaffolding the work
component](tcw://C/cli/scaffold-the-doc-trees) writes the `.gitignore` rules for
me, keeping each folder's `.gitkeep` tracked so the folder itself still arrives
in a fresh clone. On a node scaffolded before that default existed, re-running
`tcw work init` adds the rules, and I then run `git rm -r --cached` on both
folders to drop what git already tracks there — a `.gitignore` alone does not
untrack a file git has already seen. If I would rather track my resolved work, I
delete the rules.

When `work.path` points into another repository, the same rules are written
relative to that repository's root and resolution commits remove tracked work
there. The owning code repository is not modified by those transitions.

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
