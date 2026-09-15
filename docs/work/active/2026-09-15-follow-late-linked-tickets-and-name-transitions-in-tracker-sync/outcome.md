# Outcome — Let tracker sync name its transitions, bring a late-linked ticket forward, and stop reading ordinary moves as drift

All eleven planned tasks shipped. Every defect in the request was reproduced against
this tree before it was fixed, and each reproduction is now a test.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 | `3d8974b` | `tcw work tracker sync <slug>` exits 1 when the named item was started by somebody else, naming the owed record and `TCW_WORK_OWNER`; `--all` still exits 0. `binding_refusal` names the owner to run as. |
| 2 | `c0a4013` | A discard moves an unassigned ticket; every other move still refuses one. The post-transition read-back and the progress comment follow the same rule. |
| 3 | `7304aff` | `work.tracker.transitions` accepts `submit`, `rework`, `complete`, `discard`; `discard` may be per-resolution and may be partial. Shape validation only. |
| 4 + 5 | `7215184` | A named transition is selected and refused when it does not fit; drift is judged against the whole path from `since` to the target, via the ladder. |
| 6 + 7 + 8 + 9 + 10 | see below | `link` records that a late-linked ticket is behind; the forward walk; the module docstring; documentation; the capability. |

## The test result

`pytest tests/` — **3394 passed, 2 skipped** in 8m25s, from a baseline of 3367
passed, 2 skipped on the plan commit. A net +27: tests were added, one was deleted
because this item supersedes it, and one parametrisation lost a case to a test of
its own (all listed below). No test was skipped, disabled or quarantined to get
green, and the two skips are the pre-existing ones.

Verified by hand as well, driving the real CLI against the fake rather than reading
an `Outcome` object — the plan's Verification section asked for this, and it is what
proves the user-visible half:

```
tcw work tracker link <slug> SYNC-1     → binding written; ticket still 'To Do'; no transitions applied
tcw work show                           → tracker sync: pending after start … the claim is still owed
tcw work submit                         → exit 0; claimed SYNC-1; ticket walked 'To Do' → 'In Progress' → 'In Review'
tcw work tracker sync <slug>            → exit 0; current; nothing owed
```

That is GitHub #42 end to end, on a workflow with no shortcut to the top.

## What the plan and the spec got wrong

**The plan said delete `_EARLIER` and `_MOVED_FROM`; they stayed.** The ladder
replaced the *window* those tables were being read as, but they answer a different
question — "given the previous local status, where was the ticket left", and "where
did a recorded move start from" — which is a lookup, not a path. Deleting them would
have been churn with a message-ordering change attached (`_EARLIER` is descending,
the ladder ascending) and no behavioural gain. The ladder is still the single source
for the path, which is what Task 7 needed.

**The plan said commit each task; Tasks 4 and 5 share one commit**, and 6 through 10
are grouped. Both pairs were written back to back in the same function, and splitting
them afterwards would have meant surgery on one file for no reader's benefit.

**The spec under-scoped defect 5, and the fix would have shipped a worse bug.**
`sync.py:292` required the ticket to be assigned to the caller *after* the transition,
which a discard never makes it — so a successful unassigned discard would have
reported `did not reach 'Won't Do': it is in 'Won't Do'` and written a conflict that
could never clear. The spec was corrected before implementation, and the relaxation
mirrors the carve-out the owed short-circuit at `sync.py:236` already had.

**The spec's account of defect 2 named the wrong gate first.** Reproducing it showed
that when the ticket is unassigned the *assignment* check fires before the drift
check, so the "it was moved in the tracker" message only appears once the ticket is
assigned. Both variants are in the spec's Reproduction section because of this; the
Problem section leads with the drift path, which is the second gate, not the first.

**Three existing tests were re-pointed and one removed**, all because their subject
changed rather than their rule:

- `test_a_ticket_not_assigned_to_you_is_never_moved` lost its `(nobody, discard)` case
  to the new discard test, and its wording assertion now branches on whose the ticket is.
- `test_a_discard_of_an_unclaimed_ticket_with_no_discard_status_posts_nothing` became
  `…moves_nothing_but_still_comments`: its real subject is that an unmapped `discarded`
  sends no status move, and it only posted nothing because the ticket was unassigned.
- Two strict-mode tests asserted the literal word "nobody" in a message that now says
  "is unassigned". The rule they pin — such a ticket authorizes nothing — is unchanged.
- `test_the_transition_keys_c3_adds_are_not_accepted_yet` was deleted. Its own
  docstring names this change as what supersedes it.

**`test_a_ticket_moved_elsewhere_in_the_tracker_is_not_pulled_back` survived
untouched**, which the spec predicted it would not. The spec expected to re-point it,
because its scenario — ticket behind, item ahead — looked indistinguishable from
GitHub #42. Gating the catch-up on `claim: owed` rather than on the ticket being
behind made them distinguishable after all, and that test now covers the negative
case for free. This came from the advisor consult recorded below and is the single
biggest improvement over the design as specified.

**One cosmetic defect found by the hands-on run and fixed in place.** `tcw work show`
appends `"; the claim is still owed"` to a record's reason, so a reason ending in a
full stop renders as `.;`. The link-time reason drops its full stop. The wart is
pre-existing for other reasons and is not otherwise touched here.

## Autonomous decisions

One advisor was consulted, as a read-only Opus subagent. Codex is not installed in
this container (`which codex` fails), so the two-advisor pair was unavailable; the
user chose a single advisor over attempting an install. Every load-bearing claim it
made was verified against the code before being acted on — none was taken on trust.

| Question | What the advisor said | What I chose, and why |
| -------- | --------------------- | --------------------- |
| How far should chaining go? | The ladder walk, but triggered by `claim == "owed"` rather than by the ticket being behind — a ticket TCW held and somebody pushed back is also behind and must stay refused. | **Adopted.** Verified against `sync.py:82-83`, which already warns about exactly this, and against `test_a_ticket_moved_elsewhere_in_the_tracker_is_not_pulled_back`, which my position-based design would have had to re-point and which now passes untouched. Strictly better than what I specified. |
| Keyed by move or by status? | By move: `MOVE_STATUS` maps both `start` and `rework` to `active`, from different statuses, so one status key cannot name both. | **Adopted** — it agreed with my leaning but with a better argument, which is now the spec's. |
| Validate that a named transition leads to the target? | Yes, and refuse before applying. | **Adopted.** Applying an irreversible transition you already believe is wrong is the worse failure. |
| Per-resolution `discard`, and may it be partial? | Yes to both; partial, unlike `statuses.discarded` under strict mode, because this block exists only to disambiguate. | **Adopted**, with its own test. |
| Where does the unassigned exception live? | Pass the move into `assess_move` with a named constant — and **do not** add the exception to strict-mode `authorize`, because `_strict_refusal` is never called for a discard. | **Adopted.** I had already verified `cli.py:2416-2418` independently and reached the same answer; we converged. |
| `sync`'s exit code | Exit 1 for a **named slug only**; keep `--all` at exit 0. | **Adopted, and it changed my design.** I had specified a blanket "exit 0 only when nothing is owed", which would have broken `test_sync_all_skips_an_item_someone_else_started` and made every team-wide sweep fail. |
| `sync.py:292` will reject the successful discard | Flagged as its highest-value finding. | **Verified and adopted.** I read the line, confirmed the clause, and confirmed `sync.py:236` already had the carve-out to mirror. This would otherwise have shipped. |
| Should the five defects be one item? | Defensible for 1+2+3 (shared ladder), but sequence the plan so 4 and 5 land first and the chaining last. | **Adopted** as the plan's three phases. |

Its suggestion that `link` must write a record was also adopted, after verifying both
blockers it named (`cli.py:2221-2223` selects only items with a record; `cli.py:2249`
runs a recordless slug in `check_only`, which `sync.py:279-282` refuses). Without it
the repair is unreachable from the command the reporter ran.

Nothing was rejected outright. The one place I did not follow it is the plan's
`_EARLIER`/`_MOVED_FROM` deletion, above — it argued for collapsing all three
encodings of the ladder, and I collapsed only the one that was a path.

## Notes

The three originating GitHub issues (#40, #41, #42) stay open, per `CLAUDE.md`:
closing them before the fix is published would tell reporters it is fixed when they
cannot yet install it. Recorded again in `refined-outcome.md` at completion.

No version was cut.
