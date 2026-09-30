# Stop a custom merge driver from making --already-integrated pass unmerged work

## What is wanted

Find out whether a repository's own merge settings can make
`tcw work complete --already-integrated` accept a branch whose work is not
merged, and close the hole if they can.

`branch_integration` treats "`git merge-tree --write-tree HEAD <branch>` produces
`HEAD`'s tree" as proof the branch is already merged. A `.gitattributes` entry
such as `merge=ours`, with `merge.ours.driver=true` configured, resolves every
file both sides changed in `HEAD`'s favour. If `merge-tree` honors that, the
branch's edits vanish from the trial merge, the check passes, and the branch is
deleted with its work unmerged.

The first question is factual: does `git merge-tree` run custom merge drivers?
If it does, the check should run with those drivers overridden (for example
`-c merge.<name>.driver=…`, or an equivalent option). If it does not, record the
evidence and close the item.

## Notes

- Open question from the adversarial review of #72
  (`2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create`).
- Reference material: asked; none provided beyond the entry.
- Written at triage from the entry; the maintainer raised no questions on it.
