# Plan: Make claim and release assert ownership without moving a ticket

Eight tasks. Tasks 1 to 3 build the pieces the two verbs need, each one green on
its own; task 4 adds the verbs; tasks 5 and 6 are the two riskiest behaviours,
placed after their infrastructure exists and with their tests written first;
task 7 is the opt-in key; task 8 is documentation.

Nothing here edits `deliver`, `record_unsent`, `binding_refusal`, `authorize`,
`intake.claim` or `FsWorkStore.start`. That is the property that keeps this child
out of C2's, C4's and the strict-mode item's way, and every task below is checked
against it.

**Implementation happens in a worktree.** `tcw work start <slug> --worktree`
puts the edits in `.worktrees/<slug>/` on `work/<slug>`. The editable install
must be re-pointed at the worktree first — `pip uninstall tcw -y` if a stale
hook lingers, then `pip install -e .worktrees/<slug> --no-deps` — and pytest and
the CLI run with the current directory set to the worktree, or the primary
checkout's source is what runs. Restore it with
`pip install -e /Users/brian/Projects/TCW` before `tcw work complete`.

## Task 1 — Unassigning becomes possible, and the fake stops accepting anything

**Modifies** `tcw/tracker/jira.py`, `tests/tracker_fake.py`.
**Creates** nothing.

`JiraClient.assign` (`jira.py:268`) widens to `account_id: str | None`, and its
docstring says `None` unassigns and is the value Jira documents for it. `_json`
already serializes `None` to JSON `null`, so this is a signature and a docstring,
not a mechanism.

Then the fake stops certifying wrong values. Its assignee handler
(`tests/tracker_fake.py:205-207`) assigns whatever it is given and returns 204,
so `assign(id, "")` — which real Jira answers with 400 — passes today, and
`tracker_fake.py:215` then reads `""` as unassigned. It must raise for any value
that is neither `None` nor an account id registered through `account(...)`.

*Proves:* a new test in `tests/test_tracker_client.py` asserting that
`assign(issue_id, None)` leaves the fake's ticket unassigned, and that
`assign(issue_id, "")` and `assign(issue_id, "nobody")` now raise. **Write the
second half first and watch it fail** — it is a fixture becoming stricter, so it
must be red before task 1's fixture change lands.

*Suite stays green:* no production caller passes anything but a real account id
today, so the stricter fake cannot break an existing test. If it does, that test
was relying on the hole and the finding is real — report it rather than loosen
the fake back.

## Task 2 — The ownership guard says "held by", not "started by"

**Modifies** `tcw/work/cli.py`, `tcw/tracker/sync.py`, and whichever tests assert
the current wording.

`_started_by_someone_else` (`cli.py:2402-2412`) is the guard both verbs reuse.
Two changes, no decision it takes moves:

1. **Rename its wording to "held by".** After this child an item can carry an
   `owner` while sitting in `backlog`, never started, so "started by" becomes
   false at all three places that say it: the function itself (`cli.py:2409`),
   `sync --all`'s skip line (`cli.py:2639`), and strict mode's hint
   (`tcw/tracker/sync.py:658-660`).
2. **Make the take-over remedy a parameter.** It currently hard-codes
   `tcw work start <slug> --take-over` (`cli.py:2412`). `release`'s escape is
   `--force`, and sending a user to `start --take-over` to release something
   would be wrong.

*Proves:* `grep -rn "started by" tcw/` returns nothing for these three sites, and
the existing tests that assert the old wording are updated in the same commit —
`rg -l "started by" tests/` names them, and each is read before it is changed, so
a test asserting a decision is not quietly turned into one asserting a string.

*Suite stays green:* wording-only, so any failure is a test asserting the old
string, updated here.

## Task 3 — Both verbs' shared body

**Creates** `tcw/tracker/ownership.py`.
**Modifies** nothing.

One module, two functions, no CLI and no store:

- `assert_ownership(client, ticket, *, assertion="")` — the claim's tracker half.
  Refuses a resolved ticket and a ticket held by another account; applies
  `assertion` as a transition first when one is named, and otherwise applies
  none; assigns; re-reads; and reports whether the caller still holds it. Returns
  an outcome carrying the holder's name for the refusal message.
- `drop_ownership(client, ticket)` — the release's tracker half. Unassigns and
  reports a refusal rather than raising.

**It does not import `intake.claim` and does not call it.** `intake.claim` reads
`client.config.claim_transition` directly (`intake.py:329`), so it cannot serve a
differently-named transition, and editing it would reach into C4's subject. What
is carried across by hand is row `1e`'s rule (`intake.py:355-357`): a ticket
already in the landing status and already assigned to the caller is a claim that
needs no second transition — without it, idempotence fails the moment the
assertion key is set.

*Proves:* `tests/test_tracker_ownership.py`, new, driving both functions against
the fake with no CLI in the picture: idempotence for the holder, refusal naming
another holder, refusal of a resolved ticket, and — with `assertion` unset —
**zero POSTs to any transitions endpoint**, asserted against the fake's recorded
requests rather than inferred from the resulting status. Covers acceptance
criteria 1, 3 and 11.

## Task 4 — The two CLI verbs

**Modifies** `tcw/work/cli.py`.

`_tracker_claim` and `_tracker_release`, with their parsers registered beside
`link`, `unlink` and `sync` (`cli.py:3043-3210`). Both follow `_tracker_link`'s
shape: `_tracker_client(label)`, `validate_part`, `_item_or_reason`,
`binding_of`, then the work.

Order inside `claim`: identity, then the local guard from task 2 (`--take-over`),
then the binding, then the ticket, then `assert_ownership`, then the local write
and its commit. Inside `release`: identity, local guard (`--force`), binding,
ticket, `drop_ownership`, then the local write and its commit. **The local write
is last in both**, so a ticket half that failed never leaves the item claiming
something the tracker does not agree with.

Neither verb takes `--owner`. `_local_owner(st)` is called with no explicit
value, so the ladder is `TCW_WORK_OWNER`, then Git email, then Git name.

Help text follows the group's existing shape — a description saying what happens
in the tracker and what happens in this node, and an epilog listing what is
refused — because `tests/test_tracker_help.py`, `tests/test_cli_help_coverage.py`
and `tests/test_documented_cli_surface.py` all read it.

*Proves:* `tests/test_tracker_cli.py` gains four things.

1. The round trip — claim, claim again, release, claim from a second account —
   covering acceptance criteria 1, 2, 7 and 8.
2. **`claim` on an unbound item** in a node that has a tracker configured exits
   0, sets `owner`, and says no ticket was assigned; in a node with no tracker
   configured it exits 1 with `_tracker_client`'s existing message. Acceptance
   criterion 5.
3. **A refused unassignment**, driven with the fake's `fail("PUT", "/assignee",
   …)` hook: `release` exits non-zero, says the ticket was not released, and the
   item's `owner` is unchanged. Acceptance criterion 10 — and the reason the
   local write is last in both handlers, so this test is what stops that ordering
   being undone later.
4. **`release` on an `active` item** exits 0, leaves the item `active` with an
   empty `owner`, and a subsequent `claim` from another account exits 0.
   Acceptance criterion 14.

`tcw work tracker claim --help` and `release --help` exit 0 and the help coverage
tests pass.

## Task 5 — The local ownership guard, which is where the hole was

**Modifies** `tcw/work/cli.py` (both new handlers), `tests/test_tracker_cli.py`.

The riskiest behaviour, and it is placed here rather than folded into task 4
because it is the one the spec review found missing: the ticket-assignee check
does not fire on an unbound item, or on a bound item whose ticket is unassigned,
and without a local check either one silently overwrites another person's
`owner`. `owner` is not a display field — three decisions read it (`cli.py:2409`,
`cli.py:2639`, `tcw/tracker/sync.py:658`).

**Write these four tests first and watch each fail** against task 4's code:

1. `claim` on an **unbound** item owned by another identity exits non-zero and
   names them.
2. `claim` on a **bound** item whose ticket is unassigned and whose `owner` is
   another identity exits non-zero and names them.
3. Both of the above with `--take-over` exit 0 and set `owner` to the caller.
4. The `release` equivalents, gated by `--force` rather than `--take-over`.

Covers acceptance criteria 6 and 9.

## Task 6 — The lost race, and what it leaves behind

**Modifies** `tests/test_tracker_ownership.py`, and `tcw/tracker/ownership.py`
only if the tests say so.

Two tests, both driven by the fake's `before("PUT", "/assignee", …)` hook, which
runs a second account's whole claim inside the first's — the pattern
`tests/test_tracker_claim.py:219` already uses.

1. **A assigns → B's whole claim runs → A reads back.** Exactly one reports
   success: A's fails and names B. Acceptance criterion 4. The workflow is
   irrelevant, because with no assertion configured no transition is applied at
   all.
2. **What the loser leaves.** After A's failed run the ticket is assigned to B
   and A's item has no `owner` — the split the spec says is real and does not
   undo. Then B releases, A claims again, and both halves are A's. Acceptance
   criterion 13.

The second test is the one worth having: it pins a state the design accepts,
so a later change that quietly "fixes" it by rolling back the assignment has to
argue with a test rather than with a paragraph.

## Task 7 — `work.tracker.exclusive-claim-transition`

**Modifies** `tcw/store/base.py`, `tcw/work/cli.py` (the claim handler passes it
through), `tests/test_tracker_config.py`, `tests/test_tracker_validate.py`.

One optional top-level key: added to `TRACKER_KEYS` (`base.py:1106`), parsed like
`inbox-query` is — absent is `""`, present-but-empty is a problem — and carried
as a `TrackerConfig` field (`base.py:1063-1097`). It merges through
`merge_tracker_blocks` (`:1408`) with no special case, because it is an ordinary
scalar key.

The claim handler passes it to `assert_ownership` as `assertion`. Nothing else
reads it. `transitions.claim` is untouched, which is what leaves C3 free to
remove that key.

*Proves:* `tcw validate` accepts a block with the key and one without, and
reports an unknown key for a misspelling — acceptance criterion 15. Plus a test
in `tests/test_tracker_ownership.py` that with the key set to a transition the
ticket offers, a second account's claim is refused by the workflow on a workflow
that does not offer it from its own destination — acceptance criterion 12.

**Known and accepted:** an older `tcw` reading a config that sets this key loses
the whole `tcw work tracker` surface, because an unknown key fails the block
closed (`base.py:1149-1150`, `cli.py:2143-2152`). That is the requester's
standing decision not to design around old versions, recorded in the spec.

## Task 8 — Documentation

One block, after the code, over the finished diff. Every entry below has its
trigger fired by this change; none is speculative.

| Document | Trigger | What changes |
| -------- | ------- | ------------ |
| `docs/guide/jira.md` | Tracker-Change | A new section between "Taking a ticket" (`:221`) and "Linking and unlinking" (`:306`) for holding and releasing a ticket: what each verb does, that neither moves the ticket, the race window in plain words, and `--take-over` / `--force`. "Claimable and exclusive" (`:181`) gains the optional assertion key and what opting in costs |
| `README.md` | Public-API | The `tcw work tracker` row (`:657`) gains `claim` and `release`; the lifecycle table (`:510-516`) is left alone, because no lifecycle command changes |
| `skills/work/references/commands.md` | Skill-Driven-Component | Two rows in the tracker table (`:95-100`) |
| `skills/configure/references/tracker.md` | Configuration-Key-Change | `work.tracker.exclusive-claim-transition`: what it is for, that it is optional, and that setting it means claims move the ticket |
| `docs/release-notes/upcoming.md` | Public-API | One user-facing entry for the two verbs and one for the optional key |
| `docs/changelogs/upcoming.md` | Any-Code-Change | Added: the verbs, `tcw/tracker/ownership.py`, the config key. Changed: `JiraClient.assign` accepts `None`; the ownership guard's wording; the fake validates assignees |

Committed separately from the code, and the `documentation-sync` skill is invoked
to check the list rather than trusting this table.

**No capability record is written by this plan.** The new capability
`work/hold-a-tracker-ticket` is declared through the `tcw-capabilities` skill at
the implement stage, with the standing ledger checked for contradictions.

## Verification

What the suite cannot settle, and what has to be done by hand or by a person:

- **The race against real Jira.** Task 6 proves the logic with a deterministic
  interleave; it does not prove Jira's own read-after-write consistency behaves
  as this design assumes. The epic's plan already schedules a live-project pass,
  and this is one of the things it is for.
- **A project that forbids unassigned issues.** Where that setting is off, Jira
  answers the unassignment with 400 and `release` cannot complete. Task 1 makes
  the fake able to fail on demand, which proves the handling; nothing here proves
  when Jira would. It goes on the live-project list with the race.
- **Whether read-after-write is an acceptable floor.** A judgment about a trade,
  not a fact. It is the requester's at the epic's verification, and if the answer
  is no, the remedy is to recommend the assertion key rather than to redesign.
- **That nothing in `deliver`'s neighbourhood moved.** Checked by reading the
  final diff for any hunk touching `deliver`, `record_unsent`, `binding_refusal`,
  `authorize`, `intake.claim` or `FsWorkStore.start`. A hunk in any of them means
  this child grew into C2's or C4's territory and the plan was wrong.
- **Acceptance criterion 16** — that `test_tracker_sync.py`,
  `test_tracker_strict.py`, `test_tracker_link.py` and `test_tracker_import.py`
  pass unchanged. Their baseline on `main` before this work: 229 passed across
  the first two plus `test_tracker_claim.py` and `test_tracker_link.py`.

## Notes

- **Every acceptance criterion traces to a task**, checked by walking the spec's
  list rather than by memory: 1 and 3 to tasks 3 and 4; 2, 5, 7, 8, 10 and 14 to
  task 4; 4 and 13 to task 6; 6 and 9 to task 5; 11 to task 3; 12 and 15 to task
  7; 16 to Verification. The first pass of this plan had 5, 10 and 14 covered by
  no task at all, which is what the self-review is for.
- **Task ordering puts the two riskiest things last but one**, which is
  deliberate: tasks 5 and 6 both depend on the verbs existing, and both are
  test-first against code that is already there, so each failure is about the
  behaviour under test rather than about something not being wired up yet.
- **Task 2 is separable and could be its own item.** It is kept here because the
  wording only becomes wrong *because* of this child, and fixing it where all
  three call sites route through is a smaller diff than three later corrections.
- **If task 3 finds it cannot avoid editing `intake.claim`**, stop and say so
  rather than editing it: that would mean the assertion transition cannot be
  supported without reaching into C4's subject, and the answer is to drop task 7
  and ship the floor alone, not to widen the child.
