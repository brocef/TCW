# Outcome — Inherit work.tracker from parent nodes, key by key

Built on branch `work/2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`
in `.worktrees/2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key/`.

Commit ids below are the branch as rebased onto `main` after v2.1.2 (see "Rebased
onto main after v2.1.2" at the end). Test results quoted at a commit before that
section were run on the pre-rebase commits and are kept as the record of that
round; the rebased branch was re-run in full.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `376b6090` | Capability `work/inherit-tracker-settings-from-parent-nodes` (`cap-69ba01`), Missing, and the item's `capabilities.yaml` declaring it under `new:`. |
| 2 | `dd9d55cf` | `tcw/store/base.py`: `merge_tracker_blocks`, `tracker_credentials_problem`, `attribute_tracker_problems`; `parse_tracker_config` sorts unknown keys with `key=str` (Goal 8). Tests first. |
| 3 | `d3e91aeb` | `tcw/store/fs.py`: `tracker_config` / `tracker_problems` share `_resolved_tracker`, which reads ancestors through `FsProjectRegistry` when the node opts in. |
| 4 | `e1808ff0` | End-to-end tests: `tcw work tracker list` sends the child's query to the inherited site; `tcw validate` reports a parent's bad value under the child. |
| — | `0360fec4` | Inbox entry for the same non-string-key crash in other config parsers (found in review; separate change). |
| — | `2cd9a8fe` | Review fixes (see below). |
| 6 | `a3297e9e` | Documentation: `README.md`, `docs/guide/work.md`, `skills/tcw-work/references/commands.md`, both `upcoming.md` files, both capability descriptions. |

Task 5 (full suite) and Task 7 (this file) have no code commit of their own.

## Test results

- **Before the review fixes (pre-rebase `30c7db37`):** 2867 passed under
  `python -m pytest`, and 2867 passed under bare `pytest` (what CI runs).
- **After the documentation commit (pre-rebase `8c2e608c`):** 2874 passed under `python -m pytest` (14:47), and 2874 passed under bare `pytest` (14:58).
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

A multi review of the code (pre-rebase commits `c81b6a18..30c7db37`). All three produced
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

## Second round, after the first verification

The verifier recommended acceptance with five open points. The user did not accept
it as is and asked for all five to be dealt with before coming back. Two were real
problems in this item, and three were closeout or release matters.

| Point | What was done | Commit |
| --- | --- | --- |
| Docs narrower than the code | The guide said a child can set `credentials.token-env` alone, without saying that is refused beside its own `base-url`. Three docs said the missing-parent notice appears only for incomplete settings; it appears with any tracker problem. Both corrected. | `d3879888` |
| The spec's "never raises" was false | `FsProjectRegistry` raised `TypeError` sorting `connected-projects` keys of mixed types, and this item made `tracker_config()` open the registry. Fixed where the registry builds the message (`tcw/store/project.py`), with a test that failed first. The C18 test now compares the whole merged mapping. | `fda5e720` |
| Capability status | `work/inherit-tracker-settings-from-parent-nodes` is Supported. | `9fccddfe` |
| Combined review with the claim item | See below. | — |
| Issue #36 | Stays open until release. A reply is drafted for approval and not posted. | — |

`v2.1.x` in the changelog was also made exact (`fc4b5ec0` before the rebase). After
v2.1.2 was cut without this item, it reads `v2.1.2 and earlier`.

### The combined review with the claim item

The claim item was completed on `main` (`32edbd8f`) while this round ran. Before
that, both branches were merged into a throwaway copy of `main` and:

- the full suite passed there: 3009 under `python -m pytest`, and 3009 under bare
  `pytest`;
- the reviewer agent and Codex reviewed how the two interact (the local model was
  switched off for maintenance, so this round had two reviewers, not three).

Both found the same two problems, neither in this item's code:

1. **A crash in the claim code that only inheritance makes likely.** `_binding_for`
   re-read `tracker_config()` after the ticket was already claimed. If a parent
   node's file changed mid-run, that returned `None`, and `None.provider` escaped as
   a traceback (in `link`, outside any handler). That left an unbound item, and a
   re-run created a second one. The reviewer reproduced it.
2. **Docs promised one item per ticket without saying "per node"**, in the same
   release that encourages sibling nodes to share inherited settings.

Because the claim item had already completed, `main` was merged into this branch
(a merge commit since replaced by the rebase below). Then:

- `_binding_for` takes the provider and project id the claim was made with. There
  are three new tests in `tests/test_tracker_import.py`: two failed first with the
  `AttributeError`, and one shows import from an inheriting child binds with the
  child's project id (`d2b60bd9`).
- README, guide, skill reference, release notes and the claim capability's
  description scope the promise to one node, and name importing in two nodes as a
  third accepted limit (`78c44333`).

A third finding was filed rather than fixed:
`docs/work/inbox/2026-09-14-a-tracker-binding-does-not-record-its-site.md`. A binding
does not record which Jira site its ticket is from, so after a `base-url` change an
unrelated ticket with the same numeric id reads as already bound. Editing a node's
own `base-url` already did this; inheritance lets one parent edit do it for many
nodes. The suggested fix needs no format change.

### Results after this round (pre-rebase `8df69b1f`)

- Full suite: **3012 passed** under `python -m pytest`, and **3012 passed** under
  bare `pytest`. That is the 3009 of the combined tree plus the three new import
  tests.
- Codex reviewed those two commits (pre-rebase `102d67ce`, `10882d7f`) read-only (`sandbox: read-only`, tree
  unchanged). It answered "no defect" to all five questions: `project` is bound
  on every path, no other post-claim re-read remains, an early `_project_id`
  failure claims nothing, the new tests fail without the fix, and the scoped
  sentences match the code. VERDICT: CLEAN.
- `tcw capabilities check` prints `capabilities OK` and `tcw validate` prints `validate OK`.

## Rebased onto main after v2.1.2

At the user's request the branch was rebased onto the latest `main`. `main` moved
during the rebase: v2.1.2 was cut and pushed (`bb259e7c`), shipping the claim item
without this one. So the rebase was done onto `bb259e7c`, in two passes:

- The merge commit of `main` was dropped, as a rebase does, and the 16 commits
  replayed. The one commit that changed only the changelog became empty and was
  dropped, leaving 15.
- v2.1.2 had rotated `docs/changelogs/upcoming.md` and
  `docs/release-notes/upcoming.md` into `v2.1.2.md` files. Every conflict in them
  took `main`'s fresh files. Then one commit (`91be00ea`) wrote this item's entries
  into the fresh files. The fixes to the claim commands and their docs are listed
  as fixes, since the claim item was released in v2.1.2 with those defects, and
  the non-inheriting versions are named as `v2.1.2 and earlier`.
- **Checked:** apart from the two `upcoming.md` files, the rebased branch differs
  from the pre-rebase branch by exactly the changes `main` gained, file by file.
  The inheritance entries in the new changelog are identical to the pre-rebase
  text apart from the version. One pre-rebase bullet (`parse_tracker_config`)
  turned out to have doubled lines from an earlier conflict resolution, and it was
  restored from the pre-rebase text.

**Results on the rebased branch, at `91be00ea`:** 3061 passed under
`python -m pytest`, and 3061 passed under bare `pytest` (both 14:19). The count is
higher than before because the claim and capability-removal work from `main` is now
included. `tcw capabilities check` prints `capabilities OK` and `tcw validate`
prints `validate OK`.

## Left for later, deliberately

- The six other config parsers with the non-string-key crash
  (`docs/work/inbox/2026-09-14-config-parsers-crash-on-a-non-string-key.md`).
- A binding not recording its site (inbox entry above).
- Unsetting an inherited optional key, and whether `strict` inherits: the sync and
  strict-mode items (spec Non-goals, Risks 2 and 4).

## GitHub issue #36

Stays open. `CLAUDE.md` holds closing an originating issue until the fix is
released and pushed, and nothing is posted to an issue without its exact text being
approved first. `refined-outcome.md` records the deferral again at `verify`.
