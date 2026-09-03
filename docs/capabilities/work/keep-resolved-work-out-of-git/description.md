As a user, I decide what becomes of a work item once it is resolved, per resolved
status, and there are three answers.

**Gitignored** — the default arrangement, and the one described below: the item
stays on disk and out of the repository. Worth knowing what that costs: it stays
on *my* disk, so nobody else's clone has it. **Retained** — I delete the ignore
rules and the items are tracked like anything else. **Auto-deleted** — I set
`work.retain.<status>: false` and TCW commits the item into its resolved folder,
then removes it in a second commit, so my tree stays clean and the documents are
in the history where any clone can fetch them; `tcw work show` on such an item
tells me which commit, and says so plainly if that commit no longer exists here.

Nothing is deleted unless I ask. The default retains, and a malformed `retain`
reads as the default and is reported by `tcw validate` rather than quietly
becoming a deletion. Auto-delete and the ignore rules cannot both apply to one
status — git would untrack the item before it was ever committed, leaving no copy
anywhere — so TCW refuses that combination before anything moves and names the
rules to remove. Once I name a status in `retain`, scaffolding stops writing
rules for it.

The rest of this describes the gitignored arrangement in detail.

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

What differs now is what I am *told*. If I ignore a destination outside those
two, the transition still behaves the same way but prints an advisory line on
stderr saying the item is on disk and Git will not record it. TCW cannot tell a
rule I meant from one that arrived by accident, so it says so rather than
guessing. `completed/` and `discarded/` stay silent — those are TCW's own doing,
and a line on every completion is one I would learn to ignore.

It changes only what happens from here on. Items resolved before I adopted the
ignore stay in the history that already recorded them; taking them out of past
commits is a history rewrite, and TCW does not do that for me.
