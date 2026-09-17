# Outcome: Retire the claim transition key into a named start transition

## What shipped

### Task 1 — `start` replaces `claim` in the configuration, end to end (`7519a147`)

One commit, as the plan said it had to be. `TRACKER_TRANSITION_KEYS` drops
`claim` and gains `start`; `TRACKER_MOVE_TRANSITION_KEYS` gains `"start"`, so
`_parse_tracker_transitions` handles all five keys in one loop and
`move_transitions["start"]` holds the name. `TrackerConfig.claim_transition`
became `start_transition`, carrying the same string, and its four readers
(`tcw/tracker/intake.py`, `tcw/tracker/sync.py` twice, `tcw/work/cli.py`)
changed by name only.

The key stays required. The check moved from `nested_str` to
`if "start" not in transitions`, so a wrong *value* is reported by the loop with
the wording its four siblings get and an absent *key* is reported by the caller.

`TRACKER_RENAMED_KEYS` is new: a mapping from a retired key path to what
replaced it, consulted inside `nested`'s unknown-key loop. Putting it there
rather than after the call is what keeps a retired key to one problem instead of
that plus "unknown key".

Also in this commit, because they name the key or the reason for it:
`tcw/tracker/claim.py`'s `CLAIM_NOT_OFFERED` message, the `MOVE_ONTO` comment in
`tcw/tracker/sync.py`, `tcw/tracker/ownership.py`'s docstring,
`attribute_tracker_problems`'s docstring example, this repository's own
`tcw-config.yaml`, and the eleven test modules that constructed a
`TrackerConfig` or asserted on the old key.

### Correcting the spec and plan (`f21c7c08`)

See "What the plan and spec got wrong" below. Committed before the tests it
changed the shape of, so the artifacts never described work that was not done.

### Task 2 — the new assertions (`946655b6`)

Four, in `tests/test_tracker_config.py` and `tests/test_tracker_inheritance.py`.
Each was broken before it was trusted; the mutations are listed below. The
docstring at `tests/test_tracker_inheritance.py:225` that still said "nobody set
`claim`" was corrected in the same commit.

### Task 3 — this repository's own configuration

No commit; nothing to change beyond Task 1's one-word edit. Verified by hand,
below.

### Task 4 — Documentation Sync (`a47e1eb4`)

Six entries fired and two did not, exactly as the plan predicted. The
`docs/guide/jira.md` and `skills/configure/references/tracker.md` changes each
gained a migration section that was not in the plan's task list but follows from
its own reasoning: a rename every tracker-backed project must make needs a place
that says so, not only a table row that has quietly changed.

## Test result

The full suite, from the worktree, with the private virtual environment first on
`PATH` so anything shelling out to the `tcw` console script got the worktree's
code. Redirected to a file and read from the file:

```
$ PATH="/tmp/c3-venv/bin:$PATH" python -m pytest -q > /tmp/c3-suite-final.txt 2>&1
$ tail -1 /tmp/c3-suite-final.txt
3746 passed in 828.19s (0:13:48)
```

The rename commit was run the same way before it was committed:
`3739 passed in 911.22s (0:15:11)`. The seven-test difference is Task 2's four
new assertions, three of which are parametrized into four cases.

`tests/fixtures/prompt_fallback/capture.py` was not run. It re-baselines its
fixture from whatever `tcw` is on `PATH`, and with a second worktree active a
wrong pin would have rewritten the fixture silently.

## Mutations run, and what went red

Every mutation was applied to the source, the test run, the failure read, and
the source restored from a copy taken before the first one.

| # | Mutation | Went red |
| - | -------- | -------- |
| 1 | `TRACKER_MOVE_TRANSITION_KEYS` back to the four siblings, without `"start"` | `test_the_start_transition_is_a_move_transition_like_its_siblings`, on `assert config.start_transition == "Start Progress"` — `AssertionError: assert '' == 'Start Progress'` |
| 1b | `start = move_transitions.pop("start", "")` instead of `.get` — the field stays right, the dictionary entry goes | the same test, one line further on: `KeyError: 'start'` on `config.move_transitions["start"]` |
| 2 | `TRACKER_RENAMED_KEYS = {}` | `test_the_retired_claim_key_names_its_replacement` and `test_a_retired_key_in_a_parent_names_the_parents_file`, the second reporting `['root: work.tracker.transitions.claim: unknown key']` — the generic message, with no replacement named |
| 3 | delete the `if "start" not in transitions` membership test | `test_a_missing_start_transition_is_reported_by_name` and `test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node`, the second showing the problem list was empty: the block parsed clean with no start transition at all |
| 4 | `_parse_tracker_transitions`'s `name()` returns `str(value).strip()` instead of reporting a bad value | all four cases of `test_a_present_but_unusable_start_transition_is_reported`, and three of the pre-existing `test_a_malformed_transition_is_a_problem` — `assert config is None` failed with a config whose discard transition was the string `'7'` |
| 5b | report a retired key under its enclosing mapping's path: `work.tracker.transitions: claim renamed to …` | `test_a_retired_key_in_a_parent_names_the_parents_file` alone, with the message present but attributed and spelled so that nothing matched `transitions.claim` |

Mutation 1 is recorded separately from 1b because 1 alone did not prove what the
test was for. It goes red on the first of the test's three assertions, which a
plain rename would also satisfy; 1b isolates the assertion that distinguishes
"renamed the key" from "made it an ordinary move key", which is the whole point
of the item.

A sixth mutation was tried and rejected as worthless. Changing
`attribute_tracker_problems`'s match from the exact key path to any prefix broke
thirteen tests across the module, so the new one going red proved nothing about
the new one. 5b replaced it: a mistake someone could actually make, breaking
that test and no other.

Mutation 4 was also run once in a form that did not apply — the `assert`
in the mutation script fired because the text I matched appears twice, once for
statuses and once for transitions — and the test then passed on an unmutated
tree. That pass is not evidence and is not counted; the run in the table is the
one that applied.

## Verified by hand

1. **This repository's own configuration.** `tcw validate` from the worktree,
   through the private virtual environment, printed `validate OK` and exited 0.
   The code it loaded was confirmed first:
   `/tmp/c3-venv/bin/python -c "import tcw; print(tcw.__file__)"` named the
   worktree. That check matters here — the primary checkout still has
   `transitions: {claim: Start}`, so the old code would have called the
   worktree's `start:` an unknown key and failed.
2. **The message an upgrading user sees.** A throwaway node at
   `/tmp/c3-oldnode`, with a `tcw-config.yaml` still carrying
   `transitions: {claim: Start Progress}`:

   ```
   tcw-config.yaml: work.tracker.transitions.claim: renamed to work.tracker.transitions.start, the transition the start move applies, alongside submit, rework, complete and discard
   tcw-config.yaml: work.tracker.transitions.start: required
   2 problem(s).
   ```

   Two problems, the file named, the replacement named. Exit 1.
3. **Criterion 8, both halves.** `grep -rn "transitions\.claim" README.md
   docs/guide/ skills/` returns five lines, all inside the two migration
   sections this item added — see the criterion note below.
   `docs/changelogs/v2.1.0.md`, `v2.1.2.md` and `docs/release-notes/v2.1.0.md`
   still carry the old key, which is what shipped in them.
4. **Criterion 6.** `grep -rn "claim_transition" tcw/` returns
   `exclusive_claim_transition` and five lines in `tcw/tracker/claim.py`, all of
   them that module's own local parameter. `TrackerConfig` has no
   `claim_transition` attribute; mutation 1's failure message —
   `'TrackerConfig' object has no attribute 'claim_transition'. Did you mean:
   'start_transition'?` — is the incidental proof.

## What the plan and spec got wrong

**The catch-up walk was not a defect, and the spec said it was.** This is the
substantive error and it is corrected in `f21c7c08`.

The spec's Problem section claimed that the walk derives its start hop's
transition from the status while a start applies the configured name, on the
same ticket in the same run; the Design section called that behavior change
intended; the Sweep called it a sibling defect fixed here; Risk 1 was about it;
and Task 2 item 6 of the plan was a test for it.

The reasoning behind it was sound and the conclusion was not. `MOVE_ONTO["active"]`
really is `"start"`, and `transition_name` really could only ever return `""`
for it, because `start` could not be in `move_transitions`. What I did not check
before writing it down is whether anything reaches that call. Nothing does. A
probe added to `transition_name`, printing whenever it is asked for a `start`
move with a name configured, fired **zero** times across
`tests/test_tracker_sync.py`, `tests/test_tracker_replay.py`,
`tests/test_tracker_hold.py` and `tests/test_tracker_cli.py` — and the probe was
itself checked, printing on a direct call, so the silence was the answer and not
a broken probe. Reading the code agrees: the walk visits the `active` rung only
when `reached` is empty, which means the ticket is off the ladder, and every
path into `walk` has it on the ladder.

So putting `start` into `move_transitions` changes no behaviour at all. It is
still right — leaving `start` out is what made the walk's question unanswerable,
and a later change that does reach the hop would otherwise get the wrong
transition silently — but it is consistency in unreached code, not a fix. The
planned test was dropped rather than written, because a test for an unreachable
refusal either cannot be written or passes for some other reason, and what it
was for moved into the first assertion as a direct
`transition_name(config.move_transitions, "start", None)` check.

The upside is that this item now changes no runtime behaviour whatsoever. The
only thing that behaves differently is which spelling of one configuration key
is accepted.

**Criterion 8 as written is falsified by the work it also asks for.** It says no
file under `docs/guide/`, `skills/` or `README.md` mentions `transitions.claim`.
Five lines do, and all five are the migration sections — the table row that says
what the key used to be called, the two headings, and the quoted `tcw validate`
output. A rename nobody is told about is a worse outcome than a mention.
The criterion is met on its intent: no file under those paths tells a reader to
*use* `transitions.claim`, and every mention is labelled as the old name. I have
left the criterion as it stands rather than rewriting it after the fact, and
recorded the narrowing here, so whoever verifies this reads both.

**Two line citations in the spec were one or two lines off** when first written
— `intake.claim`, `_stage_removed_form` and `parse_tracker_config` — and were
corrected before the spec was committed.

**Everything else in the plan held.** Task 1 was indivisible for exactly the
reason given. `tcw/store/base.py` and C2's region around `SYNC_FIELDS` did not
come near each other. `skills/configure/references/tracker.md` already carried
C1's `exclusive-claim-transition` text, which this item edited on top of rather
than beside.

## Capabilities

**No capability delta, so no `capabilities.yaml`.** The spec's "Capability
changes" section records the reasoning: all four of the epic's deltas belong to
siblings, and no ledger entry names the key — `work/manage-external-tracker-intake`
says "the configured claim transition" without naming it, and
`work/inherit-tracker-settings-from-parent-nodes` (`cap-69ba01`) describes
merging by key without naming any. Renaming a key changes how a setting is
spelled, not what a user can do. Nothing was flipped to `Supported`.

## Notes

- **The work system was driven by hand from the first edit to `tcw/`.** The
  repository's rule is that the `tcw` CLI must not drive lifecycle transitions
  while TCW's own code is being changed, because the CLI is the thing under
  modification. `tcw work stage gate` and `tcw work stage prompt` were used
  throughout, since they only print; every artifact here was written directly
  into the item folder and committed by hand. No transition verb was run.
- **The `request`, `spec` and `plan` gates all refused**, reporting that those
  stages run in `backlog` and this item is already `active`. It was started
  before its artifacts existed. The prompts were read anyway — which is what
  `stage prompt` says it is for — and the artifacts written in order, each as
  its own commit.
- **A private virtual environment was used throughout** rather than re-pointing
  the shared editable install, since a second worktree is active. Its code path
  was confirmed from the worktree and from the throwaway node, not assumed.
- This item stops here. `refined-outcome.md` is not written, nothing is
  submitted, completed or merged.
