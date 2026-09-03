# Spec — An auto-delete step with hooks

## Capability changes

- **new** — `work/archive-a-resolved-item-before-it-is-deleted`. The ability the
  request asks for: bind a command that runs while the item still exists, and
  keep the item if it fails.
- **changed** — `work/configure-the-work-lifecycle`. Its body enumerates the
  hook environment as exactly `TCW_SLUG`, `TCW_STATUS`, `TCW_TRANSITION` and
  `TCW_NODE_ROOT`, and describes the transition set. Both move.

## Problem

**There is no moment to bind to.** `TRANSITION_IDS`
(`tcw/store/base.py:609`) is `("start", "submit", "complete", "rework",
"discard")`, and `tcw validate` rejects any other id (`:1422-1425`). The deletion
introduced by the blocking item is not any of them: `complete` and `discard`
fire when the item is *resolved*, which under retention is not when it is
removed, and binding to them would fire on every resolution including the ones
that keep the item.

Nor would binding to `complete` be right even if the timing matched. The deletion
happens for `discarded` items too, and `complete`/`discard` are deliberately kept
apart because they mean "we shipped it" and "we gave up on it" (`:605-608`) — a
single archive intent would have to be written twice and kept in sync.

**A binding could not act on the item if it existed.** `hook_env`
(`tcw/work/hooks.py:28-39`) exports four variables:

    "TCW_SLUG", "TCW_STATUS", "TCW_TRANSITION", "TCW_NODE_ROOT"

None of them is the item's path. A `command:` binding runs with `cwd` at the node
root (`tcw/work/hooks.py:57`), and the store may be in another repository
entirely, so the path is not derivable — `commands.md` states plainly that a
store path must never be composed from the node root. An S3 upload has nothing to
upload.

**What already works and should not be rebuilt.** `run_pre`
(`tcw/work/hooks.py:81-93`) documents exactly the contract this needs: "A failure
means **do not touch the store**", and callers must invoke it before any write.
`select(...)` applies `when: {tags, not_tags, type}` conditions, so "archive only
bugs" or "archive only shipped work" needs no new mechanism. `run_post`
(`:96-108`) already documents that a failure never rolls back.

## Goals

- `auto-delete` is a bindable lifecycle step id with `pre` and `post`.
- A failing `pre` binding leaves the item where it is — resolved, committed, not
  deleted — and the transition exits non-zero saying so.
- A binding receives the item's location and its resolution, in addition to
  today's four variables.
- A hook that has already moved the item away does not cause a failure.
- `tcw work delete <slug>` finishes a deletion that a failed archive left
  pending, running the same bindings.
- `tcw serve` continues to run no hooks, and a deletion is not something it
  drives.

## Non-goals

- **Retention and the two-commit deletion.** The blocking item.
- Changing `run_pre` / `run_post` semantics, the binding kinds, or `when:`.
- Making `tcw serve` run hooks. Explicitly deferred by the requester.
- Uploading anything ourselves. TCW runs the consumer's command; it has no
  opinion about S3, and no dependency on one.

## Design

**A step, not a status transition.** `auto-delete` joins `TRANSITION_IDS` and the
`LIFECYCLE_STEPS` table (`tcw/store/base.py:908-931`) with
`moves: completed | discarded → (removed)`. It adds no `LEGAL_TRANSITIONS` pair
(`:493-502`), because no status changes — the item is already resolved and it is
leaving the store rather than moving within it. `postmortem` is the precedent for
a step that "never changes status" (`:902-903`), so the model already admits one.

It is *not* reached as a verb of its own during a resolution, exactly as
`discard` is not (`:927-929`): it runs as part of the resolving transition when
retention says to delete, and `tcw work delete <slug>` is the manual entry point
for the state a failed archive leaves behind.

**Two more environment variables.** `hook_env` gains the item's location and its
resolution. The location is what `tcw work path <slug>` prints — the store's own
answer, never composed — which is the only correct source per the store-path rule
in `commands.md`, and it is what both named scenarios need: an S3 upload tars it,
a folder move moves it.

Naming and shape follow the existing four. The resolution is `done`, `wontfix`,
`duplicate` or `superseded` — the vocabulary `WORK_RESOLUTIONS`
(`tcw/store/base.py:504`) already fixes — so a script can prefix its archive by
outcome without parsing anything.

**The hook point is between the two commits.** The blocking item lands the item
in its resolved folder and commits, then deletes and commits. `pre` runs after
the first commit and before the deletion: the artifact on disk is complete and
already recorded, which is what an archive wants, and a failure leaves a state
that is committed, recorded in the graveyard, and finishable later. `post` runs
after the second commit.

This is why the request's "custom completed transition" was read as attaching to
the deletion: at `complete` time under `retain: true` there is nothing to
archive, and under `retain: false` the content still exists at the moment that
matters — the one just before it stops existing.

**An already-moved item is success, not failure.** The move-to-another-folder
scenario means the `pre` binding itself removes the folder. The deletion must
therefore treat an absent path as done rather than erroring. Documented as part
of the contract, not left as an implementation accident, because a consumer will
build on it.

**Litmus test.** "Run the consumer's archival step before the item stops
existing" is a lifecycle-binding concern, and lifecycle bindings are already
outside the store by explicit design: `hooks.py`'s module docstring says a
`WorkStore` method that shells out "is one no remote adapter could honor", so
running commands is a CLI concern. This item adds a step id and two environment
variables to that CLI layer and touches no store interface. A tracker-backed
adapter fires the same step at the same moment and exports its own location
string.

**Harness.** `command:` bindings are run by the CLI and behave identically under
Claude and Codex. `skill:` bindings remain reported rather than executed
(`tcw/work/hooks.py:53-60`), which is right here too: an archive that only
happens when an agent chooses to invoke a skill is not an archive. The
documentation must say that a guarantee belongs in a `command:`.

## Acceptance criteria

1. `work.lifecycle.auto-delete` with `pre` and `post` bindings passes
   `tcw validate`; an unknown id under it still fails, naming the offender.
2. `tcw work lifecycle` lists `auto-delete` with its `moves` string.
3. Completing an item under `retain: false` runs the `auto-delete` `pre`
   bindings, in declared order, before the item is deleted.
4. A `pre` binding that exits non-zero leaves the item present in its resolved
   folder, recorded in the graveyard, with the deletion commit not made; the
   command exits non-zero and its message names the failing binding.
5. Re-running `tcw work delete <slug>` after that failure runs the bindings again
   and, when they pass, completes the deletion.
6. A `pre` binding that moves the item folder away causes the deletion to succeed
   rather than error, and the second commit still records the removal.
7. `TCW_ITEM_PATH` equals what `tcw work path <slug>` printed for that item, and
   `TCW_RESOLUTION` is one of `WORK_RESOLUTIONS`, for both a `completed` and a
   `discarded` item.
8. Bindings carrying `when: {tags: [...]}` run only for matching items.
9. `post` bindings run after the deletion is committed, and a `post` failure
   exits non-zero without undoing it.
10. A `skill:` binding under `auto-delete` is reported and not executed.
11. Completing an item under `retain: true` runs no `auto-delete` bindings at all.
12. `tcw serve` completing an item runs no `auto-delete` bindings, as it runs none
    today.

## Risks

- **A `pre` hook that hangs holds a resolution open.** The existing binding
  timeout (`policy.timeout`) applies, and `run_bindings` already treats a timeout
  as a failure — which here means the item is kept. That is the safe direction,
  but a consumer whose upload is slow will see resolutions fail, and the
  documentation should say to raise the timeout rather than to remove the hook.
- **The item is deleted whether or not the archive was real.** A `pre` binding
  that exits 0 without uploading anything satisfies TCW completely. Nothing can
  check the consumer's storage, and the documentation must not imply otherwise.
- **`tcw serve` can resolve an item and cannot archive it.** Under `retain:
  false`, a web-driven resolution reaches the deletion with no hooks run. The
  requester has accepted that the web UI does not drive the lifecycle, so the
  honest resolution is that `serve` must not perform the deletion at all — it
  leaves the item in its resolved folder for a CLI `tcw work delete` to finish.
  Silently deleting without the archive would be the one genuinely destructive
  outcome available here, so this is not a documentation matter.
- **Two entry points, one contract.** The automatic step and `tcw work delete`
  must run the same bindings in the same order. Two code paths would drift; the
  spec's requirement is one path with two callers.

## Notes

The requester named `auto-discard` first and corrected it in the same
conversation once the `discard` collision was pointed out. Recorded because the
rejected name is the one someone will reach for again.

The two scenarios pull in slightly different directions and both are supported by
the same contract: S3 needs the artifact intact at a known path, and the folder
move needs permission to make it disappear. Criterion 6 is what keeps the second
from being a bug report later.
