# Coordination plan: separate claim from status movement in the tracker verbs

This epic implements nothing itself. Its tasks create the four children the spec
bounds, record their order as blockers, and define the checkpoints at which the
rollup is read.

## Task 1 — Open C1, the ownership primitive

```sh
tcw work new "Make claim and release assert ownership without moving a ticket" \
  --initiative 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs \
  --tags work,cli --effort high --priority 4
```

Creates `docs/work/backlog/<C1-slug>/state.yaml`. Its brief is the spec's **C1**
section, which the child's own `request` stage expands: the two verbs, ownership
as one fact across the item's owner and the ticket's assignee, idempotence for
the holder, refusal of a second holder, read-after-write with the optional
transition assertion, and the removal of `claim: owed | done` from the sync
record.

*Proves:* `tcw work show <C1-slug>` reports it in `backlog` with
`initiative: 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`.

## Task 2 — Open C2 and C3, both blocked by C1

```sh
tcw work new "Let sync move a ticket either way to match its work item" \
  --initiative 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs \
  --tags work,cli --effort medium --priority 3
tcw work edit <C2-slug> --blocked-by <C1-slug>

tcw work new "Retire the claim transition key into a named start transition" \
  --initiative 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs \
  --tags work,cli --effort medium --priority 3
tcw work edit <C3-slug> --blocked-by <C1-slug>
```

C2 and C3 are genuinely parallel and must **not** be chained to each other — the
spec's ordering diagram is the authority, and a false blocker is a lie the tool
enforces.

**Amended after C1's spec review: C3's blocker on C1 was itself false, and has
been removed.** C3's premise is that the claim no longer transitions, and that
becomes true at C4, not at C1 — C1 edits no delivery code. The `--blocked-by`
recorded for C3 by this task is therefore dropped:

```sh
tcw work edit 2026-09-16-retire-the-claim-transition-key-into-a-named-start-transition \
  --unblock 2026-09-16-make-claim-and-release-assert-ownership-without-moving-a-ticket
```

C3 is workable now, alongside C1.

*Proves:* `tcw work list` shows C2 gated and C3 workable; `tcw work start
<C2-slug>` refuses while C1 is open, and `tcw work start <C3-slug>` does not.

## Task 3 — Open C4, blocked by C2 and C3

```sh
tcw work new "Compose the lifecycle moves from claim and sync" \
  --initiative 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs \
  --tags work,cli --effort high --priority 3
tcw work edit <C4-slug> --blocked-by <C2-slug> --blocked-by <C3-slug>
```

*Proves:* `tcw work reconcile <epic>` names only C1 under **Next**.

## Task 4 — Start the epic

```sh
tcw work start 2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs
```

An initiative child cannot start while its epic is not active, so this precedes
any child work. Runs before Task 5 and after Tasks 1–3, so the board is complete
when the gate opens.

*Proves:* the epic reads `active`; `tcw work start <C1-slug>` is accepted.

## Task 5 — Rollup checkpoints

`tcw work reconcile <epic>` is run before each coordination decision, after any
child changes status, and before closeout. It writes `rollup.md`; nothing is
hand-edited into it.

Three checkpoints earn a decision rather than a read:

1. **After C1 completes** — confirm read-after-write behaves as the spec's
   criteria 1–4 require *before* C2 builds on it. (C3 no longer waits on C1; the
   checkpoint is about C2.) If the race window proves
   wider than the spec claims, C1 is reworked rather than C2 and C3 absorbing it.
2. **After C2 and C3 both complete** — whichever order they land in, since they
   are now independent of each other *and* of C1 in C3's case — confirm criteria
   8 and 10, and confirm the
   `--part` hold (criterion 9) survived C2, which risk 3 names as the likeliest
   thing to break silently.
3. **Before closeout** — the full criteria list, run against the merged tree.

## Task 6 — Closeout, and the six subsumed problems

The requester's decision is that the six stay open as independent evidence and
are closed as delivery proves them gone. At closeout, and **in this order**:

1. `tcw work reconcile <epic> --complete-when-ready`.
2. Check each subsumed problem against the delivered behaviour and resolve the
   TCW items: the two review findings now carried by this epic's request, and
   `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`,
   which this epic makes optional rather than answers — it is resolved only if
   the optional transition assertion in C1 covers what it was parked on, and
   otherwise stays open with a note saying so.
3. **GitHub #41 and #42 are answered and closed only after the version carrying
   this work is cut and pushed.** `CLAUDE.md` requires that order — an issue
   closed before the fix ships tells the reporter it is fixed when they cannot
   install it — and nothing is posted to an issue without the exact text being
   approved first. Record the deferral in `refined-outcome.md`.

## Documentation Sync

Evaluated for the epic itself, which changes no code and so fires none of the
triggers directly. Every entry below fires in a **child**, and each child carries
its own Documentation Sync block; this is the map, so nothing is written twice or
missed between them.

| Entry | Trigger | Fires in |
| ----- | ------- | -------- |
| `docs/guide/jira.md` | Tracker-Change | **All four.** C1 rewrites "Taking a ticket"; C2 reverses "It never follows Jira and never pulls a ticket back"; C3 rewrites the `transitions` table and the inheritance note; C4 rewrites what each lifecycle move does to a bound ticket |
| `README.md` | Public-API | C1 (two new verbs on the public CLI surface) and C4 (`--sync-status` removed) |
| `skills/work/SKILL.md` and its references | Skill-Driven-Component | **All four** — the CLI surface, the claim's meaning and the lifecycle moves' effects all change |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | **C1 and C3.** C3 removes `transitions.claim` and adds `transitions.start`; C1 adds `work.tracker.exclusive-claim-transition`, the opt-in exclusivity assertion. **Amended** — this table said C3 only, which was written before C1's spec placed the optional assertion behind a key of its own |
| `docs/release-notes/upcoming.md` | Public-API | All four, each appending its own user-facing entry |
| `docs/changelogs/upcoming.md` | Any-Code-Change | All four |

The **version cut is one cut for the whole epic**, not one per child:
`CLAUDE.md` asks for the cut to be batched across a run of items, and Task 6
depends on it having happened.

## Verification

What the suite cannot check, and what has to be done by hand:

- **The race that criterion 3 describes.** Two accounts claiming concurrently
  cannot be driven from the test suite against real Jira. The fake tracker can
  interleave the read and the write deterministically, which proves the logic;
  it does not prove Jira's consistency behaves as assumed. C1 must state that
  distinction in its own Verification rather than let a green fake stand in for
  it.
- **Criteria 5, 6, 7 and 8 against a real Jira project.** The originating issues
  were all found in real use and not by the suite. One throwaway ticket walked
  through the whole lifecycle is what proves them; the fake tracker proves the
  code paths.
- **Whether "the item is truth" is tolerable in practice** (risk 2). No test can
  answer whether silently reversing a deliberate manual move is acceptable. This
  is a question for the requester at the epic's `verify` stage, and the answer
  may send C2 back.
- **That no child left `deliver` in a state the catch-up-walk item cannot rebase
  onto** (risk 6). Checked by reading, at checkpoint 3.

## Notes

- **Do not use this epic as the place to make a child's code changes.** Its
  `implement` stage is coordination: dispatch, reconcile, answer blockers,
  adjust this plan.
- Child slugs are written as `<C1-slug>` and so on because `tcw work new` assigns
  them; substitute the printed slug when running Task 2 and Task 3, and do not
  guess them ahead of time.
- The blockers in Tasks 2 and 3 encode the spec's ordering diagram exactly. If a
  child's own planning finds the order wrong, the spec is what changes first.
