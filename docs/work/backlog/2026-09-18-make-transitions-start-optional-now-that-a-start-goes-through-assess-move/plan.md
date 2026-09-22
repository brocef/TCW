# Plan — Make `transitions.start` optional now that a start goes through `assess_move`

Five tasks, ordered so `pytest` is green at every commit boundary. Each code
change ships in the same commit as the test edits it forces; a task that would
leave the suite red for the next one has been merged into it.

Task numbering matches nothing in the spec by accident — each task lists the
spec's design **rules** it implements, the **acceptance criteria** it proves, and
the **mutation** (the deliberate code break) each new or changed test must go red
under. Mutations are applied one at a time, confirmed red, and reverted; the
reason a test went red is read, not assumed.

## Task 1 — make `transitions` and `transitions.start` optional

Implements design rules 1 and 3 (the `base.py` half). Proves criteria 1, 2, 3,
4, 5, 16 and the `base.py` half of 17.

**Modify `tcw/store/base.py`:**

1. Replace the unconditional call at `:1443`:

   ```python
   transitions = nested("transitions", TRACKER_TRANSITION_KEYS)
   ```

   with the shape `exclusive-claim-transition` already uses at `:1497-1501`:

   ```python
   if "transitions" in raw and raw["transitions"] is None:
       problems.append("work.tracker.transitions: expected a mapping, got NoneType")
   transitions = (nested("transitions", TRACKER_TRANSITION_KEYS)
                  if raw.get("transitions") is not None else {})
   ```

2. Delete `:1503-1508` — the comment about `start` being the one required move
   and the `if "start" not in transitions:` check. Keep `:1509`
   (`start = move_transitions.get("start", "")`) exactly as it is.
3. Rewrite the comment at `:1263-1266` so it no longer calls `start` the
   exception. What stays true: a move with no name here keeps the status-derived
   rule, and an unknown key is reported rather than ignored.
4. Rewrite `_parse_tracker_transitions`' docstring at `:1693-1695`, dropping
   "That `start` is required is the caller's check, not this one's". What stays:
   all five keys are parsed uniformly, and an absent key leaves that move on the
   status-derived rule.
5. Rewrite `attribute_tracker_problems`' docstring at `:1859-1862`, which uses
   `transitions.start: required` as its worked example of a problem about a key
   nobody set. That message no longer exists. Use one the parser still produces —
   `credentials.token-env: required` under a `credentials` mapping an ancestor
   supplied.

**Modify `tests/test_tracker_config.py`:**

6. `test_a_missing_required_key_is_reported_by_name` — drop the `transitions`
   parameter. The other required keys are unaffected.
7. `test_a_missing_start_transition_is_reported_by_name` — replace with
   `test_a_tracker_block_with_no_transitions_validates`, parametrized over the
   two absences: `transitions` missing from the block entirely, and
   `transitions: {}`. Each asserts `problems == []`,
   `config.move_transitions == {}` and `config.start_transition == ""`.
   (Criteria 1 and 2.)
8. Add `test_a_null_transitions_block_is_a_wrong_value_not_a_missing_one`:
   `transitions: None` gives no config, one problem
   `work.tracker.transitions: expected a mapping, got NoneType`, and no problem
   ending `work.tracker.transitions: required`. (Criterion 3.)
9. `test_the_retired_claim_key_names_its_replacement` — keep the three
   assertions about the `transitions.claim` problem; replace the final
   `assert "work.tracker.transitions.start: required" in problems` with its
   negation, so the retired-key message is proved to stand alone. (Criterion 5.)
10. `test_only_the_required_start_transition_is_there_by_default` — rename to
    `test_only_the_named_moves_are_on_the_config` and drop "`start` is not
    optional" from the docstring. The assertion
    (`move_transitions == {"start": "Start Progress"}` for `VALID`) is unchanged.
11. `test_a_present_but_unusable_start_transition_is_reported` — unchanged, and
    reread to confirm its docstring still holds now that "only an absent key is
    the caller's `required` check" describes a check that no longer exists.
    Reword that sentence. (Criterion 4.)
12. Add `test_a_block_with_an_exclusive_claim_and_no_transitions_validates`:
    `exclusive-claim-transition` set, `transitions` omitted, `problems == []`.
    Together with the existing `strict`-without-the-key test this is criterion 16.

**Modify `tests/test_tracker_inheritance.py`:**

13. `test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node`
    and `test_a_nested_required_key_nobody_set_is_blamed_on_the_child` — both
    use `transitions.start: required` to demonstrate the attribution rule.
    Re-point both at `credentials.token-env`: the ancestor supplies
    `credentials` with only `email-env`, and the missing `token-env` must be
    blamed on the node being checked. (Criterion 17.)
14. `test_a_retired_key_in_a_parent_names_the_parents_file` — keep the
    attribution assertions; drop the final `"pkg:
    work.tracker.transitions.start: required" in problems`.

**Mutations, each applied alone:**

| Mutation | Must redden |
| -------- | ----------- |
| restore `if "start" not in transitions: problems.append("work.tracker.transitions.start: required")` | criteria 1, 2, 5 |
| restore the unconditional `nested("transitions", …)` | criterion 1 |
| delete the `"transitions" in raw and raw["transitions"] is None` guard | criterion 3 |
| remove `"start"` from `TRACKER_MOVE_TRANSITION_KEYS` | criterion 4 |
| delete the `problems.append(STRICT_NEEDS_EXCLUSIVE_CLAIM)` at `:1483` | criterion 16 |
| in `attribute_tracker_problems`, match a problem on the nearest enclosing recorded mapping rather than the longest recorded key-path prefix | criterion 17 |

**Green at the boundary:** the six tests measured to fail under this change (the
table in the spec's design rule 6) are all edited here, except the one in
`tests/test_tracker_sync.py`, which belongs to task 2 and does not depend on this
task's source edits.

Run before committing: `pytest tests/test_tracker_config.py
tests/test_tracker_inheritance.py tests/test_tracker_validate.py
tests/test_tracker_strict.py`.

## Task 2 — one removal message for all five moves

Implements design rules 2 and 3 (the `sync.py` half). Proves criterion 15.

**Modify `tcw/tracker/sync.py`:**

1. Delete the comment and the conditional at `:276-281` and fold the advice into
   the message, so the refusal always ends
   `Fix work.tracker.transitions.<move>, or remove it to let TCW find the
   transition itself.` The `drop` variable goes with it.

**Modify `tests/test_tracker_sync.py`:**

2. `test_only_a_removable_transition_key_is_offered_for_removal` (`:1530-1545`)
   — rename to `test_every_transition_key_is_offered_for_removal`, parametrize
   over all five moves, assert the removal sentence is present for each, and
   rewrite the docstring, which currently explains why `start` is the exception.

**Mutation:** restore `drop = ("" if move == "start" else ", or remove it to let
TCW find the transition itself")`. The `start` parameter must go red; a
parametrization that only covers `complete` would stay green, which is the check
on the test itself.

Run before committing: `pytest tests/test_tracker_sync.py`.

## Task 3 — prove a start with no configured name derives, on every path

Implements no design rule; it completes C4's acceptance criterion 14, which
became testable at task 1. Proves criteria 6, 7, 8 and 9.

No source change. If any part of this task needs one, stop — it means the spec's
central claim (that a start already reaches the status-derived rule) is wrong,
and the item returns to `spec`.

**Modify `tests/test_tracker_sync.py`:**

1. `make_node` (`:87-116`) gains a keyword argument
   `transitions: dict | None = {"start": "Start Progress"}`, where `None` omits
   the key from the tracker block entirely. The default keeps every existing
   caller unchanged.
2. Add a module-level workflow beside the existing fixtures, named
   `TWO_ROUTES_IN`: `"To Do"` offers `("21", "Start Progress", "In Progress")`
   **and** `("22", "Fast Track", "In Progress")` plus the usual discards;
   the remaining statuses are `SYNC`'s. Two routes into `statuses.active` is what
   makes a configured name load-bearing — on `SYNC` the named and derived answers
   are the same transition id, so neither rule can be told from the other.
3. `test_a_start_posts_the_one_transition_transitions_start_names` (`:2491`) —
   re-point at `TWO_ROUTES_IN` with `transitions.start: Start Progress` set.
   Assert exit 0, exactly one POST ending `/transitions`, and
   `fake.applied == ["21"]`. (Criterion 6.)
4. Add `test_a_start_with_no_configured_name_derives_from_the_target_status`:
   `make_node(..., transitions=None)` on the ordinary `SYNC` workflow. Assert
   exit 0, exactly one POST, `fake.applied == ["21"]`, and the ticket assigned to
   the running account. (Criterion 7.)
5. Add `test_a_start_with_no_configured_name_consults_no_name`:
   `transitions=None` on `TWO_ROUTES_IN`. Assert non-zero exit,
   `fake.applied == []`, the item's local status is `active`, and the sync
   record is `state: conflicting` with a reason containing
   `offers more than one transition to 'In Progress' (ids 21, 22); TCW will not
   guess which`. (Criterion 8.) This is the criterion that distinguishes the two
   rules: a consulted name would have resolved the ambiguity.
6. Add three tests, one per start-bearing code path, each on `SYNC` with
   `transitions=None`, each asserting the single transition leading to
   `statuses.active` is applied and nothing else is posted. (Criterion 9.)
   - (a) the ordinary lifecycle start through `tcw work start`
     (`tcw/tracker/sync.py:872-874`) — this is task 3.4, reused, not repeated.
   - (b) the owed-start catch-up before a later move
     (`tcw/tracker/sync.py:823-825`): build it the way
     `test_a_stale_record_does_not_strand_an_item_that_has_moved_on` (`:1565`)
     does — `with_record(node, slug, {"move": "start", "claim": "owed", …})` on
     an item that has not finished — and drive it with
     `tcw work tracker sync <slug>`.
   - (c) a ladder hop onto the active rung inside `walk()`
     (`tcw/tracker/sync.py:549-551`, `:557-559`), where
     `MOVE_ONTO["active"] == "start"`: build it with the existing
     `legacy_catch_up` helper (`:1357`), which writes the `catch-up: true`
     binding an older `link --sync-status` left behind, on the `STRICT_LADDER`
     workflow so the walk really takes more than one hop.

**Mutation:** make the status-derived tail at `tcw/tracker/sync.py:298-307`
return `CONFLICTING` instead of `("apply", leads[0])`. This one mutation must
turn **all** of 3.4 and 3.6(b) and 3.6(c) red. A path that stays green is a path
the test does not actually reach, and the fixture is wrong — this is the exact
failure mode that produced two rounds of partial fixes earlier in this epic.

Second mutation, for criterion 6: delete the `if named_transition:` block at
`tcw/tracker/sync.py:271-297`. Test 3.3 must go red (the start refuses as
ambiguous) and test 3.5 must stay green.

Third mutation, for criterion 8: make `transition_name` return
`"Start Progress"` for `move == "start"` when nothing is configured. Test 3.5
must go red.

Run before committing: `pytest tests/test_tracker_sync.py
tests/test_tracker_hold.py tests/test_tracker_replay.py`.

## Task 4 — the three readers that have no status to derive from

Implements design rules 4 and 5. Proves criteria 10, 11, 12, 13 and 14.

**Modify `tcw/tracker/claim.py`:**

1. Add a verdict constant beside the existing ones (`:28-51`):

   ```python
   # The project named no start transition. Distinct from CLAIM_NOT_OFFERED,
   # which is about a name this ticket does not offer.
   NOT_CONFIGURED = "no start transition configured"
   ```

2. At the top of `assess` (`:73`), before `wanted = _normalize(...)`, return
   early on a blank name:

   ```python
   if not claim_transition.strip():
       return Assessment(claimable=NOT_CLAIMABLE, exclusivity=NOT_DETERMINED,
                         verdict=NOT_CONFIGURED,
                         detail="work.tracker.transitions.start names no transition, "
                                "so there is none to claim this ticket through.")
   ```

   The guard goes here, not in each caller: all three readers named in the spec
   reach `assess`, and one guard in the shared function is smaller than three in
   callers.

**Modify `tcw/tracker/intake.py`:**

3. Inside `_claim_from`'s `if not matches:` block (`:675-682`), **after** the
   existing `ticket.assignee_id == ticket.me_id` branch that returns row `1e`
   and **before** the row `1f` refusal, add row `1d`:

   ```python
   if assessment.verdict == NOT_CONFIGURED:
       return refused("1d", f"{key} cannot be claimed: "
                            f"work.tracker.transitions.start is not set, and this "
                            f"command claims through it. Set it, or take the ticket "
                            f"with `tcw work tracker claim` and bind an item to it "
                            f"with `tcw work tracker link`.")
   ```

   Import `NOT_CONFIGURED` alongside the existing `AMBIGUOUS` import at `:644`.
   **The order is load-bearing:** row `1e` must keep winning, or the documented
   re-run recovery (`tcw/work/cli.py:2532-2536`) and the
   `tracker claim` → `import` sequence both break.

**No change to `tcw/work/cli.py`.** `_print_ticket` (`:2458-2474`) already
prints `result.detail` on a `note:` line, so the new wording reaches
`tcw work tracker show` and `tcw work inbox show` with no edit. Task 4.8 is what
proves that, rather than a reviewer's reading of it.

**Modify `tests/test_tracker_claimability.py`:**

4. Add `test_an_unset_start_transition_is_its_own_verdict`: `assess("")` and
   `assess("   ")` on a ticket offering transitions each return
   `verdict == NOT_CONFIGURED`, `exclusivity == NOT_DETERMINED`, and a detail
   that does not contain `is ''`.

**Modify `tests/test_tracker_import.py`:**

5. Add a helper beside `_tracker` (`:29-36`) that builds the same block with the
   `transitions` key omitted.
6. Add `test_import_with_no_start_transition_names_the_key`: an unassigned,
   unclaimed ticket, no `transitions` key. Assert non-zero exit,
   `work.tracker.transitions.start` in stderr, `does not offer ''` **not** in
   stderr, no item created, `fake.applied == []`, and the ticket still
   unassigned. (Criterion 10.)
7. Add `test_inbox_accept_with_no_start_transition_refuses_the_same_way` —
   the same assertions through `tcw work inbox accept <ticket>`, which is the
   same function (`tcw/work/cli.py:851` → `_tracker_import`). (Criterion 11.)
8. Add `test_import_of_a_ticket_already_held_needs_no_start_transition`: the
   ticket is already assigned to the running account, no `transitions` key.
   Assert exit 0 and one bound item created — row `1e`, unchanged.
   (Criterion 12.)

**Modify `tests/test_tracker_strict.py`:**

9. Add `test_strict_import_of_a_held_ticket_needs_no_start_transition`:
   `strict: true`, `exclusive-claim-transition` set, no `transitions` key,
   ticket already assigned to the running account and in `statuses.active`.
   Assert exit 0 — `claim_refusal` does not stop it. (Criterion 13.)

**Modify `tests/test_tracker_cli.py`:**

10. Add `test_show_says_the_start_transition_is_unset_rather_than_wrong`:
    `tcw work tracker show <ticket>` with no `transitions` key exits 0, its
    `note:` line says the key names no transition, and the output does not
    contain `work.tracker.transitions.start is ''`. (Criterion 14.)

**Mutations:**

| Mutation | Must redden |
| -------- | ----------- |
| remove the row `1d` branch from `_claim_from` | criteria 10, 11 |
| move the row `1d` branch above the row `1e` branch | criterion 12 |
| make `assess`'s empty-name return carry `exclusivity=NOT_EXCLUSIVE` | criterion 13 |
| remove `assess`'s empty-name early return | criteria 14 and 4.4 |

Run before committing: `pytest tests/test_tracker_claimability.py
tests/test_tracker_import.py tests/test_tracker_strict.py
tests/test_tracker_cli.py tests/test_tracker_claim.py
tests/test_tracker_pre_backlog.py`.

## Task 5 — Documentation Sync

Run last, over the finished diff, as the stage instructions require. Every
entry from `tcw work docs` is evaluated below, marked **fires** or **does not
fire** with the reason.

### `README.md` — [Public-API] — **does not fire**

Trigger: the public CLI surface or user-facing behavior changes. No command,
flag or argument changes. The README's Jira sample (`:554`) sets
`transitions: { start: Start Progress }`, which stays valid and stays correct.
`grep -c required README.md` is `0`: the README nowhere states which tracker
keys are required, so nothing in it becomes false.

### `docs/guide/jira.md` — [Tracker-Change] — **fires**

A `work.tracker` key changes meaning and a `tcw work tracker` command's
behavior changes. Edit:

- `:84` — the key table row for `transitions.start`: `required` becomes `no`,
  with the sentence that naming it is still the right answer on a workflow with
  two routes into the active status.
- `:85` — the row for the four optional moves now covers all five; merge or
  reword so the table does not still separate them by requiredness.
- `:124-133` — "Inherited settings" says the claim transition is one of the
  settings usually shared from a parent. Still true, no longer required.
- `:248` — the `import` steps: step 2 says it "applies the transition named in
  `transitions.start`". Add what happens when the key is not set — `import`
  refuses and names it — since `import` is the one command that still needs it.
- `:851-875` — "Naming a transition" (the sentence at `:869-872`): delete "`start` is the exception: it is
  required…" and say instead that `import` still needs it.
- `:877-899` — "Renaming the start transition": the sample `tcw validate` output
  includes `work.tracker.transitions.start: required` at `:893`, which the parser
  no longer emits. Remove that line; the retired-key line stays.
- `:115-120` — "TCW cannot tell you that `transitions.start` is misspelled":
  still true; add that TCW now can tell you it is unset.

### `docs/guide/<topic>.md` — [Guide-Topic-Change] — **does not fire**

`docs/guide/jira.md` is excluded by this entry's own wording and handled above.
Checked every other guide: `grep -l work.tracker docs/guide/*.md` returns only
`jira.md` and `work.md`, and `work.md`'s three mentions (`:225`, `:228`,
`:647-649`) are `inbox-query`, `pre-backlog` and a list of command names, none
of which changes. `docs/guide/configuration.md:23` and `docs/guide/work.md:149`
show a `transitions:` block, but it is `work.lifecycle.transitions` — a
different key that happens to end in the same word.

### `docs/release-notes/upcoming.md` — [Public-API] — **fires**

Add, in plain language: `transitions.start` is now optional; a project that does
not set it has TCW work the transition out from the status the start is heading
for, the same way the other four moves already did; a project that does set it
sees no change at all; and `tcw work tracker import` still needs the name,
because it claims a ticket through that transition, and now says so plainly when
it is missing. Name the one case where setting it is still the right answer: a
workflow with two transitions into the active status.

### `docs/changelogs/upcoming.md` — [Any-Code-Change] — **fires**

Grouped entries:

- **Changed** — `work.tracker.transitions` and `work.tracker.transitions.start`
  are both optional; the two required checks in `parse_tracker_config` are gone.
  `transitions: null` is now reported as a wrong value rather than a missing
  required key.
- **Changed** — the "offers no transition named" refusal now offers removal for
  all five moves, `start` included.
- **Added** — `claim.assess` has a `NOT_CONFIGURED` verdict for an unset start
  transition, and `intake._claim_from` a row `1d` refusal that names the key.
- **Internal** — the comments in `tcw/store/base.py` and `tcw/tracker/sync.py`
  that stated `start` had no status-derived fallback, which stopped being true
  when the lifecycle moves were composed from claim and sync.

### `skills/<component>/SKILL.md` — [Skill-Driven-Component] — **fires**

The `work` component's CLI behavior changes, so the `work` skill must follow.
`skills/work/SKILL.md` itself needs no edit — `grep -n transitions` on it finds
only the lifecycle move list and a note about committing transitions, neither
affected. The file to edit is `skills/work/references/commands.md`:

- `:130-135` — what `show` reports: add that an unset `transitions.start` is
  reported as unset rather than as a name the ticket does not offer.
- `:219` — "a catch-up, `import`, `inbox accept` — first applies the
  transition": add that `import` and `inbox accept` refuse when no transition is
  named, and that a lifecycle start does not, because it derives one.
- `:270` — the strict-mode refusal table row for `tracker import`: unchanged in
  substance, reread against task 4.9.
- `:331` — "Neither `list` nor `show` detects a wrong `transitions.start`
  value": still true, and now sits beside the unset case.

`skills/work/references/transitions.md` needs no edit: it describes the
lifecycle moves and worktrees, and names no tracker transition key.

### `skills/configure/references/<document>.md` — [Configuration-Key-Change] — **fires**

A key in `tcw-config.yaml` changes meaning, from required to optional. Edit
`skills/configure/references/tracker.md`:

- `:5` — `import` "claims a ticket through the workflow transition named in
  `transitions.start`": add that it refuses when the key is not set.
- `:35-41` — the required/optional key list moves `transitions.start` to the
  optional side.
- `:52-55` — what `transitions.start` is: keep, and add that it is optional.
- `:63-71` — "`start` is the exception and is still required by `tcw validate`
  … making it optional is a separate change": that separate change is this one.
  Replace with the uniform rule: a move with no entry derives its transition
  from the status, and `import` is the one command that still needs the name.
- `:79-81` — the sample `tcw validate` output drops the
  `transitions.start: required` line.

The other `skills/configure/references/*.md` documents are untouched: no other
configuration key changes.

**Finally**, re-run `tcw work docs` and confirm no entry was added to
`tcw-config.yaml` between the plan and the implementation.

## Verification

The suite is the main instrument; these are the checks it cannot make.

**Environment.** Implementation runs in a git worktree with its own virtual
environment, so the primary checkout's editable install is never re-pointed:

```sh
git -C /Users/brian/Projects/TCW worktree add \
    /Users/brian/Projects/TCW/.worktrees/<slug> -b work/<slug>
python3 -m venv /Users/brian/Projects/TCW/.worktrees/<slug>/.venv
/Users/brian/Projects/TCW/.worktrees/<slug>/.venv/bin/pip install \
    -e '/Users/brian/Projects/TCW/.worktrees/<slug>[dev]'
```

Every command below runs with the working directory set to the worktree root
and that virtual environment on `PATH`, and uses **bare `pytest`**, which is
what continuous integration runs — `python -m pytest` puts the current directory
on the import path and can pass where bare `pytest` fails.

**1. The full suite, bare, after every task.**

```sh
pytest -q
```

**2. Every mutation, one at a time.** For each row of every task's mutation
table: apply it, run the named tests, confirm they go red, **read why they went
red**, and revert. A mutation that reddens a test for the wrong reason has not
been checked. Record the result per mutation; a mutation that leaves its
criterion green is a finding, not a formality.

**3. This repository's own configuration still validates**, with
`transitions.start: Start` (`tcw-config.yaml:12-13`) untouched:

```sh
tcw validate
git diff --stat -- tcw-config.yaml     # must be empty
```

**4. The two commands the suite drives only through a fake.** The tests use
`FakeJira`; nothing here contacts a real Jira, and nothing in this item may.
Confirm by reading, not by running: `grep -rn "atlassian.net\|https://" tests/`
returns only `example.invalid` and documentation samples.

**5. The comments and docstrings changed in tasks 1 and 2 are read back against
the code they sit above.** No test can catch a comment that still says `start`
is required. The three in the spec's design rule 3, plus
`attribute_tracker_problems`' docstring, are reread one by one after the code
change lands.

**6. Grep for the sentence that must no longer appear anywhere**:

```sh
grep -rn "transitions.start: required" . --exclude-dir=.git --exclude-dir=docs/work
```

Remaining hits must be only in `docs/changelogs/v2.4.0.md` and
`docs/release-notes/` — historical records of a released version, which are not
edited.

**7. The `--worktree` teardown.** Before `tcw work complete`, remove the
worktree's virtual environment and run `complete` from the primary checkout,
which is still on its own editable install and was never re-pointed.

## Notes

- **Nothing in this plan changes `work.tracker.exclusive-claim-transition`.**
  Strict mode still requires it, and criterion 16 exists to hold that.
- Task 3 is the one task with no source change. If it turns out to need one,
  that is the signal to stop and return to `spec`: the item's central claim
  would be wrong.
- The measurements the spec quotes were taken by applying task 1's source change
  to a scratch copy of the tree, running probes, and restoring the tree. Task 1
  is therefore the least uncertain task here, and task 4 the most: its two source
  edits were designed from reading, and only the defects they fix were measured.
- This is the last open child of
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. The
  version cut covering the whole epic follows it, so
  `docs/{changelogs,release-notes}/upcoming.md` are written but not rotated here.
