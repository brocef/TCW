# Can a custom merge driver make --already-integrated pass unmerged work?

Open question from the adversarial review of #72
(`2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create`).

`branch_integration` treats "`git merge-tree --write-tree HEAD <branch>` gives
`HEAD`'s tree" as proof the branch is merged. A `.gitattributes` entry such as
`merge=ours` with `merge.ours.driver=true` would resolve every file both sides
changed in `HEAD`'s favour, hiding the branch's edits there; the check would pass
and the branch would be deleted. Verify whether `merge-tree` runs custom drivers,
and if so pass `-c merge.<name>.driver=` overrides or `--no-...` equivalents.
