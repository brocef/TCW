# Spec — Audit the backlog and upstream issues against the new lifecycle

Child **C8**, the epic's last. Deliberately short: C8 ships no behaviour, and a
spec that pre-decided the dispositions would violate its own premise — that each
one is verified against the tree before it is proposed.

## Capability changes

**None.** C8 changes tracked work state and GitHub issues; it adds, removes, and
alters no user-facing capability. Verified rather than assumed: the ledger
describes what a user can do with `tcw`, and discarding a work item exercises
`work/discard-a-work-item` rather than changing it.

The one adjacent question — whether any capability record is still falsified by
C1–C7 — was already swept at C7's spec stage, which found exactly one
(`work/configure-the-work-lifecycle`) and fixed it, plus two linkage gaps also
fixed. **C8 re-runs `tcw capabilities check` and `drift` but does not re-sweep**;
duplicating C7's sweep would find the same nothing.

## Problem

Seven children changed what TCW *is* between 2026-08-12 and 2026-08-18. Eleven
backlog items and one open GitHub issue were written against the model that
preceded them, and nobody has read them since. An item that describes a problem
the new model no longer has is worse than no item: it will be picked up, scoped,
and half-built before anyone notices.

The epic already demonstrated the failure mode it is guarding against. Its plan
named two items as likely discards; **both now read `completed`** — resolved by
other means while the epic ran. A disposition argued from the epic's forecast
rather than from the tree would have discarded two items that were already done.

## Goals

1. Every backlog item and every open issue has a disposition, and the disposition
   is argued from the working tree.
2. Nothing tracked changes before the requester approves.
3. The three defects C5–C7 deliberately carried forward are filed or explicitly
   declined — not lost.

## Non-goals

- **Fixing anything the audit finds.** A disposition may be "file a new item";
  building it is that item's job.
- **Re-sweeping the capability ledger.** C7 did it.
- **Auditing completed or discarded items.** Only what is open can be stale.
- **Re-litigating an item's merit.** The question is "does the new model change
  what this means", not "is this worth doing".
- Local LLM tooling.

## Design

**Three dispositions, plus a fourth that must be sayable.** The epic names
*moot* → discard, *rescoped* → edit in place, and *newly needed* → file. To those
C8 adds **unaffected** — the epic changed nothing about this item. Without it,
every item must be forced into a change, and eleven items being audited is not
eleven items being altered. Issue #12 is the clearest case.

**Verification is read-only and precedes the proposal.** Each item's claims are
checked against the working tree, using the `tcw:tcw-backlog-auditor` agent the
epic plan names, which reports and never edits or transitions.

**One approval pass** (requester's decision, amending the epic plan's
one-at-a-time): audit everything, present a single table — item, proposed
disposition, reason, and the child that caused it — then execute only what is
approved. A row the requester amends or vetoes is recorded as such.

**Discards name the child.** `tcw work discard --reason` naming which of C1–C7
removed the problem, so the archive says why rather than that someone decided so.
The same rule governs a closed issue: **close nothing without saying which child
resolved it** — an issue closed silently reads to the reporter as ignored.

## Acceptance criteria

1. **Every one of the eleven open backlog items** (excluding C8 itself) has a
   disposition in the presented table, and every disposition cites at least one
   file, command output, or completed child as its evidence.
2. **Open GitHub issue #12 has a disposition.** If it is "unaffected", that is
   stated in the table with the reason; it is not silently omitted.
3. **Nothing tracked changed before approval** — no `tcw work` transition, edit,
   or `gh` write occurs until the requester has answered.
4. **Every executed disposition matches an approved row**, and any row the
   requester amended or vetoed is recorded with what they chose instead.
5. **Each discard's reason names the child** that removed the problem. Each
   closed issue's comment does the same.
6. **The three carried-forward defects are each either filed as a new item or
   explicitly declined with a reason**: `read_artifact`'s presence divergence
   (`fs.py:3478` vs `2217-2221`), `README.md`'s unclosed `:605` heading, and
   `hooks.md`'s "configured-but-missing skill" note.
7. **The two already-completed candidates are recorded as such** rather than
   discarded, with the note that the epic plan's prediction was stale.
8. `tcw validate`, `tcw capabilities check`, and `tcw capabilities drift` are
   clean afterwards, and the full suite still passes.

## Risks

- **An audit that changes nothing looks like an audit that did not happen.**
  Mitigated by the *unaffected* disposition being explicit and evidenced: the
  table shows the item was read, not skipped.
- **A rescope is a spec edit made without the spec stage's rigour.** An item
  rescoped here gets its request or spec edited by an auditor who is not going to
  implement it. Bounded deliberately: a rescope may correct what an item *means*
  against the new model, and may not redesign it. Anything larger is a new item.
- **The requester approves eleven rows in one pass.** Batch approval trades
  per-item deliberation for throughput — their explicit choice. Mitigated by each
  row carrying its evidence, so a wrong row is visible rather than buried.
