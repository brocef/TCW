# Plan — Audit the backlog and upstream issues against the new lifecycle

Four tasks. Only task 3 changes tracked state, and it does not start until the
requester has answered task 2.

## Ordering

There is one hard boundary: **nothing tracked changes before approval**
(criterion 3). Tasks 1 and 2 are read-only; task 3 executes; task 4 records.
Everything else about the order follows from that.

## Tasks

### 1. Audit every item and the one issue — read-only

Eleven backlog items (the twelve listed, minus C8 itself) and GitHub issue #12
on `brocef/TCW`.

**Per item**, dispatched to the `tcw:tcw-backlog-auditor` agent the epic plan
names — it reports and never edits, transitions, or tags:

- Read the item's request and any spec.
- Check its claims against the **working tree**, not against the epic's forecast.
  The forecast is known stale: it named two items as likely discards that now
  read `completed`.
- Return one of four dispositions with evidence — a file, a command's output, or
  the completed child that changed the ground:
  **moot** (discard), **rescoped** (edit in place), **newly needed** (file), or
  **unaffected** (the epic changed nothing about it).

**The three known rescope candidates** are verified rather than assumed:
`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` (C6 and
C7 moved the thing under evaluation from skill prose to the CLI's prompts), and
`2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge` plus
the three `remote/*` items (which now inherit C1's abstract intake surface and
C2's versioned DTO).

**Issue #12** — "tcw serve renders self-qualified `tcw://` links as inert" —
concerns `_hosted_projects()` omitting the anchor's own project id. The expected
answer is *unaffected*; the task is to confirm that against the code rather than
assume it from the title.

**The three carried-forward defects** get a proposed disposition too, since
criterion 6 requires each to be filed or declined: `read_artifact`'s
`p.is_file()` (`fs.py:3478`) versus the canonical presence rule
(`fs.py:2217-2221`); `README.md`'s heading at `:605` with no closing boundary;
and `hooks.md`'s "configured-but-missing skill" note, which wants a CLI change.

— criteria 1, 2, 6, 7

### 2. Present one table; stop

Item / issue · proposed disposition · reason · the child that caused it · the
evidence checked. Then **stop and wait.** No `tcw work` transition, no edit, no
`gh` write until the requester answers.

This is the task that discharges criterion 3, and it discharges it by not doing
anything.

— criterion 3

### 3. Execute exactly what was approved

Only after the answer. Per approved row:

- **moot** → `tcw work discard <slug> --reason "<why>, resolved by <child>"`.
  The reason names the child; an archive that says only "discarded" is why this
  rule exists.
- **rescoped** → edit the item's `initial-request.md` (or `spec.md`) in place,
  committed per item. **Bounded**: correct what the item *means* against the new
  model; do not redesign it. Anything larger is a new item.
- **newly needed** → `tcw work new` with the tags the item warrants.
- **unaffected** → nothing.
- **issue** → `gh issue comment` naming the child, then `gh issue close` if the
  approved disposition is to close. Never close without the comment.

A row the requester amended or vetoed is executed as they chose, and what they
chose is recorded in `outcome.md`.

— criteria 4, 5

### 4. Whole-tree checks

`tcw validate`, `tcw capabilities check`, `tcw capabilities drift`, `pytest -q`.
Recorded in `outcome.md`. C7's capability sweep is **not** repeated — it found
one falsified record and two linkage gaps and fixed all three.

— criterion 8

## Documentation Sync

**Evaluated; nothing fires.** Stated rather than skipped, because a Documentation
Sync section that is silently ignored is indistinguishable from one nobody read.

- `README.md` [Public-API] — no CLI surface or user-facing behaviour changes.
- `docs/release-notes/upcoming.md` [Public-API] — nothing user-visible.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — **no code changes at all.**
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — no component changes.

C8 uses the `tcw-audit-work-backlog` skill; it does not modify it.

## Verification

What no check covers:

- **Whether a disposition is right.** The evidence makes it *reviewable*, not
  correct. This is why the requester approves the table rather than being told
  what happened, and it is the whole of C8's correctness — the epic gives it no
  acceptance criterion of its own.
- **Whether a rescope stayed inside its bound.** "Correct what it means, do not
  redesign it" is a judgment. The per-item commits make each one readable on its
  own, which is the only real guard.
- **Whether the audit missed a stale item.** It covers what is in `backlog`. An
  item in `blocked`, or one whose staleness has nothing to do with this epic, is
  out of scope by design and would need a general backlog audit instead.

## Notes

- **The epic plan's one-item-at-a-time rule is amended** to a single approval
  pass, at the requester's direction. Recorded here because the epic plan is the
  document it contradicts.
- **The audit's scope is smaller than the epic predicted**: eleven items and one
  issue, with both named discard candidates already completed. That is the epic
  overestimating its own disruption, in the safe direction.
