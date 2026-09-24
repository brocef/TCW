# Refined outcome — give a recordless sync a move, and let strict mode work without `transitions.start`

## Decision

**Accepted** by the requester on 2026-09-24, on the condition that the full suite
was green after the changes decided at verify. It was: see Evidence.

## What verify changed

Two read-only reviews were run: the TCW verifier against the 36 criteria, and an
adversarial review of the combined diff. Each finding was checked against the code
before anything was acted on.

**Fixed at verify: findings that belonged to this change** (`5aba0717`, docs `8a12d558`)

1. **Blocking, confirmed by reproduction.** A strict `tcw work tracker claim
   --take-over` on a workflow that offers the claim transition from
   `statuses.active` applied the transition, assigned the holder's ticket to the
   caller, and only then refused. The item was left still owned by the holder. The
   same shape, minus taking anyone's ticket, applied to an unassigned ticket there
   under `start`. The verdict was knowable from the ticket as read, so
   `_unclaimable_on_active` now refuses before anything is sent, for `start` and
   `tracker claim` alike.
2. **Significant.** With `off_active_refuses=False`, `claim_refusal` skipped the
   question even when the claim had just applied a transition that landed off
   `statuses.active`. It now asks at the status the transition landed on.
3. **Goal 9.** The not-exclusive refusals now name a next step
   (`not_exclusive_advice`).
4. **Wording that said more than the code does** (criteria 31 and 32, flagged by the
   verifier). The guide, release notes and work skill reference now say that a held
   ticket still in the backlog status is not checked, and that a strict
   `tracker claim` gives a way forward only for the released-item case.

**Decided by the requester: departing from the spec's goal 8** (`7a75d76f`, docs
`ca6f435b`)

- `import` and `inbox accept` take the ticket through `transitions.start`. Where
  that differs from `exclusive-claim-transition`, a second person could come in
  through it. These two commands now refuse if **either** transition is still
  offered from where the claim led. `start` and `tracker claim`, which take the
  ticket through `exclusive-claim-transition`, check that one alone. The spec said
  "about no other key"; the reviewer argued it was wrong for the intake commands,
  and the requester chose to check both.

**Accepted as is, by the requester**

- A ticket the caller already holds, still in the backlog status, on a workflow that
  excludes nobody, is accepted by a strict `start` without the check (row 3 of the
  outcome's measurement; criterion 23 is partly met). What the ticket offers from
  there says nothing about the active status, and re-applying the transition is what
  the idempotent claim must avoid. The real answer needs the workflow definition,
  which is already
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`.
  It is written down in the changelog, the guide, the release notes and the
  capability entry.

**Filed rather than fixed: pre-existing**

- `2026-09-24-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list`
  (`2c0ddb0a`). A strict `tracker claim` of an unassigned ticket past
  `statuses.active` still gets a bare transition list, and on a permissive workflow
  it moves the ticket back before refusing. A take-over of a colleague's ticket on
  the active status on a directed workflow gets the same bare list.

**Noted, not acted on**

- `transitions: null` under strict mode now yields two problems: the existing
  "expected a mapping" and the new one saying `start` is missing. Harmless, and
  outside criterion 12's null or blank case.
- A recordless `sync` of a discarded item on a legacy `catch-up: true` binding no
  longer claims the ticket before walking it. That matches the resolution rule, and
  it is recorded here because the spec's D2 did not name it.

## Evidence

- Full suite, bare `pytest` on the final code (`ca6f435b`): **4462 passed, 3 skipped**
  in 1197.62s, with no failures or errors. That is 4459 plus the three test cases
  added at verify (the take-over test and the two landed-elsewhere cases); the skip
  count is unchanged.
- Targeted runs after each verify fix: 482 passed (after `5aba0717`) and 456 passed
  (after `7a75d76f`) across the tracker test files.
- Every new test for a verify fix was mutation-checked. Undoing the fix turned it
  red: the take-over test (the pre-send refusal removed), the landed-elsewhere test
  (the `landing = outcome.status` line removed), and the import-checks-both test (red
  before the code existed).
- `tcw validate`: OK. `tcw capabilities check`: OK. `tcw capabilities drift`: none.
- Both capability entries, `work/require-tracker-backed-work` and
  `work/synchronize-external-tracker-work`, stay **Supported**, and their text matches
  what shipped, including the check-both decision.

## Closeout

- **Route:** committed directly on `main`; no worktree or branch to merge.
- **Documentation:** Jira guide, release notes, changelog, configure and work skill
  references, README, and two capability entries. All were updated in this item.
- **Originating GitHub issue:** none.
- **What the epic still needs:** this was the last child of
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. The
  requester's decision on the epic makes the live-Jira walkthrough the last gate
  before the epic closes, and it runs against this shipped code.
