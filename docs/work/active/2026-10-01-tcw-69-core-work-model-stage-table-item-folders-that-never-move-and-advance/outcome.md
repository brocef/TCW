# Outcome — Core work model: stage table, item folders that never move, and advance

## Where the work is

All code is on branch `work/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance`,
made in the worktree `.worktrees/2026-10-01-tcw-69-…` from a new epic branch,
`epic/tcw-3.0`. The owner chose this layout on 2026-10-02: every TCW 3.0 child
branches from `epic/tcw-3.0` and merges back into it, and `main` receives 3.0
only when the epic is finished, because TCW-70 makes the branch's `tcw` refuse a
2.x configuration. The board (`docs/work/`) stays on `main`.

From the first code edit on, the board was driven by editing files, as
`CLAUDE.md` requires. `tcw work start` was run once before that, on `main`.
Tests and `tcw` ran from a private virtual environment pinned to the worktree,
not from the shared editable install.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `33051f70` | `tcw/exit.py` (codes 0–6) and `tcw/errors.py` (`TcwError` and its six subclasses; `Refused` carries an optional backend `name`). |
| 2 | `2a2bae5d` | `tcw/work/model.py`: `Slug`, `title_words`, `PRIORITIES`, `SIZES`, `Item`, `Changes`/`UNSET`, `validate_changes`, `apply_changes`, `blocks_of`. |
| 3 | `93e7153d` | The stage table `STAGES` and its navigation (`stage`, `completion_stage`, `discard_stage`, `start_stage`, `inbox_stage`, `flow_order`, `next_stage`, `position`, `is_skip`, `records_gate_stage`, `gates_for`). |
| 4 | `7d58d578` | `tcw/work/config.py`: `parse_work_config`, `parse_bindings`, `When`, `Binding`, `StageConfig`, `HookLimits`, `WorkConfig`, `ConfigProblem`; fixture `tests/fixtures/tcw-config-2.8.yaml`. |
| 5 | `83261813` | `tcw/work/layout.py`: `Layout`, rounds, handoffs, `round_verdict`, `current_verdict`, `path`. |
| 6 | `3cd049ee` | `tcw/work/backend.py` (`WorkBackend`, `Query`, `Comment`, `default_includes`) and `tests/work/memory_backend.py`. |
| 7 | `360e916c` | `tcw/work/gates.py`: declarations, records gate and its mid-work form, completion gate, drift, `ledger_reader`; `Route` and `route_capability_path` moved here from `recursion.py`, which imports them back. |
| 8 | `1a190327` | `tcw/work/advance.py`: `advance`, `discard`, `Outcome`. |
| 9 | `b88c7b4c` | `tcw/work/references.py`: `reference_problems`, `stage_problems`. |
| 10 | `06bb78dd` | `tests/work/test_model_guards.py` and `tests/work/test_no_git.py`. |
| 11 | `94fef974` | Changelog entry `docs/changelogs/upcoming/2026-10-01-tcw-69-….md`. |

## Tests

- `pytest tests/work -q`: 264 passed.
- After Task 7, the four suites that reach the moved routing code
  (`test_capability_gate_children.py`, `test_recursion.py`,
  `test_capabilities_rm.py`, `test_unreadable_capabilities_sidecar.py`) plus
  `tests/work`: 331 passed.
- Full suite (AC 20): **deferred to the end of the epic** at the owner's
  instruction on 2026-10-02, because it was running far slower than the
  plan's half-hour estimate. A run started after Task 7 was stopped at about
  61% with no failures so far. AC 20 is therefore covered only by the
  targeted runs above until the epic's closing full run.
- `tcw validate` from the worktree with the branch's own code: `validate OK`.

Every new test file was run before its module existed and failed on the
import, as it should.

### Mutation checks

**The guards (Task 10).** Each injected defect turned the expected test red,
and the failure message named the defect:

| Mutation | Red test and message |
| --- | --- |
| `"review"` added to `advance.py` | `test_no_stage_name_is_spelled_outside_the_table[advance.py]`: `advance.py:32: 'review'` |
| `"spec/x.yaml"` as part of an implicitly joined literal in `layout.py` | `…[layout.py]`: `spec/x.yaml` |
| `import subprocess` in `layout.py` | `test_no_module_starts_a_process_or_writes_to_git[layout.py]`: `import subprocess` |
| `fs._git([...])` in `gates.py` | `…[gates.py]`: `._git` |
| `"plan"` in `model.py` outside `STAGES` | `test_model_spells_stage_names_only_inside_the_table`: `model.py:99: 'plan'` |
| the memory backend's `set_stage` runs `git commit --allow-empty` | `test_a_forced_advance_with_hooks_changes_no_git_state`: `HEAD` differs |

**`advance` (Task 8)**, whose tests all passed on their first run once the
module existed:

| Mutation | Result |
| --- | --- |
| skip check removed | both skip tests red |
| `MovedWithoutNote` not handled | `test_a_lost_note_gives_exit_6_and_post_still_runs` red |
| `when:` ignored | both `when` tests red |
| hook environment without the caller's environment | the `python -c` hook fails with exit 127, test red |
| dry run ignored | dry-run test red |
| reported stage not compared | `test_a_backend_reporting_another_stage_is_an_error` red |
| a `stale` verdict treated as `accepted` when choosing the target | **stayed green**, and correctly so: the direction check (Design 6.4) refuses the same forward move from a verdict stage that is not accepted, with the same round-file hint. The two checks overlap by design; neither is dead, because the target choice also decides the backward move on `rejected`. |

**The config test for `when.type`** first asserted only that `"type"` was in
the message, which the generic "unknown key" message also satisfies. With the
`type` refusal removed it stayed green, so it was tightened to assert the
refusal's own wording (`have no type`) and re-checked red.

## Hand traces (plan "Verification")

1. **Review disabled, qa enabled, bare `advance` from implement.**
   `_choose_target`: implement has no verdict, so the target is
   `next_stage(implement)`, which passes over disabled review to qa.
   `is_skip(implement, qa)` is false because the only stage between them is
   disabled. `gates_for(qa)`: `records_gate_stage` is `next_stage(implement)`,
   which is qa, so the records gate runs on this move, then qa's `pre` hooks.
2. **A qa rejection, then a fix.** Implement round 1; review round 1 accepted
   with `judges: 1`; qa round 1 rejected with `judges: 1`. A bare advance from
   qa reads `rejected` and targets implement, a backward move needing nothing.
   The fix writes implement round 2. A bare advance from implement goes to
   review (records gate). Now review's latest round says `judges: 1` while the
   latest implement round is 2, so `current_verdict(review)` is `stale`, and a
   bare advance from review is refused, naming `review/round-2.md`. Only a new
   review round with `judges: 2` lets the item go on to qa, and qa likewise.
3. **Jira-mode qa rejection, `external_stages = {request, qa}`.** A bare
   advance from qa is refused: the verdict lives in the backend, so the
   message says to use `--to`. `--to implement` without a reason is refused by
   the external-verdict rule; with `--reason "fails on Safari"` it passes, and
   `set_stage(folder, "implement", note)` carries the reason as the comment
   that TCW-71 sends with the transition. Acceptance is `--to completed
   --reason …`; the completion gate then checks only review.

## The backend interface against TCW-70 and TCW-71

Re-read against both specs and plans. Neither backend has to fake an
operation: TCW-70 implements all eleven over files (`lookup` always `None`,
`current_user` from `user.name`), and TCW-71 implements all eleven against Jira
(`lookup` from folder names without the network). Two details for TCW-70:

- TCW-70's `create(..., request="")` writes no request and `read_request`
  answers `None`; the memory backend stores `""` and answers `""`. TCW-70's
  plan turns `test_memory_backend.py` into a contract test over both backends,
  and that is where the two must agree.
- TCW-70 adds a `report` callable to its own constructor. That is an adapter
  detail and does not touch the protocol.

## What the plan or spec got wrong

- **The plan said a memory-backend constructor argument `stage=None` would put
  an item in the "no stage" state.** A constructor argument cannot say *which*
  item. It is a test helper instead, `set_reported_stage(folder, stage)`, which
  sets any stage, or none, without recording a call.
- **The plan said the cycle check "stops after visiting as many slugs as
  exist".** The check cannot know how many exist from a `parent_of` callable.
  It stops at a slug it has already visited, which ends a cycle already present
  in the data just as surely (tested).
- **The plan put `stages`-with-`all` refusal in the memory backend's `list`.**
  It lives in `Query` itself (`__post_init__`), so every backend gets it; the
  memory backend's test still checks it through `list`.
- **`Layout` gained a `backend` field** (a name used in refusals), because the
  spec's Design 4.12 says a refusal for an external stage names the backend
  and `Layout(work_root, enabled, external)` had nothing to name it with. It
  defaults to "the work backend".
- **`title_words` takes `limit` with a default** of `FOLDER_LIMIT - 20`
  (`PREFIX_ALLOWANCE`), the bound AC 2 states. A single word longer than the
  limit is cut hard, since there is no `-` to cut at; the plan did not say.
- **`completion_stage()` and the other finders return stage names, not `Stage`
  records.** The plan did not say which; names are what every caller compares.
- **`WorkConfig.stage(name)`** was added: every stage has a `StageConfig`, and
  this returns it, defaulting for a stage the mapping omits.
- **`fake_reader.py`** was added as a shared test helper, used by the gate,
  advance and no-git tests.
- Nothing in the spec turned out wrong.

## Notes

- **Blockers.** TCW-70 to TCW-77 are already work items with `blocked-by`
  chains (TCW-70 is blocked by this item), so the plan's note about recording
  blockers later no longer applies.
- **Closing.** Completion is by hand (the CLI is under change): merge the
  branch into `epic/tcw-3.0`, run `tcw validate`, write
  `refined-outcome.md`, move the folder to `docs/work/completed/`, and move the
  Jira ticket TCW-69 by hand, since a hand edit runs no tracker sync.
