# Accepted

The user accepted the work at the verify stage and chose the closeout route in
the same message: "Approved, merge to main locally and close out the work item."

## What was accepted

The thirteen commits listed in `outcome.md`, plus the six written during this
stage: two tests closing gaps the assessment found (`c1524505`), one behaviour
fix with its test (`18e4a605`), its changelog line (`267178a7`), and three
document corrections (`5a174843`, `1d23e153`, `695797ad`).

All sixteen acceptance criteria are met. Five needed work at this stage to get
there, and the distinction matters:

- **3, 12 and 13 were code-correct but unverified.** Each was proved so by
  breaking the code and watching the suite stay green: the claim verb could stop
  reading `work.tracker.exclusive-claim-transition` entirely (105 tests still
  passed), the branch handling a workflow *refusing* the configured transition
  was never executed by any test, and the claim side had no equivalent of the
  release side's ordering test — this item's own mutation table had credited the
  release test for both. Two tests in `tests/test_tracker_hold.py` now kill all
  three mutations.
- **4 and 16 are met in substance, and their wording is wrong.** Criterion 4
  specifies a `PUT /assignee` hook where the test correctly uses a `GET` hook,
  which is the only one that produces the interleaving the criterion describes.
  Criterion 16 promises four named suites pass *unchanged*; they pass, but one of
  them carries the same one-line rename the rest of the change does. Both are
  recorded in `outcome.md` rather than quietly restated.

## What this stage found, beyond the criteria

One live defect, now fixed. `assert_ownership`'s read-back had two branches for
three possible answers. A ticket assigned to the caller and then unassigned
before the read-back fell into the lost-race branch, which reported it as "held
by somebody else… they took it while this claim was in flight" — naming a holder
that does not exist, and telling the caller to wait for somebody to let go of
something nobody holds. It now says the ticket was unassigned mid-claim and that
re-running will take it.

Four further spec defects, all recorded in `outcome.md` and two of them
corrected in `spec.md` itself. The most substantive: **Design step 7 describes a
state the code never reaches.** It says a lost race may leave the ticket assigned
to the caller with the item unowned, and that the message must say so. On the
lost-race path the read-back has already found another account, so the ticket
belongs to the winner and the shipped wording is right. The state step 7
describes is real but belongs to two other paths — a failed read-back and a
failed local write — each of which already has its own message.

## Definition of Done

- **tests pass** — `pytest` over the whole suite from the worktree: **3718
  passed, 0 failed** through `6a65bcd1`. The six commits written at this stage
  are covered by a full run on the merged `main`, with the editable install
  restored to the primary checkout: **3739 passed, 0 failed** (17m11s), plus
  `tcw validate` clean. The count differs from the branch run because `main` had
  advanced by two commits, and because this stage added three tests.
- **docs synced** — `docs/guide/jira.md` (a new "Holding and releasing a ticket"
  section, the configuration block and the key table), `README.md` (the tracker
  row and a new example), `skills/work/references/commands.md`,
  `skills/configure/references/tracker.md`, `docs/release-notes/upcoming.md` and
  `docs/changelogs/upcoming.md`. Four triggers fired: `Public-CLI-API`,
  `Tracker-Change`, `Any-Code-Change` and `Configuration-Key-Change`.
- **capabilities reconciled** — `work/hold-a-tracker-ticket` (`cap-2778c5`)
  flipped `Missing` → `Supported`. It is the item's only declared delta, and
  `tcw capabilities check` passes.
- **reviewed** — the spec by the adversarial spec reviewer, whose finding that
  the `owed` replacement rule was factually wrong caused the item to be rescoped
  before implementation; the implementation by the adversarial code reviewer,
  which found the local-ownership hole now closed by `_held_by_someone_else`; and
  the finished change by the `tcw-verifier` agent at this stage, whose three
  mutation findings I reproduced myself before acting on them. Neither Codex nor
  `bllm` was run, so this was not a full multi review.
- **version offered** — the version stays where it is. `CLAUDE.md` asks for the
  cut to be batched across a run of items rather than taken one per item, and
  this is the first of four children in its epic. The entries are already in
  `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` for whoever
  cuts it after C4.
- **originating GitHub issue answered and closed** — not applicable. The item
  came from the epic `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`,
  not from an issue, and carries no tracker binding.

## Closeout route

Merged into `main` in the primary checkout locally, as instructed. Not pushed,
and no version cut. The editable install was restored to the primary checkout
before completing, so no worktree path is left registered.

## Deliberately left for someone else

- **The `claim: owed | done` removal moved to C2**, on the requester's decision
  at the spec stage. `deliver`'s `finish` and `record_unsent` both write
  `"claim": "owed"` without writing `catch-up`, so the rule this item was going
  to rely on was false. Recorded in both this item's spec and the epic's.
- **An active item with no holder is a state this item creates**, and C4's rule
  that a claim gates work has to answer for it. Already noted in the epic's spec.
- **Criteria 4 and 16 keep their imprecise wording.** They are met, the
  imprecision is written down, and rewriting frozen acceptance criteria after
  they have been judged would make the record less honest rather than more.
