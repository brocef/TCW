As a user, I run `tcw work start <slug>` to move an item from backlog into active. The tool refuses if the item has unresolved blockers; I pass `--force` to override.
For initiative child tasks, the tool also refuses to start the task until its related epic is active.

TCW commits the status move itself, scoped to the item's own folders so unrelated edits in my working tree are never swept in. I turn that off with `work.auto-commit-transitions: false` in `tcw-config.yaml`, and `work.trunk-branch` adds an advisory warning when I transition from some other branch.
Starting work is an atomic claim, and a claim TCW cannot record is refused before the item moves — outside a Git repository the item stays in the backlog and the command says why. I identify the claimant with `--owner`,
`TCW_WORK_OWNER`, or my Git email/name; the active item records that identity and
its UTC start time. If another process wins, TCW reports the existing claim so I
can select another item. `--take-over --owner <identity>` deliberately replaces
an active claim; `--force` remains limited to blocker and initiative gates.

With `--worktree`, TCW persists the setup in whichever repository owns each part:
the item's own state in the work store's repository, the `.worktrees/` ignore rule
in the code repository, and only then the branch and linked worktree. When
`work.path` puts those in the same repository — the default — that is still one
commit carrying both. When they differ, the two commits cannot be made atomic, so
a refusal stops the command, names the repository that already committed, and
leaves no worktree behind for me to re-run against. The work branch therefore
carries the code side only: a Git branch cannot contain lifecycle files that live
in another repository, and the item stays visible through `tcw work path <slug>`.
