# Outcome — Inherit work.tracker from parent nodes, key by key

Built on branch `work/2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`
in `.worktrees/2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key/`.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `c83f84bd` | Capability `work/inherit-tracker-settings-from-parent-nodes` (`cap-69ba01`), Missing, and the item's `capabilities.yaml` declaring it under `new:`. |
| 2 | `c81b6a18` | `tcw/store/base.py`: `merge_tracker_blocks`, `tracker_credentials_problem`, `attribute_tracker_problems`; `parse_tracker_config` sorts unknown keys with `key=str` (Goal 8). Tests first. |
| 3 | `54be3ffc` | `tcw/store/fs.py`: `tracker_config` / `tracker_problems` share `_resolved_tracker`, which reads ancestors through `FsProjectRegistry` when the node opts in. |
| 4 | `30c7db37` | End-to-end tests: `tcw work tracker list` sends the child's query to the inherited site; `tcw validate` reports a parent's bad value under the child. |
| — | `9fb77253` | Inbox entry for the same non-string-key crash in seven other config parsers (found in review; separate change). |
| — | `2b33ea2e` | Review fixes (see below). |
| 6 | `8c2e608c` | Documentation: `README.md`, `docs/guide/work.md`, `skills/tcw-work/references/commands.md`, both `upcoming.md` files, both capability descriptions. |

Task 5 (full suite) and Task 7 (this file) have no code commit of their own.

## Test results

- **Before the review fixes, at `30c7db37`:** 2867 passed under
  `python -m pytest`, and 2867 passed under bare `pytest` (what CI runs).
- **Final, at `8c2e608c`:** 2874 passed under `python -m pytest` (14:47), and 2874 passed under bare `pytest` (14:58).
- `tests/test_tracker_inheritance.py`: 59 tests, and the four existing tracker test
  files (`test_tracker_config.py`, `test_tracker_validate.py`,
  `test_tracker_absent.py`, `test_tracker_cli.py`) pass unchanged (C12).
- Documentation tests (`test_documented_cli_surface.py`,
  `test_documentation_*`, `test_skill_lifecycle_parity.py`, and others): 447 passed
  after the doc commit.
- **Every test that passed on its first run was broken on purpose and seen to fail
  for the right reason**, and then the code was restored. Broken on purpose: the
  credentials comparison (`<=` → `<`), how a skipped null is recorded, which
  ancestor is asked for its missing parent (`-1` → `0`, with a four-node chain),
  opt-in (`None` only, and absent treated as `{}`), only `email-env` counted by the
  credentials rule, and the whole store change (for the two CLI tests).
- `tcw capabilities check` and `tcw validate` pass.
- The guide's two-file example was built in a scratch graph. The package got the
  site's settings with its own query, the repository with no block had no tracker,
  and repeating the parent's `base-url` without `credentials` was refused, as the
  text says.

## Reviews

A multi review of the code (commits `c81b6a18..30c7db37`). All three produced
usable output.

- **Adversarial code reviewer (agent): DONE, nothing blocking.** It ran 63,878
  combinations of three nodes' blocks against the credentials rule and found no
  config that sends a token to a `base-url` chosen in a nearer file. Accepted:
  - no test held `tracker: {}` to "does not opt in", and no test told the first
    reachable ancestor from the last. Both confirmed by breaking the code with no
    test failing, and both now tested.
  - the abstract `WorkStore.tracker_config` docstring did not say an adapter must
    merge.
  - the changelog should name two upgrade effects: a damaged block in a board-less
    parent now disables its opted-in children, and an omitted `timeout-seconds`
    now inherits.
  - a test for a `base-url` set in an intermediate parent.

  Noted, no change: a `null` written in several files is blamed on the farthest one,
  which matches the spec.
- **Codex (`codex exec`, `sandbox: read-only` confirmed in its header; HEAD and
  `git status` unchanged afterwards): FINDINGS.**
  - Accepted: an integer key and a string key of one spelling shared a source
    record entry. Record paths now keep keys as written.
  - Accepted: a key containing `": "` was attributed to the wrong file. Attribution
    now uses the longest recorded path that prefixes the problem.
  - Accepted: one missing test direction for partly inherited credentials
    (email-env nearer, token-env inherited).
  - Accepted: "reported under each child" was tested with one child. It is now
    tested with two.
  - Narrowed: two recorded paths that spell the same (int `5` vs `"5"`, or a key
    literally named `credentials.x` beside a nested one) can still be attributed to
    each other's file. The block is invalid either way and every problem is still
    reported. Documented on `attribute_tracker_problems`.
  - Needs a separate change: `FsProjectRegistry.open` raises `TypeError` on a
    `connected-projects` block with mixed key types (reproduced). It predates this
    item, and neither CLI path reaches `_resolved_tracker` with it, because both
    open the registry first. Filed with six other sites of the same shape in
    `docs/work/inbox/2026-09-14-config-parsers-crash-on-a-non-string-key.md`.
- **Local model (`bllm review diff`, gemma4, two slices with a contract per
  slice).**
  - Merge slice: "no defect" on all six questions.
  - Store slice, two findings, both rejected:
    - "`registry.config()` may return None". It returns `{}` for an unknown id
      (`tcw/store/project.py:333-335`).
    - "The missing-parent notice follows the credentials problem, breaking
      'exactly one problem'". The spec adds the notice whenever there are problems.
      The "exactly" came from my own guidance wording, not the spec.

## What the plan or spec got wrong

- **Plan, "Before starting": re-pointing the editable install was not done, and
  should not be.** Another session was implementing the claim item in its own
  worktree at the same time, and the editable install is shared by every session on
  this machine. Re-pointing it at this worktree could have run the wrong code under
  that session. Instead, pytest ran with the worktree root as the current directory.
  A probe test confirmed `tcw.__file__` resolved to the worktree under both
  `python -m pytest` and bare `pytest` (`pyproject.toml` sets `pythonpath = ["."]`).
  The `tcw` command itself still ran the primary checkout's code, which was only
  used for `tcw capabilities` / `tcw validate` / `tcw work` lifecycle commands whose
  code this item does not touch. `CLAUDE.md`'s worktree section does not mention
  this alternative, and it is the safer default when sessions overlap.
- **Plan, Task 2: "record key paths as tuples of `str(key)`" was wrong.** It let an
  integer key and a string key of the same spelling overwrite each other's source
  (Codex). Paths now keep the keys as written and are joined with `str` only for
  attribution.
- **Plan, Task 2: "the text between `work.tracker.` and the first `: `" was
  wrong** for a key whose name contains `": "`. Replaced by longest-prefix matching.
- **Plan, Task 3 tests: the three-node chains could not tell the first reachable
  ancestor from the last.** A four-node test was added. My first version of it
  connected the top node after the chain was built, which broke the graph; the
  fixture's graph check caught that before the test could pass for the wrong reason.
- **Spec, Design "Which blocks take part": silent on an ancestor whose `work` value
  is not a mapping** (for example `work: 5`). The code skips it, matching how
  `_work_config` treats the node's own file.
- **Plan, Task 3 step 1: the own-block-not-a-mapping case goes through
  `merge_tracker_blocks`** rather than straight to the parser. The merge returns
  that block unchanged, so the output is identical.

## Left for later, deliberately

- The seven other config parsers with the non-string-key crash (inbox entry above).
- Unsetting an inherited optional key, and whether `strict` inherits: the sync and
  strict-mode items (spec Non-goals, Risks 2 and 4).
- The claim item is being built in parallel. If both ship in one release, review
  their combined change. Both edit `README.md`, `docs/guide/work.md`,
  `skills/tcw-work/references/commands.md` and both `upcoming.md` files, so the
  second to merge resolves text conflicts there.

## GitHub issue #36

Stays open. `CLAUDE.md` holds closing an originating issue until the fix is
released and pushed, and nothing is posted to an issue without its exact text being
approved first. `refined-outcome.md` records the deferral again at `verify`.
