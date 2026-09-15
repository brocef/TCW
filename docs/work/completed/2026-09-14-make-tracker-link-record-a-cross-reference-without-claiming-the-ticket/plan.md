# Plan — Make `tracker link` record a cross-reference without claiming the ticket

Eight tasks. Tasks 1–6 are code and leave the suite green at every boundary;
task 7 records the hand-off on the sibling item; task 8 is the Documentation
Sync block.

The ordering principle: the binding document is emptied of `claimed-by` **first**
(task 1), because that is what makes `_binding_for` writable from a `TicketRead`
and therefore what lets `link` stop claiming at all. Doing it the other way round
leaves an intermediate commit where `link` has no `ClaimOutcome` and no legal way
to produce a binding.

---

## Task 1 — Take `claimed-by` out of the binding document

**Modify** `tcw/tracker/intake.py`

- `binding_document` (line 161): drop the `account_id` and `account_name`
  keyword parameters and the `"claimed-by"` entry from the emitted mapping.
- `_BINDING_KEYS` (line 177): drop `"claimed-by"`, so `unlink_document` stops
  trying to move a key that is no longer written.
- `find_binding` (line 131): leave the `RESOLVED_STATUSES` skip in place, but
  correct the docstring — the clause "a resolved item's binding cannot be
  repaired from here" stops being true at task 3. Replace it with the surviving
  reason (a discarded item's ticket may be taken again) and state the
  consequence: a ticket held by a resolved item can be bound to a second, open
  item.

**Modify** `tcw/work/cli.py`

- `_binding_for` (line 1714): replace the `outcome` parameter with
  `ticket_id: str, ticket_key: str, ticket_url: str`, and drop the `account_id`
  / `account_name` arguments it forwards. Keep the docstring's explanation of
  why `provider` and `project` are passed in rather than re-read.
- Its two call sites — `_tracker_import` (line 1808) and `_tracker_link`
  (line 1896) — pass `outcome.issue_id, outcome.key, outcome.url`.

**Modify** `tests/test_tracker_import.py`

- `write_binding` (line ~109): drop `"claimed-by"` from the fixture document.
- Line 152: replace `assert doc["claimed-by"] == {...}` with
  `assert "claimed-by" not in doc` — this is criterion 5.

**Modify** `tests/test_tracker_binding.py`

- The `claimed-by` block in the fixture YAML (line ~36) and the assertion at
  line ~229 that reads `entry["claimed-by"]["account-id"]`. The assertion is
  testing that `unlink_document` moves the binding keys into history; repoint it
  at a key that survives (`entry["ticket"]["key"]`) and add
  `assert "claimed-by" not in entry` — criterion 6.

**Modify** `tests/test_tracker_link.py`

- Line 61: `doc["claimed-by"]["account-id"] == A` becomes
  `"claimed-by" not in doc` — criterion 4.

**Proves it:** `pytest tests/test_tracker_import.py tests/test_tracker_binding.py
tests/test_tracker_link.py` green. `link` still claims at this point; only the
document shape changed.

---

## Task 2 — `link` stops claiming

**Modify** `tcw/work/cli.py`, `_tracker_link` (line 1846)

- Drop `claim` from the import list; keep `read_ticket`, `find_binding`,
  `binding_of`, `validate_part`, `unlinked_history`, `BINDING_SIDECAR`,
  `BindingProblem`, `Bound`, `Malformed`.
- Delete `outcome = claim(client, ticket)` (line 1887) and the
  `if not outcome.claimed: _print_refusal(...)` block (lines 1891–1893).
- Build the binding from `ticket` (a `TicketRead`) instead:
  `_binding_for(client.config.provider, project, ticket.issue_id, ticket.key,
  ticket.url, part, today, unlinked_history(...))`.
- Replace the success line (line 1904). `_claim_summary` says "claimed by this
  run" / "already assigned to you", neither of which is now true. Print
  `→ bound {slug} to {ticket.key} ({ticket.url}). The ticket is unchanged in the
  tracker.` — the mirror of `unlink`'s existing closing line (line 1943).
  `_claim_summary` stays; `_tracker_import` (line 1824) still uses it.
- Rewrite the function docstring: it currently says "claiming it by the same
  rules as `import`".
- Leave the local-write failure message, but drop "claimed {outcome.key}, but"
  from it — nothing was claimed, so re-running is not finishing a claim.

**Modify** `tests/test_tracker_link.py`

- Rename `test_link_claims_and_binds_without_touching_the_body` to
  `test_link_binds_without_touching_the_body` and replace
  `assert fake.tickets["10052"].assignee == A` with assertions that the ticket's
  status and assignee are unchanged and `fake.writes() == []` — criteria 1, 2, 3.
- Add `test_link_binds_a_ticket_someone_else_holds`: set
  `fake.tickets["10052"].assignee = "acct-b"`, link, assert exit 0, the binding
  is written, the assignee is still `acct-b`, and `fake.writes() == []` —
  criterion 10.
- **Delete** `test_link_refuses_a_ticket_someone_else_holds` (line 114). It pins
  the behaviour being removed; it is not edited into its own opposite.
- Add `test_link_refuses_an_unknown_ticket`: `link <slug> NOSUCH-1` exits 1 and
  writes no `tracker.yaml` — criterion 13. The fake raises 404 from `_find`.
- Update the module docstring (line 4), which says "`link` claims by exactly the
  rules `import` does".

**Proves it:** the four criteria above, plus the existing refusal tests
(criterion 12) still passing unchanged.

---

## Task 3 — `link` and `unlink` accept resolved items

**Modify** `tcw/work/cli.py`

- `_unresolved_item` (line 1830): delete the `RESOLVED_STATUSES` branch (lines
  1839–1842) and rename the function to `_item_or_reason`, since it no longer
  refuses unresolved-ness. Update its docstring and both call sites (line 1865
  in `_tracker_link`, line 1924 in `_tracker_unlink`).
- Drop the now-unused `RESOLVED_STATUSES` import if nothing else in the module
  uses it — line 731 (`_work_delete`) does, so it stays.

**Modify** `tests/test_tracker_link.py`

- **Delete** `test_link_refuses_a_resolved_item` (line 81) and
  `test_unlink_refuses_a_resolved_item` (line 143).
- Add `test_link_binds_a_resolved_item`, parametrized over both resolved
  statuses: link, assert exit 0, the binding exists and `fake.writes() == []` —
  criterion 7.
- Add `test_unlink_removes_a_binding_from_a_resolved_item`, same two statuses —
  criterion 8.
- Add `test_link_refuses_a_slug_that_does_not_exist`: exit 1, message contains
  "no such work item in this node", no file written — criterion 9.

There is no `discard` method. Both resolved statuses are reached through
`complete`, whose `resolution` chooses the destination (`resolution_status`,
`tcw/store/base.py:685-693`): `st.start(slug)` then
`st.complete(slug, "done", ["acked"])` lands in `completed`, and
`st.complete(slug, "wontfix", dod_ack=[], force=True)` lands in `discarded`
straight from `backlog` — the form `tests/test_capabilities.py:399` already
uses. `make_node` leaves retention at its default, which keeps both, so the
fixture needs no extra config.

**Proves it:** criteria 7, 8, 9.

---

## Task 4 — `tracker` subcommand help

**Modify** `tcw/work/cli.py`, lines 2233–2258

- Give each of the five `tracker` parsers
  `formatter_class=argparse.RawDescriptionHelpFormatter`, a `description=`, and
  an `epilog=` holding the examples.
- Each `description=` states every change the command makes in the tracker and
  in the work store. For `link` after task 2 that is: writes the binding
  sidecar, changes nothing in the tracker, and leaves the work item's status,
  owner and documents alone. For `import`: moves the ticket through the claim
  transition, assigns it, and creates a backlog item. For `unlink`: local only.
- Rewrite `link`'s `help=` string — currently "claim a ticket and bind an
  existing item to it" (line 2248).
- `help=` on every `tracker` positional: `slug` as "a work item slug in this
  node", `ticket` as "a ticket key, e.g. EX-123".
- Each `epilog=` lists the main refusals and one or two example invocations,
  including a `--part` example.

**Create** `tests/test_tracker_help.py`

- `test_tracker_help_describes_every_subcommand`: walk the `tracker` subparsers
  from `build_parser()` (`tcw/cli.py:467`) and assert each has a non-empty
  `description`, a non-empty `epilog`, and a `help=` on every positional —
  criterion 14.
- `test_tracker_link_help_does_not_promise_a_claim`: `link`'s `description` and
  `help` contain neither "claim" nor "assign" — criterion 15. Assert on the
  parser's attributes, not on captured `--help` output, so the test does not
  depend on terminal width.

**Proves it:** criteria 14, 15.

---

## Task 5 — A `help=` on every positional, CLI-wide

**Create** `tests/test_cli_help_coverage.py`

- `test_every_positional_has_help`: recursively walk `build_parser()` through
  every `argparse._SubParsersAction`, collect positional actions (no
  `option_strings`, not a subparsers action) with a falsy `help`, and assert the
  collection is empty. Put the offending `command path → dest` pairs in the
  assertion message so a future failure names them.

Write this test **first** and watch it fail with 46 entries — that count is the
spec's, obtained by the same walk, and a test that starts green means the walk
is wrong.

**Modify** `tcw/work/cli.py` (31), `tcw/taxonomy/cli.py` and
`tcw/capabilities/cli.py` (15 between those two)

- Add a one-line `help=` to each. Describe the argument, not the command: a
  `slug` is "the work item's slug", a `title` is "the item's title", a
  `stage_id` is "a lifecycle stage id (see `tcw work lifecycle`)".
- The 5 in the `tracker` group are already done by task 4; the test is what
  confirms nothing was missed.

**Proves it:** criterion 16, and the same test is the regression guard.

---

## Task 6 — Full-suite green

Run `pytest` and `tcw validate`. Fix anything the earlier tasks moved that is
not in the tracker or help files — `grep -rn "claimed-by" tests/ tcw/` must come
back empty, and `grep -rn "tracker link" README.md skills/ docs/` shows what
task 8 has to reach.

Two tests must still pass **unedited**, because `import` keeps claiming and this
item must not have touched it:
`test_a_ticket_assigned_to_someone_else_is_refused_naming_them`
(`tests/test_tracker_claim.py:99`) — criterion 11 — and
`test_a_ready_unassigned_ticket_is_transitioned_then_assigned`
(`tests/test_tracker_claim.py:67`). An edit to either means task 2 reached into
`claim`, which is a non-goal.

**Proves it:** criteria 11 and 18.

---

## Task 7 — Record the claiming hand-off on the sibling item

**Modify** `docs/work/backlog/2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker/`

This item's non-goal is that item's requirement, and prose in this folder does
not reach whoever picks that one up. It has no artifacts at all today, so write
its `initial-request.md` recording what this session decided: that `tcw work
start` claims the ticket a linked item is bound to, that this is the home for
claiming now that `link` does not claim, and that `tracker import` is the only
claiming path until it lands.

Also `tcw work edit 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker
--blocked-by 2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`
— a blocker rather than a sentence, because `start` refuses past one and prose
does not. If sync landed first, `start` would claim a ticket that `link` had
already claimed, which is the incoherent ordering.

**Proves it:** `tcw work show` on that item lists the blocker and an `R`
artifact; `tcw validate` passes.

---

## Task 8 — Documentation Sync

All four of this project's entries fire. Scope is concrete, so each is named.

**`README.md` — [Public-API].** Fires: the public CLI surface changes.

- Line 368, the command table comment: "take it for an item you already have"
  becomes wording that says it records a cross-reference and changes nothing in
  the tracker.
- § Taking a ticket (lines 433–444) folds `link` into `import`'s claim. Split
  them: `import` claims, `link` only records, and say that a ticket can be
  linked at any status including a finished item, and whoever holds it.
- The "Three limits to know" paragraph (line 446) gains the limit from the spec's
  Risks: a ticket held by a resolved item can be bound to a second, open item.

**`docs/release-notes/upcoming.md` — [Public-API].** Fires: user-visible
behaviour changes. Plain language, no module names. Must say that `link` no
longer moves or assigns the ticket, that it now works on finished items and on
tickets somebody else holds, and — explicitly, because the spec accepted it as a
risk — that nothing claims a linked ticket yet, so a ticket stays where it is
until you start it in the tracker yourself.

**`docs/changelogs/upcoming.md` — [Any-Code-Change].** Fires. Grouped entries:
_Changed_ for `link` no longer claiming and for `link`/`unlink` accepting
resolved items; _Removed_ for `claimed-by` leaving `tracker.yaml`; _Added_ for
the `tracker` help text and the CLI-wide positional `help=` sweep.

**`skills/tcw-work/…` — [Skill-Driven-Component].** Fires: the work component's
CLI surface changes.

- `skills/tcw-work/references/commands.md:93` — "claim a ticket for an existing
  unresolved item" is wrong twice over.
- Grep the rest of `skills/tcw-work/` for `tracker link` and for claim wording
  before deciding the file is the only site.

Written as **one pass over the finished diff**, after tasks 1–7, and committed
before `outcome.md`.

**Proves it:** criterion 17, and `tcw validate` (which resolves `tcw://` links)
still passing.

---

## Verification

Beyond the suite:

- **`--help` reads well to a human.** Criteria 14–15 assert that a description
  exists and that `link`'s omits "claim"; neither can tell whether the prose is
  any good. Run `tcw work tracker {list,show,import,link,unlink} --help` and read
  all five, checking in particular that someone who has never run `link` can tell
  which positional is the slug.
- **No live Jira call is made anywhere in this change**, and none is needed to
  verify it: every test runs against `tests/tracker_fake.py`. The behaviour that
  cannot be checked here is that a real Jira ticket is genuinely untouched by
  `link` — the fake's write log is the proxy. Worth one manual `link` against a
  real ticket before the version is cut, confirming its status and assignee in
  the Jira UI afterwards.
- **A binding written before this change still reads.** Not covered by a test,
  by decision (no migration). Confirm by hand: write a `tracker.yaml` carrying
  `claimed-by`, run `tcw work tracker unlink <slug> --reason x`, and check the
  command succeeds and the stale key is left in the document rather than
  crashing `unlink_document`.

## Notes

- Task 5 touches files outside `tcw/work/`, which is wider than the rest of this
  item. It is a one-line-per-argument change with a test that enforces it, and
  the spec's § 6 records why the sweep was not narrowed to the `tracker` group
  that reported it.
- No task changes `claim` itself, `import`'s claiming, or `tcw work start`. If
  one starts to, the spec's non-goals are the thing to re-read, not to work
  around.
