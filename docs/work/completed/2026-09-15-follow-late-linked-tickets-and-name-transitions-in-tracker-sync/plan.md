# Plan — Let tracker sync name its transitions, bring a late-linked ticket forward, and stop reading ordinary moves as drift

Ordered so the suite is green at every commit boundary, and so the riskiest change —
the forward walk, which applies transitions nobody asked for one at a time to a shared
tracker — lands last, on infrastructure that already exists and with its tests already
written.

Three phases, in the order the spec's Risks section requires: the two small independent
fixes first (no new configuration, each independently verifiable), then the
configuration schema, then the ladder. If anything has to slip, phase C is what slips,
and nothing earlier depends on it.

Baseline for every "suite still green" below: **3367 passed, 2 skipped**, `pytest
tests/`, ~8m20s.

## Phase A — the independent fixes

### Task 1 — `sync` stops reporting success for a named slug it skipped

**Modifies** `tcw/work/cli.py` (`_tracker_sync`, lines 2208-2280), `tcw/tracker/sync.py`
(`binding_refusal`, lines 329-348).
**Adds** cases to `tests/test_tracker_sync.py`.

Split the single loop at `cli.py:2234-2238` so the named-slug branch and the `--all`
branch can differ. For a named slug, the owner skip keeps its message, appends the
record's state and that it is still owed, and sets `code = 1`. For `--all` the skip
stays exit-0 and unchanged. `binding_refusal`'s refusal text (`sync.py:345-347`) gains
`TCW_WORK_OWNER=<owner>`, read from `store.get(slug).owner` — the owner comparison
itself stays in `cli.py`, so no git/owner logic moves into `tcw/tracker/`.

**Proves:** acceptance criteria 20, 21, 22. Reproduction 4 flips from exit 0 to exit 1.

### Task 2 — an unassigned ticket is moved by a discard, and only a discard

**Modifies** `tcw/tracker/sync.py` (`assess_move` 95-124, the owed short-circuit 234-236,
the post-apply read-back 288-297, `deliver`'s call into `assess_move`),
`tcw/tracker/progress.py` (`_send`, 121-125).
**Adds** cases to `tests/test_tracker_sync.py`; **narrows**
`test_a_ticket_not_assigned_to_you_is_never_moved` (line 378).

Add `MOVES_ALLOWING_UNASSIGNED = frozenset({"discard"})` beside `MOVE_STATUS`. Give
`assess_move` the move it is serving and split its assignment check three ways —
caller / unassigned / another account — with an unassigned message that names claiming
the ticket instead of implying somebody holds it. Relax the post-apply clause at
`sync.py:292` to `local in RESOLVED_STATUSES or again.assignee_id == again.me_id`,
mirroring the carve-out the owed short-circuit already has at `sync.py:236`; without
this a successful unassigned discard reports `"… did not reach 'Won't Do': it is in
'Won't Do'."` and records a conflict that can never clear. Apply the same discard
exception in `progress.py:_send` so the comment is posted rather than skipped.

Write the failing test first in both halves: the discard-succeeds case, and the
read-back case with the ticket already in the target and still unassigned.

`test_a_ticket_not_assigned_to_you_is_never_moved` loses exactly one parametrised case —
`(assignee=None, move="discard")` — which becomes the new test. Its `assignee=B` cases
and its non-discard `assignee=None` cases stay untouched.

**Proves:** criteria 15, 16, 17, 18, 19. Reproduction 5 flips to a closed ticket.

## Phase B — naming a transition per move

### Task 3 — the configuration keys parse and validate

**Modifies** `tcw/store/base.py` (`TRACKER_TRANSITION_KEYS` 1086, `TrackerConfig` 1040-1068,
`parse_tracker_config` 1090-1215, and the rationale comment at 1082-1085).
**Adds** `_parse_tracker_transitions` beside `_parse_tracker_statuses`, plus
`transition_name(transitions, move, resolution)` beside `target_status`.
**Adds** cases to `tests/test_tracker_config.py` and `tests/test_tracker_validate.py`.

`TRACKER_TRANSITION_KEYS` becomes `{claim, submit, rework, complete, discard}`;
`TrackerConfig` gains `move_transitions: dict`. `discard` accepts a string or a mapping
of known resolutions to strings. **A partial `discard` mapping is valid** — unlike
`statuses.discarded` under strict mode (`base.py:1176-1182`), which must be complete,
because `transitions` is an optional override whose purpose is to disambiguate only
what is ambiguous. Shape checks only, per the request. Rewrite the comment at
`base.py:1082-1085`, which is the standing rationale for `claim` being alone and stops
being true here.

Nothing reads `move_transitions` yet, so the suite stays green on this task alone.

**Proves:** criterion 3, and the first half of 26.

### Task 4 — a named transition is selected, and refused when it does not fit

**Modifies** `tcw/tracker/sync.py` (`assess_move`), `tests/tracker_fake.py` (add an
`AMBIGUOUS` workflow whose `In Progress` offers `("31","Finish","Done")` and
`("32","Abandon","Done")`).
**Adds** cases to `tests/test_tracker_sync.py`.

When a name is configured for the move, match it against `ticket.offered` with
`_normalize` and apply the single match **that leads to the target**. No match, two
matches, or a match leading elsewhere is conflicting before anything is applied —
reuse `claim.py:99-110`'s `AMBIGUOUS` wording for the two-match case. With no name
configured, the existing code path is untouched, which is what keeps
`test_no_transition_or_two_to_the_target_is_conflicting` (line 406) passing unmodified.

**Proves:** criteria 1, 2, 4, 5, 6. Reproduction 1 flips with a name configured and
stays conflicting without one.

## Phase C — the ladder

### Task 5 — one ladder replaces `_EARLIER`, `_MOVED_FROM` and `expected_statuses`

**Modifies** `tcw/tracker/sync.py` (delete `_EARLIER` and `_MOVED_FROM` at 41-45, replace
`expected_statuses` at 65-92, update `deliver` 190-192 and `authorize` 370-373).
**Adds** cases to `tests/test_tracker_sync.py`.

Introduce the rungs of spec D.0 as one ordered structure derived from
`config.statuses`, and one function that returns **the path a walk would take from a
given tracker status forward to a target**. Use it first as the drift window: a ticket
anywhere on the path from the record's `since` to the target is not drift. Compute the
window by walking the path and collecting what it passes — never by inverting the
status mapping, which is ambiguous when `completed` and `discarded` map to the same
name (GitHub #40's own configuration). A discard has no intermediates: the window is
`{since, target}`.

This is the refactor with the widest reach and no new capability, so it is a task of
its own: the whole existing suite is its test, plus the two new cases.

**Proves:** criteria 13, 14; keeps 11 green.

### Task 6 — `link` records that a late-linked ticket is behind

**Modifies** `tcw/work/cli.py` (`_tracker_link`, around 2101-2165).
**Adds** cases to `tests/test_tracker_link.py`.

When `link` binds an item whose status is past `backlog`, write
`{state: pending, move: <the move that lands on the item's own status>, since: "",
claim: owed}` through the existing sidecar write. Linking a `backlog` item writes
nothing, so the ordinary case is unchanged. This is a **local** write only — nothing is
sent to the tracker, so `link`'s promise that the ticket is untouched survives.

Without this the repair is unreachable from `sync`: `--all` selects only items that
already carry a record (`cli.py:2221-2223`) and a named recordless slug runs
`check_only=True` (`cli.py:2249`) and refuses at `sync.py:279-282`.

**Proves:** criterion 9, and makes 10 reachable.

### Task 7 — the forward walk

**Modifies** `tcw/tracker/sync.py` (`deliver`'s owed path, 234-297).
**Adds** cases to `tests/test_tracker_sync.py`.

Gate on `claim == "owed"` — **not** on the ticket being behind. A ticket TCW claimed and
someone pushed back is behind and must stay refused; `claim: owed` is the existing field
that means "TCW has never held this ticket", so no schema change. When the claim is owed
and the ticket is below the target, claim onto rung 1 and then take one hop per rung,
each hop's transition selected by Task 4's rule for the move that lands on that rung,
re-reading the ticket between hops. A hop that cannot be resolved stops the walk, leaves
the ticket where it reached, and records `since` as the status actually read. Suppress
the `since` fallback while the claim is owed, so nothing is fabricated.

Write every test in this task before the code, including the negative one (criterion 11).

**Proves:** criteria 7, 8, 10, 11, 12. Reproductions 2 and 3 flip.

## Phase D — statements, documentation, capability

### Task 8 — correct the statements that stop being true

**Modifies** `tcw/tracker/sync.py` (module docstring, 1-19).
The `base.py:1082-1085` comment is handled in Task 3.

`sync.py:10-14` currently asserts a ticket is moved only when assigned to the
authenticated account and sitting where the previous status left it. Both halves change.
Docstrings are specification in this repo, so this is work, not cleanup.

**Proves:** criterion 26.

### Task 9 — Documentation Sync

Every entry whose trigger fires, in one pass over the finished diff:

| Document | Trigger | What changes |
| -------- | ------- | ------------ |
| `docs/guide/jira.md` | **Tracker-Change** | The "exactly one transition" rule (line ~340) and the new `transitions` keys; the catch-up and its unmapped-intermediate limit; the unassigned-discard rule; `sync`'s exit code for a named slug and `TCW_WORK_OWNER`; `link` writing a record for an item past `backlog`, and what strict mode then does. Correct "exits 1 while any item it acted on is still pending" (line ~366). |
| `skills/tcw-configure/references/tracker.md` | **Configuration-Key-Change** | The `work.tracker.transitions` keys. It documents `transitions.claim` at lines 5, 33, 44 and the ancestor merge of `transitions` at 66 and 116 — all of which now describe a block with five keys, not one. |
| `docs/changelogs/upcoming.md` | **Any-Code-Change** | Grouped Added/Changed/Fixed entries, technical. |
| `docs/release-notes/upcoming.md` | **Public-API** | Plain language, no module names. |
| `README.md` | **Public-API** | Only if its Jira summary states either rule that changes; check, and record "no change needed" if not. A grep for the one-transition rule finds it in `docs/guide/jira.md` and the capability description, not in `README.md` — confirm that at the time. |
| `skills/tcw-work/SKILL.md` and references | **Skill-Driven-Component** | Only if they state the moved rules; check and record the answer either way. |

Run the `tcw:documentation-sync` skill over the finished diff rather than trusting this
table — the table is the prediction, the skill is the check.

**Proves:** criterion 24.

### Task 10 — reconcile the capability

**Modifies** the item's `capabilities.yaml` sidecar, via the `tcw-capabilities` skill.

`work/synchronize-external-tracker-work` (`cap-207f2c`) is **changed**, not added: the
three sentences the spec names under **Capability changes** stop being true, and the
`Limits I accept:` paragraph gains the unmapped-intermediate bound.

**Proves:** criterion 25.

### Task 11 — full suite and the acceptance sweep

`pytest tests/` from a clean tree, then walk the 26 acceptance criteria and record each
as met or not.

**Proves:** criterion 23.

## Verification

What the suite cannot check, and what is done instead:

- **No real Jira.** This node configures no `work.tracker` (`tcw-config.yaml` has no
  such block), and no credentials are available here; a live run against Atlassian is
  out of reach and would be a hard blocker if it were required. Everything is exercised
  against `tests/tracker_fake.py`, which models the workflow, the offered transitions,
  assignment and the account. The gap this leaves is real and is named in the spec's
  Risks: Jira's advertised `to.name` can be wrong where a post-function decides the
  destination, and the fake cannot reproduce that.
- **Hands-on CLI.** The suite drives `deliver` directly in most cases. Separately run
  the real CLI — `tcw work tracker link`, `tcw work submit`, `tcw work tracker sync`,
  `tcw work show` — against a scratch node wired to the fake, and read the actual
  printed output and exit codes, rather than trusting an outcome object.
- **The guide's prose.** Re-read `docs/guide/jira.md` end to end after Task 9 against
  the shipped behaviour, since a guide can be internally consistent and still describe a
  rule that no longer exists — which is exactly how Problem 4's documented-and-wrong
  sentence survived.
- **The record's shape across versions.** Confirm by reading `_sync_record`
  (`base.py:417-435`) that no new `state`, `move` or `claim` value was introduced, since
  an older `tcw` sharing the store would read one as a broken record.

## Notes

No new blockers between items: every task above is inside this one item, and this item's
own blockers are unchanged. The three GitHub issues stay open until publication, per
`CLAUDE.md`.

## Revision after review (2026-09-16)

Recorded by hand. Task 6 is superseded: `link` writes the owed record only under
`--sync-status`, and otherwise notes `status-synced: false` on the binding. Task 7's
walk gained a direct-transition attempt, a refusal for a ticket already past its item
or already resolved, a resume path for a walk interrupted after the claim, and aims
at the item's current status. The reasons and the user's decision are in the spec's
section of the same name; the commits are `bf84a3f` and `cd6d296`.
