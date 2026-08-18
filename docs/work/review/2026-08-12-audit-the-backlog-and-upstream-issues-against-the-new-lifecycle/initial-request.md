# Audit the backlog and upstream issues against the new lifecycle

Child **C8** of `2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`,
and the last one. C1–C7 are complete.

## Product changes

None. C8 ships no behaviour and has no acceptance criterion in the epic — its
correctness is the requester approving each disposition.

## Technical changes

None. C8 changes **tracked state**, not code: work items discarded, rescoped, or
newly filed, and GitHub issues commented, closed, edited, or opened.

## Meta changes

A design change this size invalidates work items in three ways, and each needs a
different action:

- **Made moot** — the item describes a problem the new model no longer has →
  `tcw work discard`, with the reason naming the child that removed it.
- **Rescoped** — the item still names a real gap, but against the old surface →
  edit the request or spec in place.
- **Newly possible or newly needed** — a gap this epic opened rather than closed
  → file as a new item rather than smuggling it into a closeout.

Open GitHub issues get the same three-way treatment. **Close nothing without
saying which child resolved it** — an issue closed silently reads to the reporter
as ignored.

## What is actually in scope

Established before writing this request, because the epic's plan predicted a
larger job than exists:

- **Eleven backlog items**, excluding C8 itself.
- **One open GitHub issue** on `brocef/TCW`: **#12**, "tcw serve renders
  self-qualified `tcw://` links as inert". Opened 2026-08-12. It concerns
  `_hosted_projects()` omitting the anchor's own project id — **nothing this epic
  touched**. The expected disposition is "unaffected, leave open", and saying so
  explicitly is the point of auditing it.

**Two of the epic plan's named candidates are already resolved.** It flagged
`2026-08-12-teach-the-remaining-readers-to-tell-a-vanished-item-from-an-absent-one`
and `2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`
as likely discards; both now read `completed`. The plan's prediction is stale,
which is itself worth recording — it is the epic predicting its own effect on the
backlog and getting it wrong in the safe direction.

## Constraints

1. **Batch the recommendations; the requester approves in one pass.** The epic
   plan says "one item at a time, with the requester approving each action". That
   is amended: audit every item and issue, then present **one table** of proposed
   dispositions — the disposition, the reason, and the child that caused it — for
   approval, amendment, or veto per row in a single exchange. Nothing tracked
   changes before that approval.

2. **Verification is read-only and per item.** Each item's claims are checked
   against the working tree before a disposition is proposed. A disposition
   argued from the epic's *predictions* rather than from what shipped is the
   failure mode this child exists to avoid — the two stale candidates above are
   the proof it is a real risk.

3. **Three known rescope candidates**, from the epic plan, to be verified rather
   than assumed:
   - `2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` —
     after C6 and C7 the thing under evaluation is largely the CLI's built-in
     prompts, not skill prose.
   - `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`
     and the three `remote/*` items — these now inherit an abstract intake
     surface (C1) and a versioned DTO (C2) they were written without.

4. **Three carried-forward defects must be filed or explicitly declined.** Each
   was found during C5–C7 and deliberately left:
   - `read_artifact`'s `p.is_file()` (`tcw/store/fs.py:3478`) disagrees with the
     canonical presence rule (`fs.py:2217-2221`) — C5's refined outcome.
   - `README.md`'s heading at `:605` has no closing boundary, so everything to
     `:1017` renders inside "Binding your own skills and commands to the
     lifecycle" — C7's refined outcome.
   - `hooks.md`'s "configured-but-missing skill cannot fail closed under Codex"
     note would be better said by `tcw work lifecycle` beside a reported `skill:`
     binding, but that is a CLI change with a capability delta — C7's spec §7.

5. **No local LLM tooling** (`bllm-*`) for any part of this item.

## References

- The epic's `plan.md` §"C8 — Backlog and upstream-issue audit" — the three-way
  treatment and the original candidate list.
- The `tcw-audit-work-backlog` skill and the `tcw:tcw-backlog-auditor` agent,
  which the epic plan names as the mechanism: read-only per-item verification.
- The seven completed children's `outcome.md` and `refined-outcome.md` under
  `docs/work/completed/` — what actually shipped, as against what the epic
  predicted.

## Notes

- The audit is a real work item rather than a closeout checklist because it
  changes tracked state and the requester approves each action.
- C8 is the epic's last child; the epic cannot complete while it is open.
