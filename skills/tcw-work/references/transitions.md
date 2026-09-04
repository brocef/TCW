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
produces a transition commit that _removes_ the item from git and leaves the
files on disk. Nothing else changes: the item still moves, still lists, still
reads. A node whose `.gitignore` lacks those rules gets a plain tracked rename.

**`work.retain` decides whether the item survives the transition.** Default true
for both resolved statuses, so nothing changes unless a node says otherwise.
Where a status is set `false`, a resolving transition writes *two* commits — the
item lands in its resolved folder and is committed, then the folder is removed —
and the graveyard entry records the first commit, so `tcw work show <slug>` on a
deleted item still names where its documents can be fetched from. This combination
is refused while the destination is gitignored, because the first commit would
then hold a removal rather than the item; the message names the rules to drop.
Backfill the graveyard with `tcw work tombstone add` before adopting it on an
older board, or a deleted slug can be reissued.

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
- With a `work.path` in **another** repository, the setup splits by owner: the
  item's state commits in the store repository, `.gitignore` in the code one, and
  the worktree is created only after both succeed. The two commits cannot be
  atomic — on a failure the command names which repository already committed and
  creates no worktree, so re-run `start` after fixing that repository. The work
  branch carries the code side only; the item lives where `tcw work path` says.

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
  An item whose folder moved while the branch was open (any `submit` does this) is
  **not** a conflict: the merge-back carries branch files into the folder's new
  location. Only a genuine content conflict stops it.
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
  issue and closing it — read `tcw-triage-issues` §8. `tcw work show <slug>` →
  the item's body → `## Origin` is where the issue URL lives; on an item filed
  from an issue that body is its `intake.md`, not a request. Nothing is posted
  without the user approving the exact text.

A completable epic — every child resolved — may complete **directly from
`backlog`**, with no throwaway `start`.

**Resolving records the slug.** Both `complete` and `discard` write the item's
slug to `graveyard.yaml` at the store root, in the same commit as the status
move, so `tcw://W/<slug>` references to it keep resolving after its documents
leave the tracked tree. A slug with no record is still an unresolvable
reference — that is the distinction, and it is why `tcw validate` now gives the
same answer in every checkout rather than depending on who ran the transition.

The transition **refuses** if `graveyard.yaml` cannot be written safely: it is
unparseable, is not a mapping, or holds uncommitted changes TCW did not make.
Nothing moves on that refusal. Since every graveyard write commits itself, a
dirty graveyard means something already went wrong — do not work around it by
committing the stray edit under the item's name. `[gated]`

For work resolved before the store kept records, `tcw work tombstone add <slug>`
records one after the fact; see [`commands.md`](commands.md).

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
  only when shipping. So if the item came from a GitHub issue, _nothing prompts
  you_: this line is the only prompt there is. Read `tcw-triage-issues` §8 and
  answer the issue. `wontfix` and `duplicate` close it; **`superseded` closes it
  only if the superseding item absorbed the ask** — if it deferred the ask
  instead, reply and leave the issue open, because closing it would tell the
  reporter their request was refused when it was postponed.

`tcw work drop <slug> --confirm` deletes a backlog item outright. That is not a
transition and leaves no record, which is why `--confirm` is required: without it
the command names what would go and refuses. `[gated]`

## auto-delete — `completed | discarded → (removed)`

Not a verb you type in the normal case. It runs as part of a resolving
transition when `work.retain.<status>` is `false`, after the item has been
committed where it landed and before it is removed — so a binding sees a
complete, already-recorded artifact and a failure costs nothing.

- `pre` bindings run while the item is still on disk. A failure **keeps the
  item**: resolved, recorded in the graveyard, committed, and reported as
  finishable. `[gated]`
- `post` bindings run after the removal is committed. A failure never undoes it.
- `TCW_ITEM_PATH` and `TCW_RESOLUTION` are exported alongside the usual four, so
  an archive command needs no lookup. The path is the store's own answer — never
  compose one from `TCW_NODE_ROOT` — and it is where the item is *when the hook
  runs*, which is why a `pre` and a `post` on the same transition can differ.
  `TCW_ITEM_PATH` is set on every transition, not only this one; `TCW_RESOLUTION`
  only where there is a resolution.
- A binding that moves the item away itself is supported: an already-absent
  folder counts as removed.
- `tcw work delete <slug>` finishes a removal a failed `pre` left pending,
  running the same bindings. It refuses a live item — that is `drop` — and one
  whose status the project still retains.
- `tcw serve` runs no hooks and therefore performs no removal: an item resolved
  through the web UI waits for a CLI `tcw work delete`.
- Guarantees belong in a `command:`. A `skill:` binding here is reported for the
  agent to invoke, not run, and the removal proceeds either way.
