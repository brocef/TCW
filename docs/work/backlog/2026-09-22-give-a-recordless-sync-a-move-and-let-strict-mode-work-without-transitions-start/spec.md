# Spec — give a recordless sync a move, and let strict mode work without `transitions.start`

Four defects the combined reviews of the tracker-verbs epic found. Findings 1 and 2
share one root cause in `tcw/tracker/sync.py`; finding 3 is a configuration
combination that `tcw validate` currently accepts; finding 4 is a measured behaviour
regression against the tree the epic started from, and was found by a later closeout
review.

Everything stated below about current behaviour was run, not recalled. The seven
probes in `probes/` were copied into the `tests/` folder of a throwaway copy of the
repository at `f2a9523e` and run there against the in-repo fake tracker; the
candidate fixes described in **Design** were applied to that same copy and the whole
suite re-run. Finding 4 was measured a second way, by running one probe against both
`f2a9523e` and the pre-epic tree `bfb2ff33` and comparing the output. The primary
checkout was not modified.

## Capability changes

Planned ledger deltas only. No new capability, and no status changes — both entries
below stay **Supported**.

- **`work/require-tracker-backed-work` (`cap-38f44c`).** Two deltas. The paragraph
  listing what strict mode needs gains `work.tracker.transitions.start`, with the
  reason: strict mode creates work only from a ticket, and the two commands that
  create work from a ticket — `tcw work tracker import` and `tcw work inbox accept` —
  claim through that transition. And its closing line, "A claim only authorizes work
  when the workflow could have refused a second person", becomes true of the shipped
  behaviour again (finding 4): it holds on every path a strict claim can take,
  including a ticket the caller already holds, where what is checked is that the
  workflow would still refuse a second person rather than that a transition was
  applied. The ledger text needs no rewrite for that — it needs the code to match it
  — but the entry should say which key carries the check.
- **`work/synchronize-external-tracker-work` (`cap-207f2c`).** Two sentences change.
  The paragraph that says a failed move "records whether that is pending or
  conflicting" is narrowed to lifecycle moves: a `tcw work tracker sync` run on an
  item with nothing recorded reports what it found and writes nothing at all,
  whatever the answer is. And the "a claim gates work, not resolution" paragraph
  gains that this holds for a `sync` as well, so a ticket somebody reopened on
  finished work is closed again without anyone having to take it.

Taxonomy: both entries sit under the existing `external-work-tracker` Feature. No
new Vocabulary term — "sync record", "claim" and "strict mode" are all already in
use. No taxonomy change is needed.

## Problem

### Finding 1 — a diagnostic `sync` corrupts a healthy binding

`deliver` derives the move it is serving at `tcw/tracker/sync.py:386-387`:

```python
move = move or (MOVE_ONTO[local] if start_record and not start_owed
                else record["move"] if record else None)
```

`tcw work tracker sync` passes `move=None` (`tcw/work/cli.py:3215` and `:3551`). When
the binding also has no sync record, both arms fall through and `move` stays `None`.
If the run then fails, `finish` writes that `None` straight into the record at
`tcw/tracker/sync.py:454-467`:

```python
"state": state, "move": "start" if start_owed else move, "since": since,
```

The binding reader requires every field of a sync record to be text
(`tcw/store/base.py:486-489`), so the record it has just written is one it cannot
read back. Observed, on an item that was healthy before the command ran — started,
ticket in `In Progress` and assigned to the caller, nothing owed — with the tracker
briefly down:

```
sync -> 1  pending — the tracker at https://example.invalid could not be reached
record now: {'problem': "'sync' has no text for: move"}
show:      tracker sync: record cannot be read ('sync' has no text for: move)
```

Under strict mode this then blocks the next lifecycle move, because
`binding_refusal` refuses on *any* record at all (`tcw/tracker/sync.py:978-991`):

```
tcw work complete: refused under strict tracker mode; ... SYNC-1 has a change that
has not reached the tracker (an unreadable record). Run `tcw work tracker sync ...`
first; if that cannot clear it, fix the ticket in the tracker, or unlink the item
and discard it.
```

Two things make that worse than a cosmetic record problem. The refusal describes a
short outage as an unreadable binding, and its advice ends in unlinking and
discarding the item — advice given about a state TCW created itself.

It is worse still on an item that already had a real problem. In
`probes/test_probe_strict_wedge.py`, the first strict refusal is accurate
("SYNC-1 is unassigned. Assign it to yourself in the tracker and put it in
'In Progress' or 'In Review'"). After one diagnostic `sync`, the same command
refuses with the unreadable-record message instead — the sync replaced a useful
refusal with a misleading one.

### Finding 2 — a reopened ticket on finished work cannot be closed again

Same absent move, different consequence. `assess_move` exempts a completion or a
discard from the ownership check (`tcw/tracker/sync.py:266`, against
`MOVES_NEEDING_NO_CLAIM` at `:97`), and `deliver` computes `resolving` from the same
set at `:391-392`. `None` is in neither, so a `sync` of a resolved item whose ticket
somebody reopened is treated as work rather than as a resolution, and demands that
the caller hold the ticket. Observed, for an item completed as `done` whose ticket
was then moved back to `In Progress`:

| ticket held by | result today |
| --- | --- |
| nobody | `conflicting — SYNC-1 is unassigned, so it was not moved from 'In Progress' to 'Done'. Take it with `tcw work tracker claim`…` |
| the caller | `current` — the ticket is closed again |
| another account | `conflicting — SYNC-1 is assigned to Bob, not to you…` |

Where `exclusive-claim-transition` is set, there is no way out inside TCW. The full
loop, reproduced by `probes/test_probe_reopen_exclusive.py`:

```
tracker sync              -> "Take it with `tcw work tracker claim`"
tracker claim             -> "SYNC-1 is in 'In Progress' and does not offer
                              'Start Progress', the transition
                              work.tracker.exclusive-claim-transition names."
tracker claim --take-over -> the identical refusal
tracker sync              -> back to the first message
```

Without that key, `probes/test_probe_recovery.py` shows the only escape is
`claim --take-over` — taking a colleague's ticket away in order to close work that
is already finished, which is the outcome the resolution exemption exists to
prevent.

### Finding 3 — a strict configuration in which no work can be created

`strict: true` with `work.tracker.transitions.start` unset is a dead end that
`tcw validate` currently approves. Reproduced by
`probes/test_probe_strict_import.py`:

```
$ tcw validate -> 0    validate OK

$ tcw work tracker import SYNC-1 -> 1
  SYNC-1 cannot be claimed: work.tracker.transitions.start is not set, and this
  command claims through it. Set it, or take the ticket with
  `tcw work tracker claim` and bind an item to it with `tcw work tracker link`.

$ tcw work new Some work -> 1
  refused under strict tracker mode; nothing was created. Create work from a ticket
  with `tcw work tracker import <ticket>`.
```

The two commands point at each other. `import` refuses at row `1d` of the claim
(`tcw/tracker/intake.py:650, :686-692`), and `link` needs an item that `new` will
not create. The strict block in the parser (`tcw/store/base.py:1470-1490`) checks
`statuses.active`, `statuses.completed`, `statuses.discarded` and
`exclusive-claim-transition`, and nothing else.

The configuration became reachable only today, from two children of the epic
interacting: one made strict mode require `exclusive-claim-transition`, the other
made `transitions.start` optional. Nothing checked the pair. A ticket already
assigned to the caller still imports (row `1e` wins first,
`tcw/tracker/intake.py:681-683`), so a strict project sees nothing wrong on its
author's own tickets and total failure on anybody else's.

The documentation leads projects into it. `docs/release-notes/upcoming.md:8-19` says
"Leave it out — or leave the whole `transitions` block out" and mentions only that
`import` and `inbox accept` still need it. `docs/guide/jira.md:958-962` lists strict
mode's requirements without it, and its command table names `tracker import` as the
way in.

### Finding 4 — strict mode's exclusivity promise is no longer enforced

Strict mode's stated promise is that only one person can take a ticket, and
`work.tracker.exclusive-claim-transition` is required precisely because it is what
keeps that promise (`tcw/store/base.py:1281-1286`). Nothing on the lifecycle path
now checks that the named transition actually is a mutex — a transition a workflow
will still offer after somebody has taken the ticket excludes nobody.

This is a **regression**, not a gap that was always there, and it was measured
rather than argued. The probe below sets `strict: true`, names
`exclusive-claim-transition: Start Progress`, and uses the `GLOBAL` workflow fixture
(`tests/tracker_fake.py:36-40`), where `Start Progress` leads to `In Progress` and is
still offered *from* `In Progress` — a workflow that excludes nobody. It was run
unchanged on both trees:

| `tcw work start` on a bound item, strict, `GLOBAL` workflow | pre-epic `bfb2ff33` | main `f2a9523e` |
| --- | --- | --- |
| ticket unassigned | exit 1, refused: "SYNC-1 was claimed, but its workflow still offers 'Start Progress' from 'In Progress', so a second person could claim it too." Item stays `backlog`. | exit 0, item started |
| ticket already assigned to the caller | exit 1, the identical refusal. Item stays `backlog`. | exit 0, item started, no transition applied by the claim |

Three children each did something defensible, and the combination broke the promise.
One made `exclusive-claim-transition` required under strict mode, which made it the
sole basis of the promise. One composed the lifecycle moves out of claim and sync,
which removed the lifecycle call sites of `claim_refusal` — the only thing that ever
checked the promise was being kept. One made `transitions.start` optional, which
broke the single surviving copy of that check, because it asks about that key rather
than about the exclusivity key. The rename left a visible trace: the pre-epic test
`test_a_workflow_that_cannot_exclude_refuses_import_and_start` is now
`tests/test_tracker_strict.py:471 test_a_workflow_that_cannot_exclude_refuses_import`,
with the `start` half dropped.

There are three separate things to repair.

**(a) The already-yours path asserts nothing and asks nothing.**
`assert_ownership` returns early for a ticket already assigned to the caller at
`tcw/tracker/ownership.py:117-121`, *before* the `if assertion:` block at `:122`. So
a strict claim on a ticket the caller already holds applies no transition and asks no
exclusivity question at all. That early return is correct as far as it goes — it is
what makes the verb idempotent, and re-applying a transition that has already been
applied would fail for want of it — but it currently skips the question as well as
the transition. This is the commonest way to arrive at a held ticket: a user who
assigned it to themselves in Jira, or a project that auto-assigns.

**(b) `claim_refusal` asks about the wrong key.** `tcw/tracker/sync.py:1069` calls
`assess(config.start_transition, …)`, and its refusal at `:1072-1074` names
`config.start_transition`. Since the promise now rests on
`exclusive-claim-transition`, that is wrong in both directions:

- With `transitions.start` unset, `assess` returns `NOT_CONFIGURED` with exclusivity
  `NOT_DETERMINED` (`tcw/tracker/claim.py:104-111`), which is not `NOT_EXCLUSIVE`, so
  `claim_refusal` returns `None` and a strict `import` passes having proved nothing.
- With `transitions.start` naming a non-exclusive transition while
  `exclusive-claim-transition` names a genuine mutex, `claim_refusal` refuses a claim
  that was in fact exclusive.

Neither direction is visible from the tests that survive, because every one of them
sets both keys to the same transition name (`tests/test_tracker_strict.py:279`,
`:363`, `:471` all pass `claim_transition="Start Progress"` on top of the default
`transitions: {start: "Start Progress"}`), so the two keys cannot be told apart.

**(c) A released active item cannot be retaken under strict mode, and the refusal
names no way forward.** Measured on the directed `SYNC` workflow, where
`Start Progress` is offered only from the backlog status. An item is started, strict
is turned on, and the owner runs `tcw work tracker release`, leaving the item
`active` with no owner and the ticket in `In Progress` unassigned — which
`docs/guide/jira.md:405-411` describes as the normal way to hand work over:

```
$ tcw work tracker claim <slug>              -> 1
  SYNC-1 is in 'In Progress' and does not offer 'Start Progress', the transition
  work.tracker.exclusive-claim-transition names. It offers: 'Ready for Review',
  'Finish', "Won't Do", 'Mark Duplicate'.
$ tcw work tracker claim <slug> --take-over  -> 1   the identical refusal
$ tcw work start <slug> --take-over          -> 1   the identical refusal
$ tcw work submit <slug>                     -> 1
  SYNC-1 is unassigned. Assign it to yourself in the tracker and put it in
  'In Progress' or 'In Review', then run this again; discarding the item is always
  allowed.
```

The first three list transitions that do not help and name nothing to do; the fourth,
which comes from `authorize` (`tcw/tracker/sync.py:1030-1035`), names exactly what to
do about the same state. `_strict_claim` already holds a branch that produces the
right shape of message, but it is gated one rung too high: `past` at
`tcw/work/cli.py:490-491` requires `rung > 0`, and a ticket sitting *on* the active
status is rung 0, so it falls through to the bare `assert_ownership` refusal.

## Goals

1. Running `tcw work tracker sync` on a healthy item never leaves that item in a
   worse state than it was in before the command ran, whatever the tracker answers
   or fails to answer.
2. A `sync` that reaches the tracker treats a completion or a discard as a
   resolution, so finished work whose ticket was reopened can be closed again by
   anybody, without a claim.
3. Fixing 1 and 2 does not make a failed `sync` claim the ticket on its next run.
4. `tcw validate` refuses the strict configuration in which no work can be created,
   naming the key to set.
5. `work.tracker.transitions.start` stays optional for every project that is not in
   strict mode — the child completed today is narrowed, not reverted.
6. The seven probes become real tests, so all three findings are held closed.
7. Strict mode enforces its own promise again: a claim it accepts has been checked
   against a workflow that would refuse a second claimant, on every path a strict
   claim can take, including a ticket the caller already holds.
8. The exclusivity question is asked about the key that carries the promise,
   `work.tracker.exclusive-claim-transition`, and about no other key.
9. Every strict refusal about a claim names something the user can do next.
10. `docs/guide/jira.md` stops promising behaviour TCW does not have.

## Non-goals

- **Making `transitions.start` required again in general.** It stays optional
  everywhere except strict mode.
- **Loosening the sync-record reader.** `tcw/store/base.py:485-493` rejecting a
  non-text field is correct; the defect is at the writer. A hand-broken record must
  keep being reported rather than guessed at.
- **A migration for records an earlier version already wrote.** Verified
  unnecessary: `finish` drops any existing record on a successful run
  (`tcw/tracker/sync.py:471`). A forged `move: null` record was cleared by the next
  successful `tcw work tracker sync`, with no repair command and no file surgery.
- **Rewording the unlink-and-discard advice in `binding_refusal`.** It is still the
  right advice for a genuinely undelivered move; this change stops TCW manufacturing
  a state where it is wrong. Only its punctuation is touched (see **Design**, D6).
- **Having `tcw validate` read the project's Jira workflow** to check that
  `exclusive-claim-transition` is genuinely exclusive before any ticket exists. That
  would turn an offline configuration check into one that makes network calls, and
  `tcw validate` is bound as a `pre` hook on `complete`, so completing a work item
  would start depending on the tracker being reachable. It is already filed as
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  and is not designed here. Finding 4 is repaired by asking one ticket what it
  offers, which is what `tcw/tracker/claim.py:1-19` explains the limits of.
- **Checking exclusivity outside strict mode.** `exclusive-claim-transition` may be
  set on a project that is not strict, and there the weaker claim is a documented
  choice rather than a broken promise. The check stays behind `config.strict`, where
  `claim_refusal`'s only surviving call site already puts it
  (`tcw/work/cli.py:2606-2609`).
- **The two items the reviewer raised that were not traced to a failure**: the
  forward-only return that deletes an existing record while its comment says it
  writes none, and whether `exclusive-claim-transition` must be *required* to land on
  the active status. They belong in their own item if anywhere. Finding 4(c) is not
  that second item: it is about the wording of a refusal on a state that already
  refuses, and changes no rule about where the transition must lead.
- **`2026-09-22-refuse-an-unconfigured-start-before-the-ticket-leaves-triage`**, the
  sibling backlog item where `tcw work tracker import` moves a ticket out of triage
  and only then refuses for a missing `transitions.start`. Finding 3 makes that path
  unreachable under strict mode but leaves it reachable without strict, so that item
  is still needed and still separate.

## Design

### D1 — separate the move that is assessed from the move that is recorded

The two uses of `move` in `deliver` are different questions, and the fix is to stop
answering them with one value.

- **The move being assessed** answers "which lifecycle move does this ticket owe?"
  For a bare `sync` with nothing recorded, the item's own status answers it:
  `MOVE_ONTO` (`tcw/tracker/sync.py:88-89`) maps `active → start`,
  `review → submit`, `completed → complete`, `discarded → discard`.
- **The move being recorded** answers "which undelivered local move is still owed?"
  For a bare `sync`, nothing — no local transition happened, which is what `sync`
  *is*. Nothing is owed before it runs and nothing is owed after.

So: derive the assessment move from the item's status, and write no record at all.

### D2 — what the derived move is used for, and what it is not used for

Used for exactly one thing: whether a claim is needed. That is `resolving`
(`tcw/tracker/sync.py:391-392`) and the `move` argument to `assess_move`
(`:881-882`), which reaches the ownership check at `:266`.

**Not used to look up a configured transition name** at `tcw/tracker/sync.py:879`.
This is not a preference; it was measured. A first attempt that let the derived move
reach that line broke two existing tests:

- `tests/test_tracker_sync.py:2025 test_sync_brings_a_ticket_someone_moved_on_back_to_its_item`
- `tests/test_tracker_sync.py:2477 test_sync_still_brings_back_a_ticket_a_start_left_alone`

Both failed with

```
conflicting — SYNC-1 in 'In Review' offers no transition named 'Start Progress'.
```

The reason is the contract `sync` is defined by: it has no window and reconciles a
ticket from wherever it sits, in either direction, while `transitions.start` names a
transition that only leads *out of the backlog status*. Deriving a transition from
the target status — what happens today when `move` is `None` — is the correct answer
for a bare `sync`, and stays.

`takes_ticket` (`tcw/tracker/sync.py:381`) is also left alone. It is built from
`starting`, `bound.catch_up` and `start_owed`, none of which the derived move feeds,
so a bare `sync` still never takes a ticket.

The net behavioural change from D1 and D2 is therefore narrow. For an item in
`active` or `review` the derived move (`start`, `submit`) is not in
`MOVES_NEEDING_NO_CLAIM`, so the ownership rule applies exactly as it does today.
Only `completed` and `discarded` items change — which is precisely finding 2.

### D3 — what a recordless `sync` records, per item status

Nothing, on every status it can be run on:

| item status | assessment move | written to the record |
| --- | --- | --- |
| `backlog` | none — `MOVE_ONTO` has no backlog key | nothing; unreachable anyway |
| `active` | `start` | nothing |
| `review` | `submit` | nothing |
| `completed` | `complete` | nothing |
| `discarded` | `discard` | nothing |

A backlog item never reaches the write: `target` is forced empty for `backlog`
(`tcw/tracker/sync.py:363-364`) and `deliver` returns `none` before it reads the
ticket (`:600-604`).

Three reasons the written value is nothing rather than the derived move:

1. **`start` would re-arm the claim** — the trap the request names. A record naming
   `start` sets `start_record`, and on an unfinished item `start_owed`
   (`tcw/tracker/sync.py:375`) and then `takes_ticket` (`:381`), so the next run
   would claim and assign a ticket that the user only asked TCW to look at.
2. **Any other value invents a window.** `expected_statuses`
   (`tcw/tracker/sync.py:203-242`) derives from a record's move the set of statuses
   the ticket may be in without counting as drift. `sync` is defined as the command
   with no such window. Writing `rework` on an active item, for instance, would make
   the next `sync` refuse a ticket in the backlog status with "TCW does not move it
   back" — turning one defect into another.
3. **Nothing is owed.** No local move happened, so there is no undelivered change
   for the record to describe. The record's job is to say a committed local move has
   not reached the tracker yet.

**Strict mode loses no protection.** Every strict gate reads the ticket fresh
through `authorize` (`tcw/tracker/sync.py:995-1035`), which checks ownership and
status itself and never consults the record. Confirmed by probe: with the record
gone, `probes/test_probe_strict_wedge.py`'s refusals become the accurate ones and
stay refusals —

```
$ tcw work submit    -> refused: SYNC-1 is unassigned. Assign it to yourself in the
                        tracker and put it in 'In Progress' or 'In Review' …
$ tcw work complete  -> refused: SYNC-1 is in 'To Do', not 'In Progress' or 'Done' …
```

— while `probes/test_probe_outage_blocks.py`, where nothing was actually wrong, lets
the completion through instead of demanding a second sync first.

### D4 — finding 2 needs no separate repair

Checked rather than assumed. With D1 in place and nothing else changed, a `sync` of a
resolved item whose ticket was reopened succeeds for all three ownership cases
(unassigned, held by the caller, held by another account), the ticket is moved to
`Done`, and no claim is asked for. The claim loop in
`probes/test_probe_reopen_exclusive.py` is gone at its first step. The exemption
itself is correct; the absent move was all that defeated it. No change to
`MOVES_NEEDING_NO_CLAIM` or to `assess_move`.

One nuance the fix must preserve, and does: `resolving` excludes a catch-up binding
heading for a completion (`tcw/tracker/sync.py:391-392`), because that walk climbs
the working statuses on the way and still needs the ticket held. The derived move
goes into that same expression, so the exclusion still applies.

### D5 — strict mode requires `work.tracker.transitions.start`

Per the requester's decision, which this spec does not re-open. A new module-level
problem string in `tcw/store/base.py`, alongside `STRICT_NEEDS_EXCLUSIVE_CLAIM`
(`:1281-1286`) and worded to match it: the key path, `required when strict is true`,
then why in plain words, then what to set.

Reported **only when the key is absent**, the same rule
`STRICT_NEEDS_EXCLUSIVE_CLAIM` uses (`tcw/store/base.py:1486-1489`). A key written as
`null` or blank already has its own "expected a non-empty tracker transition name"
problem from `_parse_tracker_transitions` (`:1698-1703`), and one problem per key is
enough.

The check has to sit after `transitions` is parsed (`tcw/store/base.py:1508`), not in
the strict block at `:1470-1490`, since that runs before it.

**Attribution needs no special handling.** `attribute_tracker_problems`
(`tcw/store/base.py:1855-1882`) matches a problem to the file that wrote its exact
key path, and a problem about `transitions.start` does not match a recorded path of
`transitions` — the match requires `work.tracker.transitions: ` as a prefix, which
`work.tracker.transitions.start: …` is not. So a node that turns `strict` on gets
the problem attributed to itself even when an ancestor supplied a `transitions`
block with the other four keys. That is the same outcome `STRICT_NEEDS_EXCLUSIVE_CLAIM`
already gets, and the changelog already records the reasoning for it.

Verified in the throwaway copy: `tcw validate` exits 1 with one problem naming the
key, `tcw work tracker import` and `tcw work tracker link` print the configuration
problem, and `tcw work new` refuses with "the tracker configuration has problems, and
strict mode refuses until it is fixed. Run `tcw validate`."

### D6 — the cosmetic refusal sentence

`tcw/tracker/sync.py:986-991` assembles the strict binding refusal so that it reads

> … Run `tcw work tracker sync <slug>` first; It is held by a@example.test, so run it
> as them: `TCW_WORK_OWNER=… tcw work tracker sync <slug>`. if that cannot clear it, …

— a capital letter after a semicolon and a lowercase one after a full stop. The file
is open for D1; fix the punctuation while it is.

### D7 — documentation

Four documents, from this project's documentation entries (`tcw work docs`):

- `docs/release-notes/upcoming.md` — **Tracker-Change / Public-API.** The "Naming the
  start transition is now optional" section gains the strict-mode exception, and the
  "Strict mode needs one more setting" section gains the second setting, stated as a
  breaking change for a project that has `strict: true` today with no
  `transitions.start`. Also the `sync` fix, in user terms: running the diagnostic
  command can no longer leave an item worse than it found it, and a ticket somebody
  reopened on finished work can be closed again without taking it.
- `docs/guide/jira.md` — **Tracker-Change.** The strict-mode section's requirement
  list (`:958-962`) and the sentence that explains why.
- `skills/configure/references/tracker.md` — **Configuration-Key-Change.** The
  `transitions.start` paragraph (`:53-77`) gains "optional except under strict mode",
  in the same shape as the `exclusive-claim-transition` sentence at `:96-97`, and the
  `strict` paragraph (`:187-196`) gains the key.
- `docs/changelogs/upcoming.md` — **Any-Code-Change.** The parser change, the
  `deliver` change, and the one existing test that changes.

`README.md` is not expected to fire: it does not name individual `work.tracker` keys.
The `work` SKILL.md is not expected to fire either — no CLI surface, model or
guardrail of the work component changes.

### D8 — one exclusivity detector, one key, every strict claim path

(a) and (b) are decided as one question, because they are one question: *what does
strict mode check before it accepts a claim, and which key does it check it about?*

The detector is the pre-epic one, restored: **refuse when the named transition is
still offered from the status it leads to.** A transition a workflow will still offer
after you have taken the ticket is not a mutex and proves nothing. That is what
`assess` already computes as `NOT_EXCLUSIVE` (`tcw/tracker/claim.py:128-142`), and
`claim_refusal` (`tcw/tracker/sync.py:1053-1075`) is where it already lives.

Two changes to it:

1. **It asks about `config.exclusive_claim_transition`, not
   `config.start_transition`** (`tcw/tracker/sync.py:1069`), and its refusal names
   that key (`:1072-1074`). This is (b). After D5 the first of (b)'s two wrong
   directions becomes unreachable through configuration — a strict project must set
   `transitions.start` — but the second stays reachable, and asking about the key
   that does not carry the promise would be wrong even if both were unreachable.
2. **It runs on every strict claim path**, which is the lifecycle ones as well as
   `import` and `inbox accept`: `tcw work start`'s claim (`_strict_claim`,
   `tcw/work/cli.py:447`) and `tcw work tracker claim` under strict.

For (a), the already-yours path keeps its early return and its transition is still
not applied — re-applying a transition already applied would fail for want of it, and
that early return is what makes the verb idempotent. What changes is that the
exclusivity **question** is no longer skipped with it. The question is answerable
without applying anything: read what the ticket offers now and ask whether the named
transition is still among them from the status it leads to.

That gives the behaviour the two workflow shapes deserve, and it is why (a) and (b)
cannot be settled separately:

| ticket already the caller's, strict | directed workflow (`SYNC`) | permissive workflow (`GLOBAL`) |
| --- | --- | --- |
| today | accepted, nothing asked | accepted, nothing asked |
| after D8 | accepted — the transition is not offered from the landing status, so the workflow is a mutex | refused, naming the transition and the status it is still offered from |

The idempotent claim a project relies on is preserved on any workflow that was ever
exclusive, and only a workflow that never excluded anybody starts being refused.

Where the check lives is the plan's call — `claim_refusal` gaining a second caller,
or the shared check moving into `assert_ownership` beside the assertion it replaces
on this path. The spec asks only that one piece of code answer it for all three
entry points, so a fourth entry point added later cannot quietly skip it again.

### D9 — a strict refusal about a claim names a way forward

For (c): the refusal a strict `tcw work tracker claim`, `claim --take-over` or
`start --take-over` gives on an item whose ticket sits on the active status
unassigned must name what to do, mirroring the wording `authorize` already uses for
that same state (`tcw/tracker/sync.py:1030-1035`) and the wording `_strict_claim`'s
`past` branch uses for a ticket above it (`tcw/work/cli.py:509-521`).

The condition to widen is `past` at `tcw/work/cli.py:490-491`, which requires
`rung > 0` and so misses a ticket sitting exactly on the active status. The message
for rung 0 cannot simply be the `past` one — "is in 'In Progress', past 'In
Progress'" is not true, and "move it back to 'In Progress'" is not advice. The two
things a user can actually do are: assign the ticket to themselves in the tracker,
which is what `authorize` advises and which, after D8, reaches an exclusivity check
rather than skipping one; or move the ticket back to the status the claim transition
leads from. The exact sentence is the plan's to write; the criterion is that both the
state and at least one way out are named, and that the three commands agree.

Nothing here changes whether the claim is refused. It stays refused: strict mode does
not accept an assignment on its own as proof, and that rule is untouched.

### D10 — documentation corrections that belong with finding 4

- **`docs/guide/jira.md:441-446`** currently promises that with
  `exclusive-claim-transition` set, "a claim — `tracker claim`, or the claim
  `tcw work start` makes — applies that transition before assigning, so a second
  person's transition is refused and they never reach the assignment." That is false
  today on the already-yours path. **It becomes true again by D8 rather than by
  changing the sentence** — with one addition, since D8 does not make it wholly true
  on its own. On a ticket the caller already holds, no transition is applied and none
  can be: the verb has to stay idempotent, and TCW cannot tell a ticket whose
  transition was applied earlier from one somebody assigned in Jira without ever
  transitioning it. What is checked there instead is that the workflow would still
  refuse a second person. The sentence gains that case in a clause; the promise
  itself stands.
- **`docs/guide/jira.md:405-411`** says a released item "stays active with no owner
  until somebody claims it — with `tracker claim`, or with `tcw work start`, which
  takes an active item nobody holds rather than refusing it." True without strict
  mode, false under it, where the ticket has moved past the status the claim
  transition leads from. The passage gains what strict mode does instead, and points
  at the way forward D9 adds.
- **`docs/guide/jira.md:469-474`** says `tcw work tracker claim` "is the deliberate
  exception: it applies the transition from wherever the ticket is". Under strict
  mode it does not — it refuses where the transition is not offered. The paragraph
  needs the strict-mode case stated beside the ordinary one.

These are all **Tracker-Change** entries, the same as the finding 3 documents in D7,
and they join the same release-note and changelog passes.

### Sweep — a sibling of (b) that is not in the request

The repo-wide sweep for siblings of (b) — other readers of `config.start_transition`
that are really asking an exclusivity question — found one more:
`_print_ticket` (`tcw/work/cli.py:2468-2469`), which backs both lines that
`tcw work tracker show` and `tcw work inbox show` print:

```
claimable: …
workflow:  …
```

from a single `assess(client.config.start_transition, …)`. The `claimable:` half is
correctly about `transitions.start` — that is the key `import` claims through, and
`tests/test_tracker_cli.py:202` holds that wording. The `workflow:` half is the
exclusivity question, which after this change is about
`exclusive-claim-transition`. On a project where the two keys name different
transitions, `tracker show` prints an exclusivity verdict about the wrong one. It is
the same defect as (b) at a second call site, and it was correct before the epic,
when there was only one key to ask about.

Folding it in means splitting one `assess` call into two — small, contained, and in a
file the change already opens. It is recorded here rather than assumed: **the plan
decides whether to fold it in or file it**, and criterion 33 is written so that it
can be dropped cleanly if it is filed.

### Abstraction litmus test

All of it passes. D1–D4 operate on *item status*, *the recorded state of a binding*
and *a transition against an external system* — all abstract-store vocabulary. The
binding is read and written through `read_sidecar`/`write_sidecar`, not through file
paths, and "write no record" is the removal of a write, which any store can
implement. D5 is configuration parsing, which is not storage at all. D8–D10 are
entirely about the external tracker and the refusal text around it, and touch no
store operation. Nothing here depends on the filesystem adapter.

### Harness compatibility

Every behaviour lands in the `tcw` CLI, which behaves identically under Claude and
Codex. No skill, hook or injected context carries any part of it. `tcw validate` is
the guarantee for finding 3, and the refusals in `_strict_claim`, `assert_ownership`
and `claim_refusal` are the guarantee for finding 4; a Codex user gets both
unchanged.

## Acceptance criteria

Each says how it is checked: **[fake]** is provable by a test against the in-repo
fake tracker, **[unit]** by a test that calls a function directly, **[read]** needs a
person to read the document.

**Finding 1**

1. On a bound item in `active` with nothing recorded and a healthy ticket, a
   `tcw work tracker sync` that cannot reach the tracker leaves the binding file
   unchanged: no `sync:` key is added, and `tcw work show` afterwards prints no
   `tracker sync:` line. Today it adds `sync: {move: null, …}` and `show` prints
   `record cannot be read`. **[fake]**
2. The same holds when the run reaches the tracker and the answer refuses the move:
   a conflicting bare `sync` on an item with nothing recorded writes no record
   either. **[fake]**
3. After a failed bare `sync`, a strict-mode `tcw work submit`, `rework` or
   `complete` is never refused with "has a change that has not reached the tracker".
   It either proceeds, or is refused for a reason that was already true before the
   `sync` ran and that names the ticket's real state. **[fake]**
4. After a failed bare `sync` on an `active` item whose ticket another account holds,
   the next successful `tcw work tracker sync` does not assign the ticket to the
   caller and does not apply the claim transition. **[fake]** — this is the trap; it
   fails against a fix that writes `start` into the record.
5. A binding carrying a `move: null` record written by an earlier version is cleared
   by the next successful `tcw work tracker sync`, with no repair command.
   **[fake]** — already true today; the criterion is that it stays true, since it is
   what makes a migration unnecessary.

**Finding 2**

6. `tcw work tracker sync` on a `completed` item whose ticket somebody moved back to
   the active status moves the ticket to the mapped completed status, and exits 0,
   in all three cases: the ticket unassigned, held by the caller, held by another
   account. The refusal "Take it with `tcw work tracker claim`" does not appear.
   Today two of the three refuse. **[fake]**
7. The same holds for a `discarded` item, for each discard resolution the project
   maps. **[fake]**
8. With `work.tracker.exclusive-claim-transition` set, criterion 6 holds on the first
   run, so the `sync → claim → claim --take-over → sync` loop is not reachable.
   **[fake]**
9. A catch-up binding (`catch-up: true`) heading for a completion still requires the
   ticket to be held, and still walks the statuses rung by rung. **[fake]** — the
   exemption must not widen into this case.
10. A bare `tcw work tracker sync` on an `active` item still reconciles a ticket a
    person moved on by hand back to where the item says, on a project that names
    `work.tracker.transitions.start`. **[fake]** — held by the two existing tests
    named in **What this must not break**, which must pass unchanged.

**Finding 3**

11. `tcw validate` on a node with `strict: true` and no `work.tracker.transitions.start`
    exits non-zero with one problem naming that key, and the node's tracker block
    reads as not configured. Today it exits 0. **[fake or unit]**
12. The problem is reported only when the key is absent. `transitions.start: null`
    and `transitions.start: "  "` each keep their single existing "expected a
    non-empty tracker transition name" problem and gain no second one. **[unit]**
13. The problem is attributed to the file being validated, not to an ancestor that
    supplied a `transitions` block without `start`. **[unit]**
14. With `strict` false or absent, a node with no `transitions` block at all
    validates clean and behaves exactly as it does today. **[unit and fake]**
15. `docs/release-notes/upcoming.md` states, in plain words, that a project with
    `strict: true` and no `transitions.start` will get a validation error on upgrade,
    and what to set. **[read]**
16. `docs/guide/jira.md`'s strict-mode requirement list includes `transitions.start`,
    and its description of `tracker import` as the way into strict work no longer
    stands without that key. **[read]**
17. `skills/configure/references/tracker.md` says `transitions.start` is optional
    except under strict mode, in the same shape as its `exclusive-claim-transition`
    sentence. **[read]**

**Across findings 1–3**

18. `docs/changelogs/upcoming.md` records the parser change, the `deliver` change,
    and the one existing test that changed and why. **[read]**
19. The strict binding refusal sentence reads as ordinary prose — no capital after a
    semicolon, no lowercase after a full stop. **[fake]**
20. The seven files in `probes/` are replaced by tests in `tests/` that assert rather
    than print, covering criteria 1–10 and 19, and `probes/` is removed from the item
    folder. **[read]**
21. The full test suite passes with findings 1–3 fixed. **[fake]** — measured at 4413
    passing against 4414 before, the difference being the one test named below.
    Criterion 35 is the same check with finding 4 included.

**Finding 4 — the exclusivity regression**

22. **The regression criterion.** With `strict: true`, `exclusive-claim-transition`
    naming a transition the workflow still offers from the status it leads to (the
    `GLOBAL` fixture), a `tcw work start` of a bound item whose ticket is
    **unassigned** is refused before the item moves, naming the transition and the
    status it is still offered from. The item stays in `backlog`. **[fake]** — this
    fails on `f2a9523e` (exit 0, item started) and passes on `bfb2ff33` (exit 1).
23. The same holds when the ticket is **already assigned to the caller**. **[fake]**
    — same measurement, and this is the half that (a) is specifically about.
24. The same holds for `tcw work tracker claim` under strict mode. **[fake]**
25. On a **directed** workflow, where the named transition is not offered from the
    status it leads to, every one of those commands still succeeds, and a claim of a
    ticket the caller already holds still sends nothing to the tracker. **[fake]** —
    this is the idempotence that `tcw/tracker/ownership.py:117-121` exists for, and
    a fix that applies the transition on that path breaks it.
26. The exclusivity verdict is computed from
    `work.tracker.exclusive-claim-transition` and not from
    `work.tracker.transitions.start`. Provable only by a configuration where the two
    keys name **different** transitions, since every existing test sets them the
    same: with `transitions.start` naming a non-exclusive transition and
    `exclusive-claim-transition` naming an exclusive one, a strict claim succeeds;
    with the two reversed, it is refused. **[fake]**
27. The refusal text names `work.tracker.exclusive-claim-transition`, not
    `work.tracker.transitions.start`. **[fake]**
28. The check does not run when `strict` is false: a project that sets
    `exclusive-claim-transition` without strict mode gets exactly today's behaviour
    on both workflow shapes. **[fake]**
29. On an item that is `active` with no owner whose ticket sits unassigned on the
    mapped active status, `tcw work tracker claim`, `tcw work tracker claim
    --take-over` and `tcw work start --take-over` each refuse with a message that
    names the ticket's state **and** at least one thing the user can do next, and all
    three agree. Today all three print a transition list and name nothing to do.
    **[fake]**
30. Following the way forward that refusal names leaves the user better off than
    before: on a directed workflow, doing what it says and re-running the command
    succeeds. **[fake]** — a criterion that fails if the advice is wrong rather than
    merely present.
31. `docs/guide/jira.md`'s promise that a claim "applies that transition before
    assigning, so a second person's transition is refused" is true of the shipped
    behaviour, including for a ticket the caller already holds, where the sentence
    says what is checked instead of what is applied. **[read]**
32. `docs/guide/jira.md` no longer tells a strict-mode reader that a released active
    item can simply be retaken with `tracker claim` or `tcw work start`, and no
    longer says without qualification that `tracker claim` applies the transition
    from wherever the ticket is. **[read]**
33. **Folded in, not filed** — the coordinating session confirmed it is the same
    defect as finding 4(b) at a second call site (`tcw/work/cli.py:2468-2469`, where
    one `assess` call backs both printed lines), and fixing a defect everywhere its
    callers reach it is this project's rule.
    `tcw work tracker show` and `tcw work inbox show` report their `workflow:`
    exclusivity verdict from `exclusive-claim-transition` while their `claimable:`
    verdict stays about `transitions.start`, and a project whose two keys name
    different transitions sees each line answer about its own key. **[fake]**
34. `docs/release-notes/upcoming.md` tells a strict-mode project that claims are
    checked for exclusivity again, and that a project whose workflow never excluded a
    second claimant will now be refused where it was previously accepted. **[read]**
35. The full test suite passes with all four findings fixed, and the tests written
    for criteria 22–30 live alongside the existing strict tests rather than in a
    probe folder. **[fake]**
36. `docs/changelogs/upcoming.md` records finding 4 as a regression, naming the three
    children whose combination caused it, so that a later reader can see why six
    rounds of per-child review did not find it. **[read]**

## What this must not break

The child completed today made `work.tracker.transitions.start` optional for ordinary
projects, and that must stay true. These tests hold it and must keep passing
unchanged:

- `tests/test_tracker_import.py:213 test_import_with_no_start_transition_names_the_key`
- `tests/test_tracker_import.py:219 test_inbox_accept_with_no_start_transition_refuses_the_same_way`
- `tests/test_tracker_import.py:227 test_import_of_a_ticket_already_held_needs_no_start_transition`
- `tests/test_tracker_claimability.py:227 test_an_unset_start_transition_is_its_own_verdict`
- `tests/test_tracker_cli.py:202 test_show_says_the_start_transition_is_unset_rather_than_wrong`
- `tests/test_tracker_sync.py:2522 test_a_start_with_no_configured_name_derives_from_the_target_status`
- `tests/test_tracker_sync.py:2538 test_a_start_with_no_configured_name_consults_no_name`
- `tests/test_tracker_sync.py:2557 test_an_owed_start_with_no_configured_name_derives_too`
- `tests/test_tracker_sync.py:2578 test_a_ladder_hop_onto_the_active_rung_with_no_configured_name_derives_too`

These hold the `sync` reconciliation contract that a careless version of D1 breaks:

- `tests/test_tracker_sync.py:2025 test_sync_brings_a_ticket_someone_moved_on_back_to_its_item`
- `tests/test_tracker_sync.py:2477 test_sync_still_brings_back_a_ticket_a_start_left_alone`

These hold the exclusivity behaviour that finding 4 restores rather than invents, and
must keep passing — they are the three survivors of the check the epic dismantled:

- `tests/test_tracker_strict.py:279 test_a_claim_on_a_workflow_that_offers_it_everywhere_is_refused`
- `tests/test_tracker_strict.py:297 test_a_claim_on_the_directed_workflow_is_not_refused`
- `tests/test_tracker_strict.py:471 test_a_workflow_that_cannot_exclude_refuses_import`

All three set `exclusive-claim-transition` and `transitions.start` to the same
transition name, so they pass either way and cannot by themselves show that D8
changed the key. Criterion 26 is what does that, and it needs a fixture where the two
differ — which the plan will have to add.

These hold the idempotent claim that D8 must not cost:

- `tests/test_tracker_strict.py:305 test_a_claim_row_1e_from_the_wrong_status_is_refused`
- `tests/test_tracker_import.py:227 test_import_of_a_ticket_already_held_needs_no_start_transition`

**Exactly one existing test must change** for findings 1–3, and it is the one that
encodes the configuration finding 3 makes illegal:

- `tests/test_tracker_strict.py:489 test_strict_import_of_a_held_ticket_needs_no_start_transition`
  builds `strict_node(strict=True, claim_transition="Start Progress", transitions=None)`
  and asserts the import succeeds. Under D5 that node no longer validates, so the
  import is refused for a configuration problem instead. Its premise fails twice over
  once finding 4 lands as well: its subject is that `claim_refusal` reads
  `transitions.start`, and after D8 `claim_refusal` does not read that key at all. It
  should be deleted rather than converted, and its replacement is criterion 25 — that
  a claim of a ticket the caller already holds still succeeds and still sends
  nothing, on a directed workflow. The plan should confirm that reading and say so.

Running the whole suite with the findings 1–3 fixes applied produced that one failure
and no other. The findings 1–3 fixes and the finding 4 fix were measured separately;
the plan should run the suite once with all four applied, which is criterion 35.

## Risks

- **A project with `strict: true` and no `transitions.start` breaks on upgrade.**
  Every strict-gated command refuses until they set the key. This is the requester's
  chosen outcome — a reported configuration error beats a silent substitution — but
  it is a breaking change and criteria 15–17 exist so that nobody meets it without
  warning. The blast is bounded: the configuration is only a day old, since before
  the child completed today the parser required the key outright.
- **Losing the record removes a line from `tcw work show` after a failed bare sync.**
  A user who runs `sync`, sees `pending — the tracker could not be reached`, and then
  runs `tcw work show` will no longer see it repeated there. Judged acceptable: the
  command that discovered it printed it, nothing is owed, and the alternative is the
  corruption this item exists to remove.
- **"Write no record" is a wider rule than "write a sensible move".** It changes
  every bare `sync` on a binding with nothing recorded, not only the failing ones
  the findings describe. Mitigated by criteria 2, 4 and 10 and by the full-suite run;
  the reason it is the right width is that the record describes an undelivered local
  move, and a bare `sync` makes none.
- **The derived move reaches `assess_move`, which is shared.** The blast is confined
  to `deliver`'s own call site; `assess_move` is also called from `walk`
  (`tcw/tracker/sync.py:555-568`), which passes a hop move explicitly and is
  untouched. Criterion 9 guards the walk.
- **Three separately-correct changes combined into finding 4, and nothing reviewed
  the combination.** Each child was right on its own terms. Requiring
  `exclusive-claim-transition` under strict mode was right. Composing the lifecycle
  moves out of claim and sync was right, and removing call sites that the new
  composition no longer routed through was part of doing it. Making
  `transitions.start` optional was right. What nobody owned was the invariant that
  spans all three: *strict mode checks that the transition carrying its promise is
  actually a mutex.* Each child could see its own call sites; none could see that
  after all three landed, zero call sites remained on the lifecycle path and the one
  survivor was reading a key that had just become optional. This is the same failure
  mode as findings 1–3 — an interaction only visible in the combined change — which
  is the second time it has produced defects in this epic, and the strongest argument
  for reviewing a batch as one diff rather than child by child. A criterion (36)
  exists to write it down where a later reader will find it.
- **Restoring the check refuses claims that are accepted today.** A strict project
  whose workflow never excluded a second claimant is being accepted now and will
  start being refused. That is the point — the promise was never being kept — but it
  is a behaviour change for anybody who turned strict mode on during the window the
  epic opened, and criterion 34 exists so that they are told. There is no silent
  version of this fix: the alternative is leaving strict mode promising something it
  does not do.
- **D8's blast radius is wider than (a) alone.** It changes what a strict
  `tcw work start` and `tcw work tracker claim` do on every workflow, not only the
  already-yours path. Criteria 25 and 28 bound it: a directed workflow must be
  unaffected, and a project that is not strict must be unaffected entirely.
- **A strict user who releases an item may still be stuck after D9.** D9 makes the
  refusal name a way forward; it does not make the claim succeed. On a directed
  workflow the way forward works (criterion 30). On a workflow where the ticket
  cannot be moved back to the status the claim transition leads from, and assigning
  it in the tracker then meets a non-exclusive verdict, the user's remaining option
  is turning strict mode off. That is honest but not comfortable, and it is worth
  watching whether it is reported.
- **Four changes in one item.** Findings 1 and 2 share a root cause; finding 3 is
  unrelated and lands in the parser; finding 4 is unrelated to all three and lands in
  the claim path. They are together because they came from reviews of one epic that
  is held open for all four. If the plan finds any one of them dominating, splitting
  it out is reasonable — but the epic stays open until every one lands. Finding 4 is
  the strongest candidate to split, being a regression with its own measurement
  against a second tree.

## Notes

- **Nothing in the code contradicted the request.** All three of the original
  findings reproduced as described, including the trap: a first candidate fix that
  derived the move and wrote it into the record does re-arm the claim, and a second
  that let the derived move choose a configured transition breaks two existing tests.
  Both were measured, not reasoned about.
- **Finding 4 reproduced as described, with one correction and one addition.** The
  correction is a line number: the `rung > 0` test that gates `_strict_claim`'s good
  refusal is on `tcw/work/cli.py:491`, inside the `past` expression that begins at
  `:490`. The addition is that the regression is wider than the already-yours path
  (a) on its own — measured against `bfb2ff33`, a strict `tcw work start` on a
  non-exclusive workflow is also accepted today when the ticket is **unassigned**,
  where the pre-epic tree refused it. So (a) is one of two halves: the already-yours
  path skips the question, and the ordinary path has no caller left to ask it. Both
  are covered, by criteria 23 and 22 respectively.
- **The sweep found one sibling of (b) that the request did not name**, in
  `tcw work tracker show` and `tcw work inbox show`. It is written up under
  **Design → Sweep** and left as the plan's call, with criterion 33 marked so it can
  be dropped if it is filed instead.
- **What the request left open, and what this spec decided.** The request asked what
  a recordless `sync` should record and framed the answer as a per-status value. The
  answer here is "nothing, on every status", for the three reasons in D3. It is still
  a separation of the assessed move from the recorded one — taken to its limit, where
  the recorded one is absent. If a later reader wants a record kept, the thing to
  argue with is reason 2 in D3: any value TCW could write gives the next `sync` a
  window, and `sync` is the command defined by not having one.
- The candidate fixes used to verify findings 1–3 are not a plan. They show the
  behaviour is reachable and that the suite survives; where the code goes, how it is
  commented, and how the probes become tests are the plan's to decide.
- **Finding 4 has no candidate fix yet, only a measurement.** What is established is
  the current behaviour, the pre-epic behaviour, and the three places that produce
  the difference. D8's placement question — one shared check called from three entry
  points, versus moving it into `assert_ownership` — was deliberately left open,
  because either answer satisfies the criteria and choosing between them needs the
  plan to look at what else `assert_ownership` is called from.
