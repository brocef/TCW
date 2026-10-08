# Outcome — TCW-71: the Jira work backend

Implemented on `work/2026-10-01-tcw-71-jira-work-backend-jira-as-the-single-owner-of-status-and-the-request`,
made from `epic/tcw-3.0` at `8bf085a3`, in sixteen commits (`c81306ad` to
`7d464442`), one per plan task. Task 1 (the `TCWTEST` checklist) was committed on
main as `9644f8e4`.

**One part is not done yet: Task 15, the live check against `TCWTEST` (AC 23, 24).**
It waits for the owner to apply `tcwtest-checklist.md`. Read on 2026-10-08,
`TCWTEST` still has only the statuses `To Do`, `In Progress` and `Done` for every
issue type, and none of the TCW Project, TCW Item, Effort or Complexity fields on
the Task create screen. So the scenario cannot run there yet. `tests/work/jira/capture.py`,
`tests/work/jira/recorded/` and `test_recorded_shapes.py` come from that run and
do not exist yet. Everything else in the plan is done.

## What was built

| Task | Commit | What |
| --- | --- | --- |
| 2 | `c81306ad` | The client's new and changed operations (Design 14). |
| 3 | `588e1ca2` | `work.jira` configuration and the connected-project `jira` block. |
| 4 | `67d60b44` | Text to ADF and back as a round-tripping pair; field mapping both ways. |
| 5 | `b296d06c` | JQL builders, and the fake's evaluator for exactly those shapes. |
| 6 | `50062d9d` | The fake Jira, rewritten, with a switch for each failure handled. |
| 7 | `e48e7344` | `JiraBackend` reads; ticket keys accepted where an item is named. |
| 8 | `1bb74c7c` | `JiraBackend` writes: `create`, `update`, `comment`, `rename`, `set_stage`. |
| 9 | `baf74f55` | `advance` in Jira mode; the shared backend contract runs on Jira. |
| 10 | `7fd96654`, `ccfcd3f3` | `tickets list`, `tickets adopt`, the display helpers. |
| 11 | `2a66c969` | Delegation into a Jira-mode project. |
| 12 | `740629fe` | Offline `validate` and links into Jira-mode projects, with no request. |
| 13 | `b27e37ba` | `tcw validate --remote`. |
| 14 | `3db0cb0f` | The scenario against the fake; the guards for AC 21 and 22. |
| 16 | `1862683a`, `7d464442` | Capability and taxonomy records; their declaration, kept on main. |
| 17 | `05b1cf6a` | Release-notes and changelog entries. |

## The shared contract

`tests/work/test_backend_contract.py` runs all 51 cases against `JiraBackend`.
**The skip list for `JiraBackend` is empty.**

## Acceptance criteria

| AC | Evidence |
| --- | --- |
| 1 Config | `test_jira_config.py` |
| 2 Folder names, `item.yaml` | `test_jira_read.py`, `test_jira_write.py`, `test_jira_validate_offline.py` |
| 3 `lookup` | `test_jira_read.py` |
| 4 `read` | `test_jira_read.py` |
| 5 `create` | `test_jira_write.py` |
| 6 Children | `test_jira_write.py`; scenario step 8 |
| 7 `update` | `test_jira_write.py`; scenario step 6 |
| 8 Assignee | `test_jira_write.py`, `test_jira_read.py` |
| 9 `set_stage` | `test_jira_set_stage.py` |
| 10 Through `advance` | `test_jira_advance.py`; scenario steps 2–5 |
| 11 `list` | `test_jira_list.py` |
| 12 JQL | `test_jql.py` |
| 13 `tickets list` | `test_jira_tickets.py` |
| 14 `tickets adopt` | `test_jira_tickets.py`; scenario steps 8 and 9 |
| 15 `rename` | `test_jira_write.py`; scenario step 7 |
| 16 `comment`, text round trip | `test_jira_write.py`, `test_mapping.py` |
| 17 Delegation | `test_jira_delegation.py`, `test_open.py`, `test_cli_items.py` |
| 18 `validate --remote` | `test_jira_validate_remote.py`: every bullet, and every case asserts from the fake's log that nothing was written |
| 19 Offline stays offline | `test_jira_validate_offline.py` |
| 20 Errors | `test_jira_errors.py` |
| 21 2.x is gone | `test_jira_guards.py`; the records gate over `capabilities.yaml` (below) |
| 22 Never changes git state | `test_jira_guards.py` |
| 23 Live check | **Not yet: waits for the checklist (Task 15).** The fake half passes: `test_jira_scenario.py::test_the_scenario_against_the_fake`. |
| 24 Shape agreement | **Not yet: needs the recorded responses from the live run.** |
| 25 The rest of the suite | Bare `pytest` from the branch checkout: 3178 passed, 131 skipped, exit 0. |
| 26 The three reads | `test_jira_read.py`, `test_jira_tickets.py` |
| 27 Release notes and allowance | `test_upcoming_entries.py`, the doc-allowance guard |

## Mutation checks

Every important guard was broken on purpose and the tests went red each time.
The ones the plan names:

- `import subprocess` added to `tcw/work/jira/mapping.py` fails
  `test_no_jira_module_runs_a_process[mapping.py]`.
- The string `tracker.yaml` added to `tcw/work/jira/backend.py` fails
  `test_no_module_names_the_2x_tracker`.

For `validate --remote`, each of these mutations failed the tests: passing a
move with several candidates without sampling it; no direct reads for keys a
search missed; no edit-screen check; checking records on finished items; and no
handling of an unreachable Jira. Dropping the note from `set_stage` fails the
scenario. The earlier tasks' checks are recorded in their commit messages.

## Records gate

`records_problems(layout, slug, project_reader(...), finished=True)` against this
repository's ledgers, for this item's `capabilities.yaml`, reports no problems.
Adding a declared removal of a record that still exists makes it report one. The
released 2.8.1 `tcw validate` on the branch prints `validate OK`.

## Where the work differs from the plan

1. **`advance.run_post(config, layout, project_root, item, stage, *, env=None)`.**
   The plan named a narrower signature. Adoption needs the same post step as
   `advance`, and that step needs the layout and the project root.
2. **Connected-project `jira` blocks are checked in both modes**, not only in
   Jira mode. A filesystem-mode project is the usual one to declare a Jira-mode
   project it delegates into.
3. **Offline `validate` answers a filesystem reference into a Jira-mode project
   from that project's folders** (R20). Without this, plain `validate` in a
   filesystem project would contact Jira.
4. **`open.reference_resolver`** is one function used by both `validate` and
   `validate --remote`, replacing a copy that lived inside `_work_findings`.
5. **With `--remote`, "validate OK" goes to stderr**, so a clean run prints
   nothing on stdout, which AC 18 asks for.
6. **`capabilities.yaml` is in the item's folder on main** (`docs/work/active/…`),
   not under `docs/work/backlog/` on the branch as the plan says. The branch's
   copy of the board is an old snapshot. A file added there would come back as a
   stray folder, or as a conflict, when the epic merges.
7. **One comment outside the plan**: `tcw/serve/__init__.py` still described
   strict-tracker refusals, which no longer exist. The comment was corrected.

## Documentation

Of `work.documentation`'s entries, the release-notes and changelog entries are
written. `README.md`, `docs/guide/jira.md`, `docs/guide/<topic>.md` and
`skills/configure/references/` are deferred to TCW-75, and the skills to TCW-74,
as the spec's non-goals say.

## For later children

- TCW-73's plan: `validate --remote` runs all three model checks (stage,
  reference and records) over Jira items.
