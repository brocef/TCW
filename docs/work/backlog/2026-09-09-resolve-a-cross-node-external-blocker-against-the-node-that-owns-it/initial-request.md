# Resolve a cross-node external blocker against the node that owns it

## What is wanted

When an item waits on another node's item, finishing that item should free the
one waiting on it. Today it never does. A blocker that names another node's item
(`blocked_by: - external: <node>/<slug>`) stays unresolved forever, even after
that item completes:

- `tcw work start <dependent>` still refuses, naming a completed item.
- `tcw work reconcile <epic>` prints **"Next: all blocked or complete"**, which
  reads as "this epic is finished" when its next slice is only waiting on work
  already done.

The only ways forward are `--force`, which waives every gate including unrelated
blockers and the inactive-epic check, or `tcw work edit --unblocked-by`, which
deletes the edge so the item no longer records what it waited on. Neither leaves
an accurate record. On a three-slice cross-node epic every hand-off needed that
manual edit, and one rollup was read as complete when it was not.

GitHub issue #28 and the 2026-08-25 inbox note report the same defect; both are
kept verbatim in `intake.md`.

## What is true today (checked 2026-09-15)

- `WorkStore.unresolved_blockers` in `tcw/store/base.py` adds every `external`
  entry to the unresolved list without looking at it. Its docstring says so: "An
  entry is unresolved if it is external, or a slug whose item is not resolved".
- `_ready` in `tcw/work/recursion.py`, which computes reconcile's **Next** line,
  independently treats any `external` entry as blocking.
- **Where the entry comes from.** The issue says `tcw work delegate` / `escalate`
  record the dependency. They do not: both only write a request into the other
  node's inbox and never set `blocked_by`. The `external:` entry is written by
  `--blocked-by`: `WorkStore._entry_for` stores any reference that does not match
  a local item as `{external: <text>}`.
- **What the rollup actually resolves.** The intake says the rollup "already
  resolves cross-node references". It is narrower than that. `_tasks_for` collects
  items whose `initiative` is the epic, from this node and its direct children, so
  the target showed as `completed` only because it belonged to the same epic.
  Nothing parses a `<node>/<slug>` string anywhere in `tcw/`, and a dependency on
  a sibling or parent node, or on an item outside the epic, has no resolver.

## Constraints

- **Genuinely external blockers stay free text.** Some blockers name things
  outside TCW (for example an app-signing fingerprint someone must supply) and
  must keep blocking.
- **Only open items matter.** A completed or superseded item carrying a stale
  reference is history, not a defect. The fix concerns items that are not yet
  resolved.
- **Storage neutrality.** `unresolved_blockers` lives in the storage-neutral base
  class, but finding another node today uses filesystem-only helpers
  (`child_nodes`, `registered_project_id` in `tcw/store/fs.py`). Which layer does
  the cross-node lookup has to pass the abstraction litmus test in
  `docs/lifecycle/abstraction.md`.
- **A completed target may exist only as a tombstone** (the record kept in
  `graveyard.yaml` after its folder is removed), so resolving it must consult
  that record.
- **Both call sites** (`unresolved_blockers` for `start`/`complete`, `_ready` for
  reconcile's Next line) must agree, or reconcile can name an item `start` then
  refuses.

## Options the requester offered (the spec chooses)

1. A distinct blocker kind for an in-TCW cross-node reference
   (`blocked_by: - work: <node>/<slug>`) that `start`, `list` and `reconcile`
   resolve, leaving `external:` for outside dependencies. Since `delegate` and
   `escalate` write no blocker, this means `--blocked-by` writing the new kind
   when the reference names another node's item.
2. Keep `external:` but resolve any value matching `<known-node-id>/<slug>`, and
   report it as satisfied once that item is resolved.
3. At minimum, have `reconcile` say when a blocker names a completed item, so
   "all blocked or complete" stops being ambiguous.

Also to decide: whether a reference that cannot be resolved from where the
command runs should block (today, safe but sticky), warn and proceed, or block
and say why ("cannot resolve `proposit-mobile/…` from this node").

## Repro

Two registered nodes, A and B.

1. In B: `tcw work new "thing"`.
2. In A: `tcw work new "dependent" --blocked-by "external: B/<thing-slug>"`.
3. In B: `tcw work start <thing-slug>`, then
   `tcw work complete <thing-slug> --resolution done --confirm`.
4. In A: `tcw work start <dependent-slug>` refuses, naming the completed item.

## Out of scope

- Changing `delegate` / `escalate` to record blockers. They are inbox-only by
  design.
- Clearing stale references on items that are already resolved.

## References

- [GitHub issue #28](https://github.com/brocef/TCW/issues/28) — the requester's
  report and the three remediation options above.
- [`2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`](tcw://W/2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile)
  — the same node graph and walk (#30). How far that item decides reconcile walks
  changes which nodes a cross-node reference can be resolved against, so do that
  one first.
- [`2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`](tcw://W/2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root)
  — its cross-node pass looks up `external:` blockers in the owning node by hand,
  the manual version of this fix.

## Notes

- Asked for reference material beyond the intake; none provided.
- The requester chose to leave the remediation open for the spec rather than
  keep option 1 as a preference, once told that `delegate` / `escalate` write no
  blocker.
- The standing reply already posted on #28 promised an item under an earlier slug
  that was never created in this repository (commit e7b7b19b). This item replaces
  it. Correcting that reply, and closing the issue, waits for the fix to be
  published, and the exact text needs approval first.
- The intake's line citations (`base.py` 1883–1907, `recursion.py` 138) are
  stale; this request cites functions by name instead.

## Folded in: 2026-09-16-record-a-blocker-naming-a-resolved-item-as-a-slug-not-as-free-text

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

## Record a blocker naming a resolved item as a slug, not as free text

### What happened

On 2026-09-16, opening the children of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`,
the coordinating session ran:

```sh
tcw work edit <child> --blocked-by 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
```

That item was already completed and its folder removed from the board
(`tcw work show` reports it `(resolved)`, "last present in commit 4002ffb3").
The edit wrote:

```yaml
blocked_by:
- external: 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
```

An `external:` blocker is free text and never resolves, so the child could never
have started. The same slug written as `slug:` by the request stage on the epic
itself resolved correctly and `tcw work start` on the epic passed.

### Cause (read, not yet tested)

`WorkStore._entry_for` (`tcw/store/base.py`, around line 3150) decides the entry
kind with `self.get(ref) is not None`, which only sees items still on the board.
A slug the store has resolved and recorded in `graveyard.yaml`
(`self.tombstone(slug)`) is treated as unknown text.

### What is wanted

- A ref naming a resolved item the store has a record of is written as
  `slug:`, the same as a live item. Probably also worth a message saying the
  blocker is already resolved, since blocking on finished work is usually a
  mistake.
- Check every other caller that classifies a ref the same way (`new
  --blocked-by`, `edit --blocks`, `--unblocked-by` matching) for the same shape.
- Existing `external:` entries whose text is exactly a recorded slug: decide
  whether `tcw validate` should report them.

### Related

- `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`
  — a different case (another node's item written as `external:`), same symptom.

### Origin

Found by the coordinating session while implementing the epic above;
the requester asked for it to be filed as a work item on 2026-09-16.
