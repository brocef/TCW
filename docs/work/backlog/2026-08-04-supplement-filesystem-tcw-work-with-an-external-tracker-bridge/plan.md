# Plan — Supplement filesystem TCW work with an external tracker bridge

An epic's plan is a **coordination plan**. It creates no code. Its tasks set up
the shared prerequisites, create the five children with their ordering recorded
as blockers, and define the checkpoints at which the initiative is re-read.
Every code task lives in a child's own `plan.md`.

Run every command from the primary checkout, not from a worktree.

## Task 1 — Register the shared taxonomy Feature

All four planned capabilities name one Feature, and `tcw capabilities set`
refuses a `Feature` reference that does not resolve, so the Feature has to exist
before any of them is written. It is a shared prerequisite, which is why it is
here and not in C1.

```sh
tcw taxonomy add "External work tracker" \
  "The coordination boundary between a project's TCW work store and an external tracker that owns ticket existence, assignment and claim state." \
  --kind feature --vocab work-item --vocab cli --vocab reference
```

Creates: one Feature entry in the taxonomy store (`tcw taxonomy path` resolves
where).

Proves it: `tcw taxonomy show external-work-tracker` prints `kind: Feature` with
all three vocabulary refs, and `tcw taxonomy check` exits zero.

## Task 2 — Start the epic

An initiative child cannot start until its epic is active
(`tcw/store/base.py:2683`), so this precedes every child's work, not just its
creation.

```sh
tcw work start 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge
```

Proves it: `tcw work list --status active` names the epic.

## Task 3 — Create C1 and C2, the first delivery

```sh
tcw work new "Configure an external tracker and read its tickets" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 70 --tags remote,work,cli

tcw work new "Claim an external tracker ticket and bind it to a work item" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 70 --tags remote,work,cli
```

Then record the order. `--initiative` carries no dependency relation, so without
this both read as workable at once:

```sh
tcw work edit <C2-slug> --blocked-by <C1-slug>
```

Creates: two work item folders, each holding only `state.yaml` until its own
`request` stage runs.

Proves it: `tcw work list` shows both with `initiative` pointing at this epic,
and `tcw work start <C2-slug>` refuses while C1 is open.

## Task 4 — Create C3, C4 and C5

Created now rather than later so the whole shape is visible on the board and the
blockers are recorded once.

```sh
tcw work new "Synchronize the work lifecycle outward to the tracker" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 45 --tags remote,work,cli

tcw work new "Refuse local work that no claimed tracker ticket authorizes" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 40 --tags remote,work,cli

tcw work new "Surface an item's tracker binding in the board, the projection and the web app" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 40 --tags remote,work,cli,web
```

```sh
tcw work edit <C3-slug> --blocked-by <C2-slug>
tcw work edit <C4-slug> --blocked-by <C3-slug>
tcw work edit <C5-slug> --blocked-by <C2-slug>
```

C5 is blocked by C2 **only**. It does not depend on C3 or C4, and chaining it to
them would be a false blocker the tool then enforces.

Proves it: `tcw work reconcile <epic>` lists five children, and its **Next**
section names C1 alone.

## Task 5 — Seed each child's capability at its own planning

Not a single step — it happens inside each child's `plan` stage, and it is listed
here so no child forgets it. For each child, when that child is planned:

```sh
tcw capabilities add <path> "<Name>" --status Missing
tcw capabilities set <path> --field "Planning doc=<child-slug>"
tcw capabilities set <path> --field "Feature=external-work-tracker"
tcw capabilities set <path> --field "Subject=work-item,cli,reference"
```

| Child | Capability path | Name |
| ----- | --------------- | ---- |
| C1 | `work/inspect-external-tracker-work` | Inspect external tracker work |
| C2 | `work/manage-external-tracker-intake` | Manage external tracker intake |
| C3 | `work/synchronize-external-tracker-work` | Synchronize external tracker work |
| C4 | `work/require-tracker-backed-work` | Require tracker-backed work |

C5 changes two existing capabilities rather than adding one, so it records
`work/read-a-work-item` and `work/open-a-work-item` under `changed:` in its own
`capabilities.yaml` instead.

Proves it: `tcw capabilities check` exits zero after each, and
`tcw capabilities drift` reports nothing new.

## Task 6 — Write the epic's own `capabilities.yaml`

After task 5 has seeded all four, write the epic's sidecar listing them. This is
the mechanical enforcement of acceptance criterion 12: the completion gate blocks
`complete` while any `new:` path still reads `Missing` or fails to resolve, so
the epic cannot close over a ledger that still describes the old world.

```yaml
new:
    - work/inspect-external-tracker-work
    - work/manage-external-tracker-intake
    - work/synchronize-external-tracker-work
    - work/require-tracker-backed-work
```

Modifies: the epic item's `capabilities.yaml` sidecar.

Proves it: with the four capabilities still `Missing`, `tcw work complete <epic>
--resolution done` is refused and the refusal names them. Check this
deliberately rather than assuming it — the criterion is worthless if the gate
does not actually fire.

## Task 7 — Confirm the claim assumption before C2 freezes its design

The single-winner guarantee rests on Jira Cloud serializing simultaneous
transitions on one issue and reporting the loser as a conflict. The spec records
this as an unverified assumption. Confirm it against a live Jira Cloud instance —
two concurrent transition requests on one issue, both observed — and write the
observed behavior into C2's spec. If it does not hold, C2's spec returns to its
`spec` stage and the claim boundary is redesigned; the initiative does not
proceed on the assumption.

Proves it: C2's spec quotes the observed responses, with dates.

## Task 8 — Rollup checkpoints

`tcw work reconcile <epic>` before every coordination decision, after any child
status change, and before closeout. Specifically:

1. After C1 completes — confirm C2 now reads as workable and nothing else does.
2. After C2 completes — the first delivery is done. Re-read C3, C4 and C5 against
   what C1 and C2 actually built, and revise their requests before they are
   specced. Two of the three were scoped from a request written in August 2026
   and may be wrong by then.
3. After C5 completes — C5 is the only child that can complete out of order, so
   check the board rather than assuming.
4. Before closeout — every child resolved, then reconcile a final time.

## Task 9 — Re-check acceptance criterion 1 at every child's completion

Criterion 1 says a project with no tracker configured behaves exactly as it does
today, and no single child's suite can prove it stayed true after the next child
landed. At each child's `verify` stage, run the full suite with no tracker
configuration present and confirm no existing test was edited to accommodate the
bridge.

```sh
python -m pytest -q
git diff --stat <child-branch-point>..HEAD -- tests/
```

The second command is the check that matters: an edited existing test is how this
criterion gets quietly dropped.

## Documentation Sync

**No trigger fires on the epic's own diff.** The epic writes no code, no CLI
surface and no user-facing behavior; its commits are artifacts and status moves.
Each child carries its own Documentation Sync block, and the table below is what
this plan expects each to schedule, so a missing entry at a child's plan stage is
visible as a gap rather than an omission nobody noticed.

| Entry | Trigger | C1 | C2 | C3 | C4 | C5 |
| ----- | ------- | -- | -- | -- | -- | -- |
| `README.md` | Public-API | yes — configuration and two read commands | yes — import, link, unlink | yes — sync | yes — strict mode | yes — the new board and `--json` fields |
| `docs/release-notes/upcoming.md` | Public-API | yes | yes | yes | yes | yes |
| `docs/changelogs/upcoming.md` | Any-Code-Change | yes | yes | yes | yes | yes |
| `skills/tcw-work/SKILL.md` | Skill-Driven-Component | yes — a gated reference for the tracker commands | yes | yes | yes | yes |

One judgment recorded here rather than five times: the skill entry says to update
the driving skill whenever the component's CLI surface, model, lifecycle or
guardrails change, and every child changes at least one of those. So the answer
is `yes` in every cell, and a child proposing otherwise has to argue for it.

The version cut is **not** per child. Batch it across the run, as the repository
guide requires, and cut it when the first delivery (C1 and C2) is publishable.

## Verification

What the test suite cannot settle, and who settles it.

1. **That Jira Cloud behaves as the claim design assumes.** Task 7. No mocked
   test can prove this; only a live instance can.
2. **That two real clones cannot both claim one ticket.** The suite can prove
   two concurrent processes cannot. Two developers on two machines against one
   Jira project is a manual check, run once at C2's verification.
3. **That no secret leaks.** Acceptance criterion 8 describes a greppable check
   with a sentinel token, which the suite *can* run. What it cannot check is a
   secret reaching a Jira comment or a log this repository does not own. Read
   the outbound payload construction by hand at C3's verification.
4. **That a non-developer can actually file a request.** Goal 2 is about a
   person, not a code path. One real ticket filed by someone without a checkout,
   imported end to end, at C2's verification.
5. **That the epic's completion gate fires.** Task 6, checked deliberately.

## Notes

**The first delivery is C1 and C2.** C3, C4 and C5 are specified far enough to be
ordered and no further. Do not treat their boundaries in the epic spec as their
specs; each still runs its own `spec` stage, and checkpoint 2 in task 8 exists
because those boundaries were derived from a request written before any of this
was built.

**Child slugs are written as `<C1-slug>` and so on** because `tcw work new`
mints the date-prefixed slug and printing it is how it is learned. Substitute the
printed slugs when the commands are run; do not guess them.
