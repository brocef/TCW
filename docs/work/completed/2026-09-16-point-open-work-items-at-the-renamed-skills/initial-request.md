# Point open work items at the renamed skills

## Request

No open work item should tell whoever picks it up to edit, read or declare
something under an old `tcw-…` skill or capability name. Pull request #46 dropped
the `tcw-` prefix from every shipped skill and agent, and deliberately left
`docs/work/` alone on the grounds that those documents record what things were
called when they were written. That reasoning holds for finished items. It does
not hold for open ones, where the old name is an instruction to follow rather
than a record of what happened.

Two kinds of stale name are in scope, and the requester confirmed the second
belongs here rather than in its own item:

1. **Prose that instructs.** A file that names a path to edit or a document to
   read — `skills/tcw-work/references/commands.md`,
   `skills/tcw-configure/<document>.md` — sends the reader to a path that is no
   longer there. Rewrite it. A name quoted as a record of what was done at the
   time is left alone.

2. **Capability paths in `capabilities.yaml` sidecars.** An open item declaring
   `skills/tcw-work` under `changed:` names a capability whose path is now
   `skills/work`. This is not only stale prose: the Definition-of-Done capability
   gate resolves those paths when the item completes, so the item fails at
   completion — after the work is done — rather than when the declaration was
   written.

**Deciding per file is the work.** There is no mechanical rule that separates an
instruction from a record; each of the files has to be read and judged. Matching
must be on whole names only, so `tcw-config` and `tcw-cli` are never touched.

## Notes

- **Out of scope, by the requester's decision:** a guard that stops this
  recurring. Extending the removed-names test to cover open work items was
  offered and declined, so the next rename repeats the problem unless something
  else is done about it. Worth knowing that this is a conscious choice rather
  than an oversight.
- Reference material was not separately solicited; the intake names its own
  sources and the requester's input was taken on scope instead.
- The intake's count of 22 files was re-run at `632f023` and gives 23 across
  `docs/work/backlog` and `docs/work/inbox`, one of which is the inbox entry that
  became this item. The count will move again as items are opened and closed, so
  it is context rather than an acceptance criterion.

## References

- `docs/work/backlog/2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root/intake.md`
  — the confirmed instance of kind 2: it says to declare `skills/tcw-work` under
  `changed:`, which would fail the capability gate at completion.
- `docs/work/backlog/2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title/plan.md`
  and `…/2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes/plan.md`
  — two confirmed instances of kind 1, both naming files to edit under old paths.
  Both items are already specced and planned, so they are the likeliest to be
  picked up before a sweep happens.
- The grep in the intake — the starting roster, and the whole-name matching rule
  it encodes is the rule this item has to keep.
- `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
  (completed; pull request #46) — its spec records the decision to leave
  `docs/work/` alone, which is what this item revisits for open items only.
- `tests/test_skill_lifecycle_parity.py` — holds the removed-names guard and its
  whole-name matcher; the source of the matching rule even though extending it is
  out of scope here.
