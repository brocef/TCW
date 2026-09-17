# Outcome: Make claim and release assert ownership without moving a ticket

Two verbs, one optional configuration key, and no edit to any of the delivery
code C2 and C4 are going to rewrite. That last part was the goal of the rescope
this item went through at its spec stage, and it held: the diff touches
`deliver`, `record_unsent`, `authorize`, `intake.claim` and `FsWorkStore.start`
not at all. `binding_refusal` has one line changed, and only its wording — the
"started by" hint became "held by" (Task 2, `tcw/tracker/sync.py:659`), which the
spec's Design step 2 asked for. Its behaviour and control flow are untouched.

## What shipped, task by task

**Task 1 — unassigning, and a fixture that stops lying** (`502cea94`).
`JiraClient.assign` takes `str | None`; `None` is Jira's documented unassign.

The more valuable half was the test fixture. `tests/tracker_fake.py` wrote
whatever value it was handed onto the ticket and answered 204, and its issue
reader treats `""` as unassigned — so a `release` implemented to send an empty
string would have passed every test here *and* left the ticket looking correct,
while real Jira answers 400. It now accepts only `None` or an account id
registered through `account(...)`. All 240 existing tracker tests passed against
the stricter fake, which is the evidence that nothing was relying on the hole.

**Task 2 — the ownership guard says "held by"** (`af62de9e`).
`_started_by_someone_else` → `_held_by_someone_else`, and the wording at all three
places that report it (`tcw/work/cli.py:2409`, `:2639`, `tcw/tracker/sync.py:658`).
After this item an item can carry an owner while sitting in `backlog`, never
started, so "started by" became false. The take-over remedy is a parameter now
rather than hardcoded to `start --take-over`, because `release`'s override is
`--force`.

**Task 3 — `tcw/tracker/ownership.py`** (`a736065b`). `assert_ownership` and
`drop_ownership`, with `OwnershipOutcome`. Exclusivity is assign-then-read-back.
`intake.claim` is neither imported nor edited: it reads the transition name from
`config.claim_transition` directly, so it can only ever apply the start
transition. Its row `1e` rule — a ticket already assigned to the caller is
already held — is carried across by hand, and there is a test explaining why.

**Tasks 4 and 5 — the two verbs** (`182787ae`). `_tracker_claim` and
`_tracker_release`, sharing `_tracker_ownership_target` so the two cannot drift
in what they check or in what order. The local half is guarded first and written
last, and `_own_locally` commits it.

**Task 6 — the race** (in `a736065b`, with the module). Two tests using the
fake's `before` hook.

**Task 7 — `work.tracker.exclusive-claim-transition`** (`5e4a79a0`). Optional,
top-level, absent by default.

**Task 8 — documentation** (`b12327fe`) and the capability (`7e400f82`).

## Test result

`pytest` over the whole suite, from the worktree with the editable install
re-pointed at it. Per-area runs during the work: 240 tracker tests green after
task 1, 473 after task 2, 16 new ownership tests, 14 new CLI tests, 54 config
tests, 21 validate tests, 301 doc-surface and help-coverage tests.

**Every new test that passed on its first run was mutation-checked**, and the
mutation is named here rather than merely claimed:

| What was broken | What went red |
| --- | --- |
| `assign` coerces `None` to `""` | `test_assign_unassigns_with_a_null_account_id` |
| the read-back removed, trusting the assign | both race tests, and the assertion test |
| a transition applied with no assertion configured | 7 of 16 ownership tests |
| row `1e`'s already-ours short circuit removed | `test_claiming_under_an_assertion_stays_idempotent` |
| the local ownership guard removed from `claim` | both guard tests — the hole the spec review found |
| the local owner written *before* the ticket half | `test_a_tracker_that_will_not_unassign_leaves_the_owner_alone` |
| the owner write staged but not committed | `test_a_claim_is_committed_rather_than_left_staged` |
| `exclusive-claim-transition` removed from `TRACKER_KEYS` | `test_an_exclusive_claim_transition_is_kept` |

## What the plan and spec got wrong

**`--part` was specified for both verbs and does not belong** (`bfb2ff33`). `link`
and `import` take it to choose *which item* a ticket maps to. These verbs are
given the item by slug, and an item has exactly one binding, which already
records its part — so the flag could only ever have agreed with the binding or
contradicted it. Dropped, and the spec and plan corrected rather than worked
around.

**The plan put the CLI tests in `tests/test_tracker_cli.py`; they went in a new
`tests/test_tracker_hold.py`.** That file is built on a request recorder, and
these tests need the stateful fake. A small thing, recorded because the plan
named a file.

**The plan's task 6 turned out to be part of task 3.** The race tests needed the
module and nothing else, so they were written with it rather than in a later
pass. No behaviour changed; the ordering in the plan was simply finer than the
work.

**One spec claim was wrong about the fake, in the item's own favour.** The spec
said criterion 4 needed the `GLOBAL` workflow. It does not — with no assertion
configured no transition is applied at all, so the workflow is irrelevant. That
precondition was inherited from the epic's transition-based wording. Corrected in
the criterion before implementation started.

**Writing the race test the obvious way produced a passing run that proved
nothing.** The first version had Bob read the ticket *after* Alice's assignment
had landed, so Bob was correctly refused and Alice won — a queue, not a race. A
real race has both accounts read while the ticket is unassigned. The test now
reads both tickets up front and registers the hook after, so the one-shot lands
on Alice's read-back. Worth recording because the failing version looked right.

## What a green suite does not prove

- **Jira's own read-after-write consistency.** The fake interleaves
  deterministically, which proves the logic. Two accounts against a live project
  is what would prove the rest.
- **When Jira refuses an unassignment.** A project that forbids unassigned issues
  answers 400. The handling is tested by making the fake fail on demand; the
  trigger is not reproducible here.
- **Whether read-after-write is an acceptable floor.** A judgment about a trade,
  and the requester's to make at the epic's verification.

Both live-project checks are already on the epic's verification list.

## Notes

- **An older `tcw` reading a config that sets the new key loses the whole
  `tcw work tracker` surface**, not just this feature, because an unknown
  `work.tracker` key fails the block closed. Accepted on the requester's standing
  decision not to design around old versions, and documented in both the guide
  and the configure skill so nobody meets it by surprise.
- **The capability is seeded `Missing`** with its planning back-pointer, and
  `capabilities.yaml` records it under `new:`. It flips to `Supported` at
  completion, which is what the gate checks.
- **This item got smaller during its own spec review**, and the epic's spec was
  changed rather than worked around: the `claim: owed | done` removal moved to C2
  after the review proved the replacement rule wrong. Three more epic-level
  amendments came out of the same review — C3's blocker was false and is gone,
  acceptance criterion 3 promised an exclusivity read-after-write does not give,
  and goal 2 asked for a comparison between a Git identity and a Jira account id
  that nothing can make.
