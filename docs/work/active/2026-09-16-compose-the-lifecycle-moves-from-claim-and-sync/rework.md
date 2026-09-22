# Rework: compose the lifecycle moves from claim and sync

## Verdict

**Sent back** on 2026-09-22. Two reviews ran on `cb5232d2`:

- `tcw:verifier`: every checkable criterion was met, the full suite passed (4351
  passed, 3 skipped, 0 failed), and eight mutations it redid went red. It
  recommended acceptance after three documentation corrections.
- `adversarial-code-reviewer`: NOT DONE. It found three blocking defects, each
  confirmed with a throwaway probe against `FakeJira`. None is covered by a spec
  criterion, which is why the verifier's pass did not find them. The coordinating
  session confirmed B1 by reading `tcw/tracker/sync.py:700-720`.

## What the implementation still has to do

Each item needs a test that fails before the fix, plus a recorded mutation.

### Blocking

**B1. A discard or completion must never deliver a recorded start first.** The
recorded-start block (`sync.py:700-720`) applies the start transition before the
resolution. For a start that never reached the tracker, a discard therefore moves
the ticket to In Progress and then to Won't Do (the probe recorded `['21', '51']`).
If the start hop is refused, the discard is never delivered at all. This is the
march through working statuses that `ladder_steps`' own comment (`:114-117`)
rejects. Add `not resolving` to the block's condition, and check whether the
completion side needs the same guard. Test both a discard and a completion that
carry a start record.

**B2. A failure during the recorded-start hop must leave the record naming
`start`.** Today `finish` (`:419-425`) writes the move being made. So if the start
hop's transition or its read-back fails during a `submit`, the record becomes
`{move: submit, since: ""}`, the start is forgotten, and every later `sync`
refuses as drift ("… TCW does not move it back"). Record `move: "start"` from the
refusal return at `:708`, the transition failure, and the read-back failure at
`:717`. Test: failed start, then `submit` with the hop unreachable, then a `sync`
that recovers.

**B3. A move that takes the ticket must not move it backwards through
`exclusive-claim-transition`.** Decided by the requester on 2026-09-22. When the
key is set and the ticket is already past the claim's own status (rung above 0):

- **Without strict mode:** skip the assertion transition, take the ticket by
  assigning it and reading the assignment back, and leave the ticket where it is.
  Say so in the output, including that this claim relied on assign-and-read-back
  only.
- **Under strict mode:** refuse the start before the item moves, and say why. The
  ticket is past where the exclusive transition applies, and strict mode does not
  accept assign-and-read-back as proof of exclusivity. Say what to do: move the
  ticket back in the tracker, or turn strict mode off.

This covers both `deliver` (`sync.py:620` exempts `starting`, and the HELD check at
`:730` uses the rung from before the claim) and `_strict_claim` (`cli.py:470-479`).
Then reword spec Design 3 / criterion 1 and every doc sentence promising
"forward only", so they state the rule as it now is. Test with the GLOBAL workflow
(transition offered from every status), both strict and not.

### Significant

**S1. A claim whose transition applied but whose assignment failed must say
what happened and how to recover.** Today a strict start whose assignment gets a
400 (or whose transition POST timed out after applying) leaves the ticket moved
and unassigned, with the item still in backlog. The message does not mention that
the ticket moved, and a retry then fails, because the transition is no longer
offered. That refusal is the very property that makes the transition exclusive.
Folded in, although part of it touches C1's code:

- (a) `ownership.py`'s `refused()` carries whether the transition was applied.
- (b) `_strict_claim` and `deliver` say: "{key} was moved to '{status}' but is not
  assigned to you. Assign it to yourself in the tracker, then run this again."

**S2. Document that completing an older catch-up binding still needs the ticket
held.** With `resolving` false for a completion on a catch-up binding, a ticket
another account holds is refused, which goes against criterion 8. Only bindings
written by older versions are affected. Document it in `outcome.md` and the Jira
guide rather than change it, unless the fix falls out of B1.

### False text

- `docs/guide/jira.md`, triage section: "Nothing else takes a ticket out of triage
  … `submit`, `rework` … never do". Not true when an undelivered start record is
  present, because the recorded start takes it out. Say so.
- The release notes and `jira.md`: "only `tcw work tracker sync` moves a ticket
  backwards". `rework` moves In Review back to In Progress by design (criterion
  18d). State the actual rule: a lifecycle move never moves a ticket back past its
  own window.
- The release-note bullet on `submit`/`rework`: "with or without strict mode … If
  Jira cannot be reached they go ahead". Under strict mode they are refused
  (criterion 11).
- `sync.py:640-643`: "Claiming it from there could move it back" is true only when
  `exclusive-claim-transition` is set. Make it depend on the key, in line with
  B3.
- `sync.py:676-679`: "→ {key} is already held by you." is printed on a
  `submit`/`complete` carrying a leftover start record, and right after
  `_strict_claim` has just taken the ticket. Print it only when this move took the
  ticket and it was already held before the move.
- `sync.py:688-690`: "so it was not claimed or moved back" is reached after a claim
  this run made. Reword it.
- The `walk()` comment (`:484-488`): it says both paths come only from
  `link --sync-status` and that the claim is owed. Neither is true any more.

### Small coverage gap

- The record `tracker create` writes: assert that its fields equal
  `RECORD_FIELDS`. That restores the guard the removed
  `test_the_link_that_asks_for_a_catch_up_writes_no_claim` gave: no command writes
  a claim into the record.

## Not this item's (record in `outcome.md`, do not fix)

- The web app's `work.start` on an active item nobody holds now returns HTTP 422
  (`ValueError("takeover requires an owner")`), because the store accepts the case
  and the web app passes no owner (`tcw/serve/__init__.py:953`,
  `tcw/store/fs.py:4056-4059`). A known effect, and a candidate follow-up item.
- Two simultaneous starts of an unowned active item from different checkouts: the
  last writer wins.
- The contradictory "resolved … take it with `tracker claim`" advice (present on
  main already), and the untested backup refusal in `_tracker_link` for an item
  someone else holds.

## After the fixes

Run the full suite, then re-run the adversarial review on the rework's own changes,
bounded to B1-B3 and S1. The review ends when nothing blocking remains in "belongs
to this change".

---

# Round 2 of rework (2026-09-22)

The first rework was reviewed again, bounded to its own commits
(`6be7f507..6ce7d062`). Verdict NOT DONE. B1 and B2 were each fixed at one point
on a path that has two, and S1's new sentence is false on one of the two failures
it was written for. Every finding below was reproduced end to end against the fake
tracker. The coordinating session confirmed finding 1 by reading the code. The
requester chose this round on 2026-09-22 and answered the two open questions.

### R1. B1 is unfixed on the `sync` path

`move` is replaced with the recorded move at `sync.py:358`, one line before
`resolving` is computed, so on `tcw work tracker sync` with a leftover start
record `move` becomes `"start"` and `resolving` is false however the item stands
— including discarded and completed. `starting` is computed before that
replacement, so the claim branch falls through too.

Reproduced through the CLI with no hand-built state: items X (`--part default`)
and Y (`--part backend`) bound to one ticket; `tcw work start X` with the tracker
down leaves a start record; `tcw work complete X --resolution wontfix` is held
because sibling Y is open, deliberately keeping the record; `tcw work tracker
unlink Y`; then `tcw work tracker sync X` applies `['21', '51']`, marching the
ticket To Do → In Progress → Won't Do. With the ticket unassigned the same sync
also claims it first.

**Requester's answer:** a `sync` of a resolved item must never claim its ticket or
advance it into a working status first. Guard on the item, not on the move —
`local not in RESOLVED_STATUSES` in the recorded-start condition
(`sync.py:753-756`), which also subsumes `not resolving` for the lifecycle path.
Apply the same reasoning to the pre-backlog step at `sync.py:572`, which on a
`sync` of a resolved item takes the ticket out of triage for the same wrong
reason. Reword the comments at `sync.py:114-117` and `:746-751` if they end up
saying something other than what the code does.

### R2. B2's fourth failure path: taking the ticket

B2's fix covers the start hop only. Taking the ticket happens earlier on the same
run — `leave_pre_backlog` (`sync.py:572-581`) and `assert_ownership`
(`sync.py:669-695`) — and each failure goes through `taken_back` → `finish`, which
writes the later move's name.

Reproduced with no race and no outage: `work.tracker.pre-backlog: {Triage:
Accept}`, a ticket already yours in Triage, and the real transition out of Triage
named something else (a typo, or a renamed workflow). A failed `start` records
`{move: start}`; `submit` passes the gate because the ticket is yours;
`leave_pre_backlog` refuses; the record becomes `{move: submit}`. The start is
forgotten, and the item is then permanently stuck: every later `sync` refuses as
drift, and `takes_ticket` is false for ever after.

**Requester's answer:** the record keeps naming `start` for the claim and the
Triage failures too, not only for the hop. Carry one flag rather than three
assignments — set `start_owed` beside `takes_ticket` (`sync.py:357`), clear it
once the start hop has landed and been read back, and have `finish` write
`"start"` while it is set. The three `move = "start"` lines then go.

### R3. S1's sentence is false when the read-back failed

`transitioned` is the wrong fact to key the message on. `assert_ownership` refuses
in two later places: the assignment failing (`ownership.py:144`, the ticket really
is unassigned) and the read-back failing (`:151`), which happens only after the
assignment succeeded. Both callers print "was moved to X but is not assigned to
you", which in the read-back case is false, contradicts the sentence printed
beside it, and replaces advice that would have worked — running it again succeeds,
because `assert_ownership` returns early for a ticket already yours.

Say the ticket is unassigned only from the assign-failure return, and let the
read-back return keep "Run this again to find out." Add the caller-level test for
the read-back case, which is the coverage gap that let this through. Fix the wrong
premise in `test_a_failure_after_the_assertion_reports_the_transition_and_where_it_led`'s
docstring while you are there.

### R4. Two more false sentences

- `docs/guide/jira.md:449`: "The transition is never applied to a ticket that is
  already past `statuses.active`" is false — `tcw work tracker claim`
  (`cli.py:3317`) still applies it, with no rung check, and says so as it does.
  B3 was scoped to `deliver` and `_strict_claim`, so scope the sentence to
  lifecycle moves or name `tracker claim` as the deliberate exception.
- `docs/guide/jira.md:362`: "Nothing else ever does. `complete`, a discard …
  never" take a ticket out of triage — false for a `complete` on a catch-up
  binding, where `resolving` is deliberately false. Add the same "only on an old
  binding" caveat the ownership half already carries (`jira.md:725-733`).

### R5. Spec criterion 2

Criterion 2 ("the same `start` assigns the ticket to the running account") was not
amended alongside criterion 1 and is now false for the case criterion 1 carves
out. Amend it.

### Non-blocking, fold in if cheap

- `cli.py:1372`: the `TransitionCommitError` recovery calls `_deliver_after`
  without `say_claim`, so a strict start that trips it prints the claim line twice.
- `cli.py:506-513`: the strict refusal says applying the transition "would move it
  back" even where the workflow does not offer it from there.
- `_deliver_after(say_claim=False)` suppresses the whole claim message, so a
  second successful claim after someone stole the ticket mid-run is swallowed.
  Limit the suppression to the "already held by you" sentence if that is cheap.

### Where this stops

This is the last scheduled round. After it, a bounded review of these fixes only.
Anything still open is reported to the requester split into "belongs to C4" and
"needs a separate item" rather than starting another round.
