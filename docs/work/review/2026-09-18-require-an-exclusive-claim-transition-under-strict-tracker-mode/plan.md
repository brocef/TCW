# Plan: require an exclusive claim transition under strict tracker mode

Three tasks: make every strict test fixture valid under the new rule, add the rule
with its tests, then write the documentation. The suite is green at every task
boundary. Line numbers below were checked against `6d14ba1c`; the spec's citations
into `tcw/` all still hold at that commit.

The order matters for one reason. Once the rule exists, any strict fixture that
lacks the key becomes a broken configuration, and a test that expects a refusal
would still pass, now because the configuration is broken rather than because of
what it tests. So the fixtures are fixed **first**, while the key is still
optional and adding it changes nothing, and the rule lands on a suite that already
satisfies it.

## Setup for implementation

Implementation runs in a git worktree with a private virtual environment (a
separate Python install directory), so the shared editable install of `tcw` is
not re-pointed. `<scratch>` is the session's scratchpad directory and `W` the
worktree:

```sh
W=/Users/brian/Projects/TCW/.worktrees/2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode
python -m venv --system-site-packages <scratch>/venv
<scratch>/venv/bin/pip install -e "$W" --no-deps
<scratch>/venv/bin/pip install --ignore-installed pytest
```

Every test command in this plan is run with the virtual environment activated
(`source <scratch>/venv/bin/activate`) and the current directory set to `$W`, as
bare `pytest`, the way CI runs it. Confirm once that the worktree's source is what
runs: `python -c "import tcw; print(tcw.__file__)"` must print a path under `$W`.

## Task 1 — Give every strict fixture the key, while it is still optional

No production change. Adding the key cannot change what these tests exercise:
the only reader of `exclusive_claim_transition` is `tcw work tracker claim`
(`tcw/work/cli.py:3198`), and none of the tests below that turn strict mode on
call it (checked: the `tracker claim` calls in `tests/test_tracker_sync.py:588`,
`:2123`, `:2174` and `tests/test_tracker_pre_backlog.py:639` are all on
non-strict nodes). The value used everywhere is `Start Progress`, the fixtures'
existing `transitions.start`.

**The fixture sweep.** Found with
`grep -rn '"strict": True\|strict: true\|strict=True\|\["strict"\] = True\|set_tracker_key(.*"strict", True' tests/ evals/`
and by following each hit's helper, not copied from the spec. The spec's list
(Design 4) was built from a narrower pattern and missed every site marked
**new** below. `evals/` has none.

**Modifies:** `tests/test_tracker_strict.py`, `tests/test_tracker_validate.py`,
`tests/test_tracker_cli.py`, `tests/test_tracker_sync.py`,
`tests/test_tracker_comment.py`, `tests/test_tracker_pre_backlog.py`,
`tests/test_tracker_config.py`.

`tests/test_tracker_strict.py`:

- `strict_node` (`:32-36`) gains a keyword-only argument `claim_transition`,
  **with no default**, and sets `exclusive-claim-transition` to it (or leaves it
  unset when it is `None`). No default because this repository's implementation
  rules forbid a shared fixture from defaulting an axis the code branches on
  (`docs/lifecycle/implementation.md`, "Tests that cannot narrow a criterion"),
  and after Task 2 the parser branches on this key. Every caller passes it
  explicitly: the 13 calls at `:85`, `:99`, `:124` (the `strict` pytest fixture,
  which most strict gate tests use), `:145`, `:146`, `:214`, `:296`, `:305`,
  `:404`, `:545`, `:689`, `:747`, `:821`. All pass `"Start Progress"`, including
  the `strict=False` and parametrized ones at `:99`, `:545` and `:747`, so the
  key's presence never varies together with `strict`.
- `parsed(strict=True, statuses=STATUSES)` at `:57`, and the four strict cases of
  the parametrized list at `:68-75` (`no-active`, `no-completed`,
  `partial-discards`, `no-discarded`): add `"exclusive-claim-transition": "Start
  Progress"`, so each case is broken only by the status it names. `BASE`
  (`:24-29`) is **not** changed: `tests/test_tracker_comment.py` imports it and
  `parsed` for non-strict parsing, where the key has no business.
- **new** `:318`, `:752`, `:813`: `set_tracker_key(root, "strict", True)` on a node
  built without strict mode. Add
  `set_tracker_key(root, "exclusive-claim-transition", "Start Progress")` beside
  each. `:318` (`test_an_unbound_item_cannot_start_submit_or_complete_but_can_be_discarded`)
  is the clearest wrong-reason risk: it asserts only a strict refusal and an
  unchanged status, which a broken configuration also produces.
- `:411` and `:427` turn strict mode back on for a node made by `strict_node`,
  which already carries the key; `set_tracker_key` touches only `strict`, so
  nothing to add. Listed so the next reader does not re-check them.
- `:706-715`, `test_strict_survives_problems_that_come_from_an_ancestor`: add the
  key to `full`. Its first case asserts `tracker_config() is None` for a reason of
  its own (a parent block that is `"off"`); without the key that assertion gains
  a second reason and could survive losing the first.

`tests/test_tracker_validate.py`: `:92`, `:326`, `:333` — add the key to each
`set_tracker` mapping. All three assert **no** tracker problem, so they go red
loudly without it rather than passing wrongly.

`tests/test_tracker_cli.py`: `:1408`, `:1644`, and the conditional mapping at
`:1589` (used with `strict=True` at `:1603` and by the parametrized test at
`:1612`) — add the key inside the strict branch.

`tests/test_tracker_sync.py` — **new** `:1894` and `:1923`: each sets
`config["work"]["tracker"]["strict"] = True` in place; set
`config["work"]["tracker"]["exclusive-claim-transition"] = "Start Progress"`
beside it. (`test_tracker_sync.py` cannot import from `test_tracker_strict.py`,
which imports it, so these are written inline.)

`tests/test_tracker_comment.py` — **new** `:470`, and
`tests/test_tracker_pre_backlog.py` — **new** `:531`, `:546`: add the
`set_tracker_key(root, "exclusive-claim-transition", "Start Progress")` line beside
each `set_tracker_key(root, "strict", True)`.

`tests/test_tracker_config.py:151-157`: **remove**
`test_strict_is_reported_as_unknown_because_c4_owns_it`. Its docstring claims a
behaviour that has not existed since strict mode shipped, and it passes only
because the word "strict" appears in the missing-statuses problems. Removed rather
than rewritten because what a correct version would check is already checked:
that strict is an accepted key is `test_a_boolean_strict_is_accepted`
(`tests/test_tracker_validate.py:85`) and Task 2's criterion 2 test.

**Proves:** spec criterion 9, and the first half of criterion 8 (every strict
fixture sets the key). `pytest` over the whole suite is green, with the same
count as `main` minus the one removed test.

**Mutation:** none meaningful at this task; with the key optional, no test can
tell whether a fixture carries it. That is why the sweep is checked by Task 2's
sweep check instead, once the rule exists.

## Task 2 — The rule, and the tests that pin it

**Modifies:** `tcw/store/base.py`, `tcw/tracker/ownership.py`,
`tests/test_tracker_strict.py`.

In `parse_tracker_config` (`tcw/store/base.py`), inside `if strict:` at `:1455`,
after the `statuses.discarded` check (`:1463-1467`):

```python
        if "exclusive-claim-transition" not in raw:
            problems.append(STRICT_NEEDS_EXCLUSIVE_CLAIM)
```

with a module-level string beside `TRACKER_RENAMED_KEYS` (`:1273`), so the tests
can import one text rather than copy it:

```
work.tracker.exclusive-claim-transition: required when strict is true. Strict mode
promises that only one person can take a ticket, and a claim keeps that promise by
applying this transition, which your workflow will not apply to a ticket that has
already been taken. Name the transition that takes a ticket into work.
```

(one line in the code). `not in raw`, not `raw.get(...)`: a key written as `null`
or `""` is already reported by the check at `:1479-1485`, and one problem per key
is the rule the retired-key note follows (`:1426-1430`).

Comments: the one at `:1456-1457` ("Strict mode gates completing and discarding
against these") gains that it also needs the claim transition, and why; the one at
`:1479` ("Optional, so a lone `null`…") says "optional unless strict". The
`tcw/tracker/ownership.py` module docstring (`:26-31`), which says the key is
"opt-in", gains "(required under strict mode)". The `tracker claim` help text
(`tcw/work/cli.py:4118-4131`) stays: "unless the project names one" is true in
both modes.

**Adds**, in `tests/test_tracker_strict.py`'s configuration section, one test per
criterion:

1. Criterion 1: `parsed(strict=True, statuses=STATUSES)` with no key → `config is
   None`, `problems == [STRICT_NEEDS_EXCLUSIVE_CLAIM]`, and the text starts with
   `work.tracker.exclusive-claim-transition: required when strict is true` and
   contains `only one person` and `Name the transition`. The exact-list assertion
   is what stops it passing on another problem.
2. Criterion 2: the same with `exclusive-claim-transition="Start Progress"` →
   `problems == []` and `config.strict is True`.
3. Criterion 3: parametrized over no `strict` key and `strict=False`, no key →
   `problems == []`.
4. Criterion 4: parametrized over `None` and `""` under strict → exactly one
   problem naming the key, it contains `expected a non-empty string`, and it is
   not `STRICT_NEEDS_EXCLUSIVE_CLAIM`.
5. Criterion 5: `strict_node(..., strict=True, claim_transition=None)`;
   `validate(root)` contains
   `f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}"`, and `cli(root, "work",
   "list")[0] == 0`. Pattern: `test_validate_names_the_key_and_the_board_still_reads`
   (`:84`).
6. Criterion 6: `strict_node(..., strict=True, claim_transition="Start Progress")`,
   two bound items (`bound_item`), start one so it is active, **then**
   `set_tracker_key(root, "exclusive-claim-transition", None)`. Assert
   `tracker_strict() is True`, `tracker_config() is None`,
   `tracker_problems() == [f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}"]`;
   then `work start` on the backlog item and `work submit` on the active one each
   exit 1 with `REFUSED` and `tcw validate` in stderr, and each item's status is
   unchanged.
7. Criterion 7, beside `test_strict_survives_problems_that_come_from_an_ancestor`
   (`:704`), using `test_tracker_inheritance`'s `_chain`, `_store`, `COMPLETE`,
   `ABSENT` and `QUERY_ONLY`, with `full = {**COMPLETE, "statuses": STATUSES}`:
   - (a) root `{**full, "strict": True, "exclusive-claim-transition": "Start"}`,
     repo `ABSENT`, pkg `QUERY_ONLY` → `_store(pkg).tracker_problems() == []`;
   - (b) the same root without the key → the child's problems are exactly
     `[f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}"]`, attributed to the
     child's own file even though `strict` came from the parent (Design 2);
   - (c) root without the key, pkg `{**QUERY_ONLY, "exclusive-claim-transition":
     "Start"}` → the child's problems are `[]`;
   - (d) root without the key, pkg `{**QUERY_ONLY, "strict": False}` → the
     child's problems are `[]`.

**Proves:** spec criteria 1–7, and the second half of criterion 8.

**Mutations**, each applied, run, confirmed red for the stated reason, and
reverted:

- Delete the new check → tests 1, 5, 6 and 7(b) red.
- Make it fire whether or not the key is set (drop the `not in raw` test, keep
  `if strict:`) → tests 2, 7(a) and 7(c) red.
- Move it out of `if strict:` so it fires for every block without the key →
  tests 3 and 7(d) red. (The spec lists 7(d) under the previous mutation; it
  cannot go red there, because (d)'s child is not strict and the check stays
  inside `if strict:`. Corrected here.)
- Test presence with `raw.get("exclusive-claim-transition") is None` instead of
  `not in raw` → test 4's `None` case gets two problems → red.
- Criterion 8's second half: delete the `set_tracker_key(root, "timeout-seconds",
  -1)` line in `test_a_broken_strict_block_names_validate` (`:688`) and in
  `test_a_broken_strict_block_refuses_inbox_accept_even_with_ticket` (`:820`) →
  each red, because a valid strict block refuses `new` and `inbox accept` without
  naming `tcw validate` (`tcw/work/cli.py:521-524`). Restore both.
  `test_a_broken_strict_block_still_refuses_new` (`:304`) is deliberately not in
  this list: it asserts only a strict refusal, which a valid strict block also
  gives for `new`, so it stays green with or without its break. It guards the
  code (a broken block must not switch strict mode off), not the fixture, and is
  unaffected by this item.

**Sweep check**, the proof that Task 1 found every strict fixture: temporarily
replace the new `problems.append(...)` with
`raise AssertionError("strict block without exclusive-claim-transition")` and run
the whole suite. The only failures allowed are the tests that build a strict
block without the key on purpose: tests 1, 5, 6 and 7(b) above. Any other failure
is a strict fixture Task 1 missed; add the key to it and rerun. Revert the
`raise`.

## Task 3 — Capability statement and Documentation Sync

One pass over the finished diff.

**Modifies:** `docs/capabilities/work/require-tracker-backed-work/description.md`,
`skills/configure/references/tracker.md`, `docs/guide/jira.md`,
`docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`.

- **Capability** (criterion 12): in `description.md:36-37`, the sentence "`tcw
  validate` reports a strict block missing `statuses.active`,
  `statuses.completed`, or a `statuses.discarded` that covers every discard
  resolution" gains `work.tracker.exclusive-claim-transition`. Edited as a file;
  the capability stays `Supported`. Its sentences about how a claim proves it is
  exclusive are left for C4 (spec, "Capability changes").
- **Documentation** — per the block below.

**Proves:** criteria 10, 11 and 12, checked with
`grep -n -A8 "strict: true" skills/configure/references/tracker.md docs/guide/jira.md`
(every hit's YAML also names `exclusive-claim-transition`),
`head -20 docs/release-notes/upcoming.md`, and
`grep -n exclusive-claim-transition docs/capabilities/work/require-tracker-backed-work/description.md`.
`tcw validate` from `$W` (the virtual environment's `tcw`) reports nothing new.

**Mutation:** not applicable to prose; the Verification section covers reading
the texts together.

## Documentation Sync

| Entry | Trigger | Fires | Why, and what |
| --- | --- | --- | --- |
| `skills/configure/references/tracker.md` | Configuration-Key-Change | **yes** | The meaning of `work.tracker.exclusive-claim-transition` changes: required under strict mode. The strict paragraph (`:172-178`) adds the key to what strict mode needs; its YAML example (`:185-192`) sets it. The key's paragraph (`:84-92`) says "optional **except under strict mode**", qualifying "Leave it unset unless the project needs it". |
| `docs/guide/jira.md` | Tracker-Change | **yes** | A `work.tracker` key changes. The settings-table row (`:86`, "no") becomes "no; yes under strict mode". "Strict mode: no work without a ticket" (`:871-885`) adds the key to what strict mode needs and to its YAML example. "When two people claim at once" (`:431-434`, "why the setting is optional and off by default") gains the strict exception. None of these sentences says that `tcw work start` uses the key; that is C4's to add. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | Currently empty. Its **first** entry, marked as a breaking change for projects that set `strict: true`: strict mode now needs `work.tracker.exclusive-claim-transition`; `tcw validate` reports it missing, and strict commands refuse until it is set; set it to the transition your workflow uses to take a ticket into work, one it will not apply to a ticket someone already took; setting it means `tcw work tracker claim` applies that transition, which moves the ticket. C4's entry follows it and must not repeat any of this (C4 plan, Documentation Sync, already amended in `6d14ba1c`). |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Under Changed: `parse_tracker_config` requires `exclusive-claim-transition` when `strict` is true, reported as `STRICT_NEEDS_EXCLUSIVE_CLAIM`; a present-but-empty value keeps its existing problem. Under Internal: every strict test fixture now sets the key; `strict_node` takes it as a required argument; the stale `test_strict_is_reported_as_unknown_because_c4_owns_it` is removed. |
| `README.md` | Public-API | no | Its strict section (`README.md:524-537`) lists what strict mode refuses, not which keys it needs, and its configuration example is not strict. |
| `docs/guide/<topic>.md` | Guide-Topic-Change | no | The only other guide mentioning strict mode, `docs/guide/work.md:651`, links to `jira.md` and names no key. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | no | `skills/work/references/commands.md`'s strict section (`:236-258`) says a block with problems is refused and to run `tcw validate`, which stays true; no skill lists strict mode's required keys. Configuring belongs to `configure`, covered above. |

## Verification

What the suite cannot answer, to be checked by hand and recorded in `outcome.md`:

- **The texts read together.** The validate message, the two documentation
  entries and the release-note entry must each be true in a release that has this
  item and not C4 (spec Risk 2): none may say that `tcw work start` uses the key.
  Read all four side by side.
- **What an upgrading strict user sees**, once, in a throwaway node: a strict
  block without the key, then `tcw validate`, `tcw work start <slug>`, and
  `tcw work tracker list`. The first and third name the key; the second names
  `tcw validate`. Paste the three outputs into `outcome.md`.
- **The open question from the spec** (should the next version cut wait for C4?)
  is the user's, not implementation's. Raise it at verify.

## Notes

**Every acceptance criterion traces to a task.** 1–7 → Task 2. 8 → Task 1
(fixtures) and Task 2 (the `timeout-seconds` mutations and the sweep check).
9 → Task 1. 10, 11 → Task 3 and Documentation Sync. 12 → Task 3.

**Where the spec was incomplete against the code.**

- Design 4's fixture list missed eight strict sites that turn strict mode on with
  `set_tracker_key(root, "strict", True)` or `config[...]["strict"] = True`:
  `tests/test_tracker_strict.py:318`, `:752`, `:813`,
  `tests/test_tracker_sync.py:1894`, `:1923`, `tests/test_tracker_comment.py:470`,
  `tests/test_tracker_pre_backlog.py:531`, `:546`. Its grep pattern matched only
  literal `"strict": True`. All are in Task 1.
- Criterion 7's mutation list puts 7(d) under "fire whether or not the key is
  set"; 7(d)'s child is not strict, so only moving the check out of `if strict:`
  turns it red. Task 2 lists the corrected mutation.
- Design 4 said to add the key to `BASE`; this plan adds it at the strict call
  sites instead, because `BASE` is also imported for non-strict parsing by
  `tests/test_tracker_comment.py`.

Neither changes the design or a criterion's substance, so the spec is not
reopened.

**Dependencies.** This item blocks C4
(`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`), already recorded in
C4's `state.yaml`. Nothing blocks this item.
