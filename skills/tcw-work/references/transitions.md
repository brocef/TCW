# Transitions

A **transition** moves an item's status. A **stage** produces an artifact.
Nothing is both.

**You drive transitions — the tool never moves an item for you**, so an item's
status is only as accurate as you keep it. Two are easy to forget: `start` before
the first line of code, and `complete` the moment work is verified. Keep status
in step as you go; do not batch the moves at the end.

**TCW commits every transition itself** (`work.auto-commit-transitions`, default
true), scoped to the item's own folders so unrelated edits are never swept in.
Do not commit a status move by hand. If a commit is refused, the item still
moved and the tool says so — commit it yourself, do not re-run the transition.

**A gitignored destination is untracked rather than moved.** `tcw work init`
gitignores `completed/` and `discarded/` by default (their `.gitkeep` stays
tracked, so the folders survive a clone), so completing or discarding usually
produces a transition commit that *removes* the item from git and leaves the
files on disk. Nothing else changes: the item still moves, still lists, still
reads. A node whose `.gitignore` lacks those rules gets a plain tracked rename.

Transitions are **never delegated to a subagent**. They carry the gates, and
those are evaluated once, by the session holding the user relationship.

## start — `backlog → active`

`tcw work start <slug> [--worktree] [--force]`

- Unresolved blockers refuse the move. `[gated]`
- An initiative child refuses until its epic is `active`. `[gated]`
- `--force` overrides both. `[gated]`
- `--worktree` isolates the item's code on its own branch and worktree;
  transitions stay on the primary checkout, edits ride the branch, and `complete`
  merges back. It commits regardless of `auto-commit-transitions`, because the
  branch is cut from `HEAD` and would otherwise not contain the item's own move.

`plan.md` being present is a **check**, not a gate: the tool does not refuse.

## submit — `active → review`

`tcw work submit <slug>`

No gates. `review` means implemented, acceptance pending — **not** resolved: the
item still blocks its dependents and still holds its epic open, because
verification can reject it.

`outcome.md` being present is a check, not a gate.

## rework — `review → active`

`tcw work rework <slug>`

- **Refuses while `refined-outcome.md` is present.** `[gated]` That document
  asserts the work was verified; after a rejection it is false. Delete it and
  write `rework.md` first — TCW never deletes it for you.

The only reverse edge in the machine. Nothing leaves `completed` or `discarded`.

## complete — `review | active → completed`

`tcw work complete <slug> --resolution done --confirm`

- `--confirm` is required. `[gated]`
- Unresolved blockers refuse a shipment. `[gated]`
- An epic refuses while initiative children are open. `[gated]`
- **Capability reconciliation is enforced**, not merely acknowledged: it fails if
  a capability the item declared `new:` still reads `Missing`, or a declared path
  does not resolve. Flip it, mark it `Omitted`, or `--force` with the reason in
  `outcome.md`. `[gated]` **REQUIRED SUB-SKILL: Use tcw-capabilities.**
- For a `--worktree` item, the work branch is merged back before teardown, and a
  merge conflict fails closed — resolve and re-run rather than forcing. `[gated]`
- **Run it from the primary checkout, not from inside the item's own worktree.**
  Both the merge-back and the teardown act on the primary checkout, so from
  inside it refuses and names where to re-run. `[gated]` Completing from an
  unrelated worktree is fine. Everything else — `submit`, `rework`, the reads —
  works from either. If you took the item into a worktree, `cd` back out before
  `complete`.
- From `active` it prints that the verify stage was skipped. `[prompted]` —
  advisory only: no second confirmation, and the exit status is unchanged.
- `--already-integrated` skips the merge-back when the branch was merged outside
  TCW (a merged PR). Every other gate still runs.
- The Definition-of-Done checklist is printed before `--confirm`. `[prompted]` —
  it is no longer stored. The node sets its own list in `docs/work/dod.yaml`,
  which **replaces** the built-in five (`tests pass`, `docs synced`,
  `capabilities reconciled`, `reviewed`, `version offered`) rather than extending
  them — omit one and it is gone, with no error.
- **If the item came from a GitHub issue**, closing it out means saying so on the
  issue and closing it — read `tcw-triage-issues` §8. `tcw work path <slug>` →
  `initial-request.md` → `## Origin` is where the issue URL lives. Nothing is
  posted without the user approving the exact text.

A completable epic — every child resolved — may complete **directly from
`backlog`**, with no throwaway `start`.

## discard — `backlog | active | review → discarded`

`tcw work complete <slug> --resolution wontfix|duplicate|superseded --confirm`

**The resolution picks the destination**, so `completed/` answers "what shipped?"
on its own. `discard` is a transition id for binding purposes but not a verb of
its own.

- `--confirm` is required. `[gated]`
- Blockers do **not** gate a discard: being blocked indefinitely is one of the
  commonest reasons to give up.
- Capability reconciliation degrades to a warning. Mark leftovers `Omitted`.
- A worktree is torn down but its **branch is kept**, and named in the warning —
  deciding work is unwanted is not authority to destroy an unmerged branch.
- **No Definition-of-Done checklist is printed at all** — `complete` computes it
  only when shipping. So if the item came from a GitHub issue, *nothing prompts
  you*: this line is the only prompt there is. Read `tcw-triage-issues` §8 and
  answer the issue. `wontfix` and `duplicate` close it; **`superseded` closes it
  only if the superseding item absorbed the ask** — if it deferred the ask
  instead, reply and leave the issue open, because closing it would tell the
  reporter their request was refused when it was postponed.

`tcw work drop <slug> --confirm` deletes a backlog item outright. That is not a
transition and leaves no record, which is why `--confirm` is required: without it
the command names what would go and refuses. `[gated]`
