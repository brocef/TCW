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
