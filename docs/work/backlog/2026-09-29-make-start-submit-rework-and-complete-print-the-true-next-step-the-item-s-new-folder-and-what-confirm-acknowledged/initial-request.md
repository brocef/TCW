# Make start, submit, rework and complete print the true next step, the item's new folder, and what --confirm acknowledged

## What is being asked for

The lines `tcw work` prints after it creates or moves an item are read by agents
as instructions, and several of them are wrong or incomplete. An agent that
follows them skips lifecycle stages; an agent holding a path from an earlier turn
has nothing telling it the folder moved; and nobody can tell from the output what
`complete --confirm` did with the Definition of Done. The user asked to start with
this item because a wrong hint misled the session that triaged it.

The request covers three reported problems, plus the creation hints the user
added when this stage asked:

1. **The next-step hints point at the wrong step** (GitHub #68).
   - After `tcw work start`, the hint says to run `tcw work complete` "when done &
     verified". That skips `submit` and the verify stage. An agent following it
     completes straight from `active`.
   - After `tcw work submit`, the hint says to "delete refined-outcome.md" to send
     the work back, but right after `submit` that file does not exist yet; it is
     written later, at acceptance. The hint reads as if one is already there.
2. **`complete --confirm` prints the Definition of Done as unticked boxes and then
   completes anyway** (GitHub #67). Three agents could not tell whether `--confirm`
   acknowledged the items, assumed them, or ignored them. The same unticked list is
   also printed before `complete` refuses for an unrelated reason (for example
   `--already-integrated` on an item with no worktree), which makes the list look
   like the reason for the refusal. Asked for: when `--confirm` is given, show the
   items as acknowledged and say `--confirm` did it; and print the checklist only on
   the path that actually completes.
3. **`submit` and `rework` report a status, not the item's new folder** (GitHub #58,
   point 1). `new`, `start` and `complete` print the path the item now lives at;
   `submit` and `rework` print only `→ review` / `→ active`. These are exactly the two
   transitions after which a stage writes an artifact into the folder that just
   moved (`verify` after `submit`, `implement` after `rework`), so the correct path
   is missing precisely where it is needed.
4. **The hints after creating an item skip the planning stages** (added by the user
   at this stage). `tcw work new` says "when you begin implementing, run
   `tcw work start`", which jumps over `request`, `spec` and `plan`. This is the
   hint that misled the triage session. `tcw work inbox accept` creates items too
   and should be brought in line with whatever `new` ends up saying.

The outcome wanted: every next-step hint `tcw work` prints after creating or moving
an item points at the actual next step of the lifecycle, the transitions that move
a folder all say where it went, and the Definition of Done output says truthfully
what happened to it.

## Constraints

- The hints are guidance printed to standard error; the transitions' behavior
  (what they refuse, what they commit) is not being changed here, except that the
  Definition of Done list must no longer be printed on a path that then refuses.
- Whatever the hints say must hold under a project's own lifecycle configuration,
  not only TCW's defaults — a project can bind different stages and gates.

## Out of scope

- The rest of GitHub #58 — `complete` checking for the verify artifact, `validate`
  finding a slug under two statuses, and the stage text about where to write. That
  is the item `2026-09-29-make-a-stale-item-path-fail-loudly-complete-checks-for-the-verify-artifact-validate-finds-a-slug-under-two-statuses-and`.
- A folder that never moves when an item changes status (suggested in a comment on
  #58), which is also recorded on that item.
- Closing the originating GitHub issues. By this repository's rule they are
  answered and closed only after the version carrying the fix is published.

## Notes

- Reference material: asked; none provided.
- Scope was confirmed by the user at this stage: all three issues stay together
  because they change the same few printed lines and their tests, and the creation
  hints are included.
- For the spec: `inbox accept` currently prints no next-step hint at all (only
  `→ now at <path>`), so "in line with `new`" may mean adding one.

## References

- GitHub [#68](https://github.com/brocef/TCW/issues/68) — the wrong next-step hints after `start` and `submit`.
- GitHub [#67](https://github.com/brocef/TCW/issues/67) — the unticked Definition of Done list.
- GitHub [#58](https://github.com/brocef/TCW/issues/58) — point 1 only, the missing folder after `submit` and `rework`.
- `intake.md` in this folder — the three reports quoted word for word.
