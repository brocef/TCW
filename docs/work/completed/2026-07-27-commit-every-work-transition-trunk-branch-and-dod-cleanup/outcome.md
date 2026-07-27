# Outcome

All planned tasks shipped, one commit each, suite green at every boundary.

| Commit | Task |
|---|---|
| `e34f082` | Commit plumbing, flag off |
| `04e6ef9` | Auto-commit switched on |
| `21cf293` | `--worktree` stops double-committing |
| `52bcff2` | `dod:` removal + `--already-integrated` |
| `282435e` | Documentation sync |

809 Python tests pass (from 785). `tcw validate` OK.

## What shipped

Auto-commit lives in `FsWorkStore._effect_transition`, the single choke point
both the CLI and `tcw serve` pass through. A CLI-side implementation would have
left web-app transitions staged but uncommitted — the stranded-state problem
this feature exists to remove, reintroduced through the other door.

Commits are scoped to the item's source and destination folders. There is one
test that fails only if that pathspec is widened back to `docs/work`; every
other test in the file passes either way.

`TransitionCommitError` is deliberately distinct from every other store error,
because the item *did* move. Reporting a refused commit as a failed transition
would be false and would invite a retry of something that already happened.

## Four things implementation disproved

Recorded because this epic's subject is documentation drifting from behavior.
All four were assertions written into the spec or plan before the code existed.

**1. Stderr matching was the wrong detection strategy.** The plan said to match
`git commit`'s "nothing to commit" output, having predicted two possible
sentences. Probing found *three* — `nothing to commit`,
`error: pathspec ... did not match any file(s) known to git`, and
`nothing added to commit but untracked files present` — all localized and all
version-dependent. `git status --porcelain` is the stable signal: contractually
formatted, and exit 0 even for a pathspec git has never heard of.

**2. Untracked entries had to be excluded from that check.** A scoped
`git commit -- <paths>` records tracked content only, so a pathspec holding
nothing else has nothing to commit. Porcelain reports `??` lines, which would
have driven the check into calling `git commit`, which then fails benignly and
would have been reported as a real error.

**3. Pathspecs had to be filtered individually.** `git commit` fails outright if
*any* pathspec matches nothing — which is exactly what a transition's vacated
source folder does when the item was created but never committed. This one broke
67 existing tests the moment auto-commit was switched on, which is how it was
found.

**4. A store outside a git repository never worked, and the spec said it should.**
Acceptance criterion 5 called for a transition outside a repo to succeed. It
cannot and never could: every write stages, and staging is `git add` with
`check=True`, so a non-git node fails at item *creation*, long before any
transition. Pinned as pre-existing behavior rather than "fixed". `tcw init`
refuses outside a repo for this reason.

A fifth, smaller correction: the plan proposed simulating a refused commit with a
held `index.lock`. That blocks `git mv` too, so the move never happens and the
case under test — moved, commit refused — cannot arise. A rejecting pre-commit
hook is the right instrument. `index.lock` still drives the unit-level test of
`git_commit_result`, where no move is involved.

## Verification beyond the suite

1. `tcw validate` → OK.
2. **A real repository driven through every transition**, with a second item's
   `spec.md` left deliberately uncommitted throughout. `git log --stat` shows
   five commits, each containing exactly the moved item's two files as clean
   renames; the unrelated file was still untracked at the end. That is the
   scoping claim confirmed outside the harness that asserts it.
3. `--worktree` end to end: the branch carries its own status move, two
   non-empty commits, nothing left in the tree.

## Notes

**`tcw serve` treating `TransitionCommitError` as success is the decision most
worth revisiting.** The item moved, so an error status would make the UI
re-render the old status and invite a retry — but the failure only reaches the
terminal running `tcw serve`, which a browser user is not watching. The honest
fix is surfacing it in the mutation response's `warnings`, which those endpoints
do not currently use. Deliberately not done here; it belongs with the web
complete-modal work the sibling child already owes.

**`--already-integrated` never touched `pr`.** Child 1 added that field
predicting this child would consume it, and it did not — the flag needs only the
`worktree` and `branch` fields that already existed. `pr` remains unconsumed.
That was the stated condition for calling it premature, and it is worth saying
plainly at epic close rather than quietly leaving the field in place.

**The `dod:` and `phase` removals now form a pattern worth naming:** a field
stops being read, existing items keep it inertly, and no migration pass is
added. Two instances is enough to make it the house answer for dropping a
persisted field; child 4 should state it once rather than have it rediscovered.
