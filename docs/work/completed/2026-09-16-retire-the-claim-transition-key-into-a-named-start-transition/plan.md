# Plan: Retire the claim transition key into a named start transition

Three code tasks and one documentation block. The first task is one commit and
cannot be split: renaming a dataclass field breaks its readers in the same
instant, and leaving this repository's own `tcw-config.yaml` on the old key
would leave `tcw validate` failing between commits.

## Task 1 — `start` replaces `claim` in the configuration, end to end

One commit. The suite is green at its boundary and red anywhere inside it.

**Modifies `tcw/store/base.py`:**

- `TRACKER_TRANSITION_KEYS` (`:1127`): `claim` out, `start` in.
- `TRACKER_MOVE_TRANSITION_KEYS` (`:1128`): `"start"` in, first. Delete the
  comment above it that says `start` is absent because `transitions.claim`
  names it.
- New module constant beside them:

  ```python
  # A key that used to exist, with what replaced it, so a config written for an
  # older tcw is told what to change rather than only that a key is unknown.
  TRACKER_RENAMED_KEYS = {
      ("transitions", "claim"):
          "renamed to work.tracker.transitions.start, the transition the start "
          "move applies, alongside submit, rework, complete and discard",
  }
  ```

- `nested`'s unknown-key loop (`:1193-1194`): look the `(key, sub)` pair up in
  `TRACKER_RENAMED_KEYS` and fall back to `"unknown key"`. Reported here rather
  than after the call, so a retired key produces one problem and not two.
- `parse_tracker_config` (`:1241`): delete the
  `nested_str(transitions, "claim", …)` call. After `move_transitions` is
  parsed, add the membership test for the required key:

  ```python
  if "start" not in transitions:
      problems.append("work.tracker.transitions.start: required")
  start = move_transitions.get("start", "")
  ```

  and pass `start_transition=start` at `:1271`.
- `TrackerConfig.claim_transition` (`:1079`) → `start_transition`, with a
  comment saying it is the same string as `move_transitions["start"]`, named
  because the readers of it want the start move's transition specifically.
- `TrackerConfig.exclusive_claim_transition`'s comment (`:1082-1084`): its
  cross-reference "Not `transitions.claim`" becomes "Not `transitions.start`".
- `_parse_tracker_transitions`'s docstring (`:1369`): it says `claim` is parsed
  separately because it is required. It becomes: all five keys are parsed here,
  and `start`'s required-ness is checked by the caller.
- `attribute_tracker_problems`'s docstring (`:1525`): its example
  `transitions.claim: required` becomes `transitions.start: required`.

**Modifies the four readers, by name only:**

- `tcw/tracker/intake.py:329` — `client.config.claim_transition` →
  `client.config.start_transition`.
- `tcw/tracker/sync.py:743` and `:747` — the same, twice.
- `tcw/work/cli.py:2224` — the same.
- `tcw/tracker/ownership.py:10` — docstring mention of
  `client.config.claim_transition`.

**Modifies two comments and one message that name the old key:**

- `tcw/tracker/sync.py:53-54` — the `MOVE_ONTO` comment claiming the claim has
  a transition name of its own. `active`'s move is still `start`; the reason
  given for it is what changes.
- `tcw/tracker/claim.py:166` — the `CLAIM_NOT_OFFERED` detail string names
  `work.tracker.transitions.claim`. It becomes `…transitions.start`. The
  function's parameter stays `claim_transition`: `tcw/tracker/claim.py` is about
  whether a ticket can be claimed, which is still what it answers, and C4 is
  what retires that concept. Only the text that names a configuration key is
  wrong today, and only that is changed.

**Modifies `tcw-config.yaml:13`:** `claim: Start` → `start: Start`.

**Modifies the existing tests that name the old field or key:**

- `tests/test_tracker_claim.py:31`, `tests/test_tracker_client.py:35`,
  `tests/test_tracker_ownership.py:33` — the `claim_transition=` constructor
  argument.
- `tests/test_tracker_config.py:45`, `:200`, `:297`, `:300` — assertions on
  `config.claim_transition`; `:88-91`
  (`test_a_missing_claim_transition_is_reported_by_name`) — renamed to
  `test_a_missing_start_transition_is_reported_by_name` and asserting on
  `work.tracker.transitions.start`; `:294` — the comment explaining that
  `exclusive-claim-transition` and `transitions.claim` are different keys, which
  is still true of `transitions.start`.
- `tests/test_tracker_inheritance.py:229` and `:523` — the exact problem string
  `work.tracker.transitions.claim: required` becomes
  `work.tracker.transitions.start: required`.
- Every fixture or helper elsewhere in `tests/` that writes a `transitions:`
  block with a `claim:` key. Found by
  `grep -rn "claim: " tests/` and `grep -rn "claim_transition" tests/` before
  the task is called done; the two greps are re-run at the end and must return
  nothing but `exclusive` matches.

*Proves:* the full suite, green. Criteria 1, 6 and 7 in part; criteria 2–5 are
Task 2's.

## Task 2 — The assertions this item adds, each mutation-checked

One commit, in `tests/test_tracker_config.py` and
`tests/test_tracker_inheritance.py`. Every assertion below is broken before it
is trusted: the named mutation is applied to the source, the test is run, the
failure is read, and the mutation is reverted. Each mutation and what went red
is recorded in `outcome.md`.

1. `test_the_start_transition_is_a_move_transition_like_its_siblings` —
   a block with `transitions: {start: Start Progress}` parses, and
   `config.start_transition`, `config.move_transitions["start"]` and
   `transition_name(config.move_transitions, "start", None)` are all
   `"Start Progress"`. The third is what the walk would call, and it is the
   assertion that item 6 below was meant to cover from the outside.
   *Mutation:* remove `"start"` from `TRACKER_MOVE_TRANSITION_KEYS`. Expected
   red: `KeyError: 'start'` on `move_transitions`. This is the assertion that
   distinguishes "renamed the key" from "made it an ordinary move key", so it is
   the one that must not pass for the wrong reason.
2. `test_the_retired_claim_key_names_its_replacement` —
   `transitions: {claim: Start Progress}` does not parse; exactly one problem
   mentions `work.tracker.transitions.claim`; that problem contains
   `work.tracker.transitions.start`; no problem for that key contains
   `unknown key`; and `work.tracker.transitions.start: required` is also
   reported.
   *Mutation:* empty `TRACKER_RENAMED_KEYS`. Expected red: the problem reads
   `unknown key` and names no replacement.
3. `test_a_missing_start_transition_is_reported_by_name` (the renamed existing
   test) — `transitions: {}` reports `work.tracker.transitions.start: required`.
   *Mutation:* delete the `if "start" not in transitions` membership test.
   Expected red: the block parses with no problems at all.
4. `test_a_present_but_unusable_start_transition_is_reported`, parametrized over
   `None`, `""` and `5` — each is reported for
   `work.tracker.transitions.start`, with the wording
   `_parse_tracker_transitions` gives its four siblings.
   *Mutation:* make `_parse_tracker_transitions`'s `name()` accept any value.
   Expected red: no problem is reported for the bad value.
5. In `tests/test_tracker_inheritance.py`, alongside the two existing
   `transitions.start: required` assertions:
   `test_a_retired_key_in_a_parent_names_the_parents_file` — a parent node whose
   `transitions` block sets `claim`, a child that inherits it, and
   `attribute_tracker_problems` prefixing the renamed-key problem with the
   parent's label.
   *Mutation:* change `attribute_tracker_problems`'s path match to the enclosing
   mapping (`transitions`) rather than the exact path. Expected red: the problem
   is attributed to whichever file supplied the `transitions` block rather than
   the one that supplied `claim`. If the two labels coincide in the fixture the
   mutation proves nothing, so the fixture must put the `transitions` block and
   the `claim` key in different files; that is checked before the mutation is
   run.
6. ~~`test_the_catch_up_walk_uses_the_named_start_transition`.~~ **Dropped
   during implementation, and the spec amended with it.** The walk's start hop
   is not reachable: a probe in `transition_name` that prints whenever it is
   asked for a `start` move with a name configured fired zero times across
   `tests/test_tracker_sync.py`, `tests/test_tracker_replay.py`,
   `tests/test_tracker_hold.py` and `tests/test_tracker_cli.py`, and reading the
   code agrees. A test asserting a refusal on that path could not be written
   honestly, and writing one that passed for some other reason is exactly the
   unearned green this project's rules exist to stop. What it was for — that
   `transition_name` can answer for a start at all — moved into item 1.

*Proves:* criteria 1–4, 5 and the first half of 6.

## Task 3 — This repository's own configuration, checked rather than assumed

No new files. `tcw validate` is run from the worktree against the edited
`tcw-config.yaml` from Task 1, and its output is read rather than its exit code.
It must report no `work.tracker` problem. `tcw work tracker list` is **not** run:
it needs live Jira credentials, and criterion 7 is about the configuration
parsing, not about the site answering.

*Proves:* criterion 7.

## Task 4 — Documentation Sync

One commit, after the code is green. Every entry below was evaluated against the
finished diff; the two that do not fire are recorded with why.

| Document | Trigger | Fires? | What changes |
| --- | --- | --- | --- |
| `docs/guide/jira.md` | Tracker-Change | **yes** | The `transitions` table row (`:72`) moves from `transitions.claim` to `transitions.start` and joins the sibling row below it; the four configuration examples (`:49`, `:129`, `:556`) and the inheritance prose (`:115`); the misspelling note (`:101`); the claim sequence (`:234`); the `exclusive-claim-transition` cross-reference (`:365`); and the sentence at `:566` that says there is no `start` key, which is exactly the sentence this item falsifies. A short note that a configuration written for an earlier release is reported by `tcw validate` with the new name. |
| `skills/configure/references/tracker.md` | Configuration-Key-Change | **yes** | `:5`, `:22`, `:33`, `:50`, `:62`, `:78`, `:175` — the same rename, including the "no `start` key" claim at `:62` and the `exclusive-claim-transition` contrast at `:78`. |
| `README.md` | Public-API | **yes** | The configuration example at `:544`. The Jira prose around `:510-525` describes what a start does to a ticket, which this item does not change, and is left alone. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | A new section in plain language: the key is now called `transitions.start`, every tracker-backed project has to change one word, and `tcw validate` names the replacement and the file. No module names. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Under Changed and Removed. Also corrects an existing line in that file — "`transitions` keys other than `claim` are unknown to 2.3.0 and earlier" — which names a key that no longer exists. |
| `skills/work/references/commands.md` | Skill-Driven-Component | **yes**, narrowly | `:291` states that neither `list` nor `show` detects a wrong `transitions.claim` value. The statement stays true of `transitions.start`; only the key name is wrong. No `tcw work` verb, field or guardrail changes, so `skills/work/SKILL.md` itself is untouched. |
| `docs/changelogs/v2.1.0.md`, `v2.1.2.md`, `docs/release-notes/v2.1.0.md` | — | **no** | A changelog records what shipped in a past version. `transitions.claim` is what shipped then, and rewriting it would make the history wrong. |
| `skills/capabilities/`, `skills/taxonomy/`, the capability ledger | — | **no** | No capability entry changes; the spec's "Capability changes" section records why. |

*Proves:* criterion 8.

## Verification

What the suite cannot check, run by hand from the worktree and quoted in
`outcome.md`:

1. `tcw validate` against this repository's own edited `tcw-config.yaml`, run
   through a private virtual environment pointed at the worktree so the shared
   editable install is not disturbed. Output read, not exit code.
2. A hand-built node whose `tcw-config.yaml` still carries
   `transitions: {claim: Start}`, validated the same way, so the message a real
   upgrading user sees is read as they will see it — not only as a test
   asserts it.
3. `grep -rn "transitions\.claim" README.md docs/guide/ skills/` returns
   nothing, and `grep -rn "transitions\.claim" docs/changelogs/ docs/release-notes/`
   still returns the released-version files. Criterion 8, both halves.
4. `grep -rn "claim_transition" tcw/` returns only `exclusive_claim_transition`
   and `tcw/tracker/claim.py`'s local parameter. Criterion 6.
5. The full test suite, redirected to a file, with the last lines read. A
   background run reporting exit code 0 is not evidence.

## Notes

- Nothing here is blocked. The epic removed C3's blocker on C1 (`plan.md:43-53`
  of the epic), and C2 is independent of this item in both directions.
- Task ordering puts the riskiest change — the catch-up walk beginning to use a
  named transition — behind the assertion that detects it (Task 2, item 6)
  rather than in the commit that makes it. The commit that changes the behavior
  is Task 1, so if Task 1's suite run goes red in a walk test, that is the risk
  arriving and it is diagnosed before Task 2 is written, not after.
- `tests/fixtures/prompt_fallback/capture.py` is not run by this item. It
  re-baselines its fixture from whatever `tcw` is on PATH, and with two
  worktrees in play a wrong pin would rewrite the fixture to another tree's text
  with nothing going red.
