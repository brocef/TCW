# Outcome — TCW-77: web viewer, a single-process document reader and editor with autocomplete everywhere

Implemented on `work/2026-10-01-tcw-77-web-viewer-a-single-process-document-reader-and-editor-with-autocomplete-everywhere`,
made from `epic/tcw-3.0` at `58da5913`, one commit per plan task, `a98a1824`
to `527f435f`. Task 14 (mutation checks) found no gap, so it has no commit.
`capabilities.yaml` (`06139206`) and this file are on main.

Tests were run per task against the changed areas, never as a full suite, in a
private virtual environment installed from the worktree, with the worktree as
the current folder, and with `HOME` and `XDG_CONFIG_HOME` in scratch folders
for every command run by hand. The final run covered the eight standing files
(`test_cli_contract.py`, `test_cli_help_standard.py`, `test_static_guards.py`,
`test_cli_handler.py`, `test_tree_store_raises.py`, `test_no_node.py`,
`test_ledger_3_0.py`, `test_documented_cli_surface.py`), `tests/serve/`,
`test_capabilities.py`, `test_taxonomy.py`, `tests/work/test_cli_items.py`,
`test_capability_ref_wording.py`, `test_upcoming_entries.py` and
`test_plugin_manifests.py`: 1146 passed, 9 skipped (the 9 are TCW-70's
not-ported 2.x cases in `test_capabilities.py`). The client: `npx vitest run`
132 passed in 14 files; `tsc --noEmit` and `eslint web --max-warnings 0`
clean; `pnpm check:build` passes on the committed tree. `pytest
--collect-only -q` collects 4110 tests with no error.

The Playwright run was not made, by the epic's instruction; see "Browser tests
and snapshots" below.

## What was built

| Task | Commit | What |
| --- | --- | --- |
| 1 | `a98a1824` | Work-layer helpers the viewer calls: `new_item` and `creation_stage` (the function behind `tcw work new`, with the inbox stage), `blocks_target`, `readable` (in `tcw/work/record.py`), `layout.item_folders()`, and `create_fields()` for the Jira create form. |
| 2 | `3f460162` | One Python process: `tcw/serve/server.py` (`ThreadingHTTPServer`, the packaged client with a fallback to `index.html`, Host and Origin checks on every request, JSON writes of at most 1 MiB, the content security policy, errors mapped from `tcw/errors.py`). Node.js, Fastify, the sidecar and `runtime.py` removed. |
| 3 | `c254829e` | `GET /api/project`, `GET /api/work` (with the fallback to item folders), `GET /api/work/<folder>`. |
| 4 | `87c838d1` | An item's files: read, write with a SHA-256 revision, where a new document, round or handoff goes; the declaration as six lists; validation findings on save. |
| 5 | `a1768de5` | `PATCH` with `{changes, expected}`, comments, `blocks`, create (here, at the inbox, into a connected project), tickets and adopt, `/api/options`. |
| 6 | `34f0679c` | Taxonomy and capability edits refuse an inherited entry (403) and a subject that is not a vocabulary entry (400). |
| 7 | `f4abe9d3` | The client's 3.0 model, board, filters, stage tabs and read-only item page. |
| 8 | `963d8c2e` | The file editor, properties, blocks and comment forms, the new-item form, the Tickets view, the declaration form and its plain-text fallback. |
| 9 | `14a4f4fb` | Refuse, warn and allow modes on every reference field, server suggestion sources, path segments, `!` on roles and conditions, scales from the project, `tcw://` completion in the Markdown editor. |
| 10 | `443236b4` | `tests/serve/test_no_stage_names.py`, `tests/serve/test_wording.py`; the git-word and node guards read `tcw/serve/`. |
| 11 | `562653d6` | `tests/serve/jira_launcher.py` and its tests; `web/e2e/parity.spec.ts` rewritten; `web/e2e/jira.spec.ts`. |
| 12 | `29f9b290` | Records: `web`, `web/editing`, two new `web/` records, the two `cli/` records' viewer sentences, the `local-web-app` term. |
| 13 | `527f435f` | `docs/guide/web-viewer.md` rewritten; changelog and release-notes entries; the guide half of the wording test. |

## Acceptance criteria

| AC | Evidence |
| --- | --- |
| 1 One process, no Node, git read only | `tests/serve/test_no_process.py` (`test_the_git_rule`, `test_only_read_only_git_runs_while_answering`, `test_the_child_process_starts_no_child`); `tests/serve/test_process.py::test_the_node_server_is_gone`, `::test_no_serve_module_starts_a_process` |
| 2 stdout and exit codes | `test_process.py` (URL alone and SIGTERM exit 0, port in use, outside a project, missing assets, flushed before serving, `--no-open`, loopback only) |
| 3 Static files | `tests/serve/test_static.py` |
| 4 Security | `tests/serve/test_security.py`; `test_work_write.py::test_no_answer_carries_the_jira_credentials` |
| 5 No lifecycle | `test_no_process.py::test_lifecycle_routes_do_not_exist`, `::test_no_route_moves_an_item`, `::test_no_serve_module_imports_the_lifecycle`; the client: `work-views.test.tsx` (the `tcw work advance` line, no move control) |
| 6 Files | `tests/serve/test_files.py` |
| 7 Declaration form | `test_files.py` (round trip, empty lists, changed must exist, parser fallback, stale 409); `declaration-form.test.tsx` |
| 8 Properties, blocks, comments | `tests/serve/test_work_write.py`; `work-forms.test.tsx` |
| 9 Creating | `test_work_write.py` (here, inbox, connected project, other-project fields, delegation refusals, refused values create nothing); `work-forms.test.tsx` |
| 10 Jira mode (memory backend) | `test_work_read.py` (the `jira_*` cases and degrading), `test_work_write.py` (read-only, refused ticket key, tickets, assignee suggestions); `test_files.py::test_a_stage_the_backend_keeps_has_no_files`, `::test_files_stay_editable_while_the_backend_cannot_answer` |
| 11 Jira mode, real backend | `tests/serve/test_jira_launcher.py` (no credentials: fallback naming the variable, file saved; with them: one search and no `/user`; the marker). The browser half is `web/e2e/jira.spec.ts`, written and not run. |
| 12 Autocomplete | `reference-input.test.tsx` (refuse, warn with `other-project/2026-01-01-x`, `!` on Roles and When, server source), `reference-search.test.ts` (the field table, path segments, `tcw://` options), `shared-components.test.tsx` (typing `tcw://` inserts `tcw://W/<folder>`); the server's 400s in `test_work_write.py` and `test_records.py`; `test_work_write.py::test_assignee_suggestions_ask_for_ten` |
| 13 One project | `test_work_read.py::test_a_child_projects_items_are_not_on_the_board`; `test_records.py` (another project's item answers `other-project`) |
| 14 No stage names | `tests/serve/test_no_stage_names.py`, with the planted `"review"`, `"plan/plan.md"` and `"request body too large"` cases |
| 15 Validation notices | `test_files.py::test_a_dangling_link_is_a_warning_and_the_file_is_saved`, `::test_a_round_without_a_verdict_is_warned_invalid`, `::test_files_stay_editable_while_the_backend_cannot_answer` |
| 16 Build | `pnpm build`; `pnpm check:build` passes; `tests/serve/test_static.py` |
| 17 Old tests | See "2.x tests deleted or rewritten". The full suite was not run, by the epic's instruction. |
| 18 Wording | `tests/serve/test_wording.py` (server strings, guide lines, "never changes git state", both entries start with `##`) |

## Mutation checks

Each guard below was broken on purpose; the named tests went red for the
stated reason, and the file was restored (`git status` clean afterwards).

- The Host rule accepting a missing `Host` when `Origin` is loopback:
  `test_no_host_with_a_loopback_origin_is_refused` and the matching
  `test_the_loopback_rule` case red.
- The static resolver without the inside-the-folder check: the encoded
  traversal case of `test_nothing_outside_the_client_folder_is_served` and
  `test_a_traversal_that_escapes_is_not_found` red.
- The stale check on files removed: `test_a_stale_write_changes_nothing`,
  `test_creating_a_document_makes_its_stage_folder` (the repeated create) and
  `test_a_stale_declaration_save_is_409` red.
- `expected` not compared on `PATCH`:
  `test_a_property_change_checks_what_the_form_loaded` and the stale step of
  `test_a_local_blocker_must_be_an_item_here` red.
- The 403 for backend-owned content removed:
  `test_jira_owned_content_is_read_only` red.
- Degrading turned off: both cases of
  `test_jira_mode_degrades_when_the_backend_cannot_answer` (`Unreachable`,
  `BackendError`) red.
- The file rules allowing `item.yaml`:
  `test_paths_the_layout_does_not_name_are_404[item.yaml]` red.
- The stage-name scan ignoring path segments: the four planted
  `plan/plan.md` cases red.
- The capability subject check removed:
  `test_a_refused_capability_value_is_400_and_writes_nothing[fields2]` red.
- stdout printing a prefix before the URL: the four process tests that read
  the URL red.
- The client stage-name scan, with a planted
  `` `${"x"}/plan/plan.md` `` in `model/work.ts`: red, naming the line.

## 2.x tests deleted or rewritten

Deleted, with the 2.x server they tested (replaced by `tests/serve/`):

- `tests/test_serve.py`, `tests/test_serve_write.py`,
  `tests/test_serve_resolve.py`, `tests/test_serve_runtime.py`.
- `tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream`
  and `::test_serve_reads_an_upstream_item`: they drove 2.x routes (start,
  plan stages, sidecars) that no longer exist; the viewer serves one project,
  and writing into an upstream through `blocks` and create is refused by
  `test_work_write.py::test_blocks_into_an_upstream_is_refused` and
  `::test_targets_delegation_refuses`.
- Their entries in `tests/not_ported.py` (one `test_serve_resolve.py` case and
  nine `test_upstream_projects.py` cases), since the tests are gone.

Rewritten, keeping what they test:

- `tests/test_findings_type.py`: a viewer save's findings are now
  `{severity, where, message}` objects, read through `tests/serve/conftest.py`.
- `tests/test_literal_store_names.py`: the 404 for an encoded slash also
  checks the JSON `code`.
- `tests/conftest.py`: the browser opener is patched in `tcw.serve.server`.
- `tests/test_static_guards.py`, `tests/test_no_node.py`: read `tcw/serve/`.

Client tests: `ui/work-resource.test.ts` deleted with the 2.x work resource;
`tree`, `api`, `work`, `route-utils`, `shared-components`,
`work-document-tabs`, `app` and `content-views` tests rewritten for 3.0.

## Where the work differs from the plan

1. **Criterion 1's command shape.** The real read-only git commands put
   `-C <path>` first (`git -C <root> rev-parse …`,
   `git -C <root> --no-optional-locks status …`); the test allows that prefix.
2. **An undeclared create target answers 409**, as the spec says, not 400 as
   the plan says.
3. **The blocks test uses a second child project**, `s`, beside the target.
4. **`tcw/serve/work.py` imports `tcw.work.cli`** for `new_item` and
   `blocks_target`, the functions behind `tcw work new` and `edit --blocks`,
   rather than a copy.
5. **In Jira mode, refusing an assignee** is left to the operation.
6. **Task 7 already did part of Task 8**: it removed the `Planning doc` and
   `Tracker` form fields, the 2.x modals and the 2.x work editor, because the
   client would not compile otherwise.
7. **The forms are in a new file**, `ui/work-forms.tsx`, with
   `work-forms.test.tsx`, not in `work-views.tsx`; the declaration form is in
   `ui/declaration-form.tsx`.
8. **Board rows are coloured by stage kind** (flow, side, terminal, none),
   not by stage name, so the CSS names no stage.
9. **Tickets is a mode of the detail pane** with no URL of its own.
10. **The reference-search fields for the assignee and the declaration
    lists were added in Task 8**, which needed them, not Task 9.
11. **The client stage-name scan is a small tokenizer in Python**, not a
    TypeScript parser, so the test needs no Node. Its own cases show it skips
    comments and reads past JSX apostrophes and regular expressions.
12. **The unreachable banner shows the exception's own message**, "could not
    reach the tracker at <site>", which is TCW-71's client wording. Criterion
    11 quotes "Jira is unreachable", which Design 7.3 gives only as an
    example; `jira.spec.ts` checks the real message.
13. **The launcher writes `requests.log` and reads the `unreachable` marker
    in the fixture folder**, beside the project folder rather than inside it,
    so the log never appears in the project's own files.

## Records gate

`records_problems(..., finished=True)` over this item's `capabilities.yaml`,
against the branch's ledger and taxonomy, reports no problem. The stores' own
checks report nothing for the records this item changed.

## Browser tests and snapshots

`web/e2e/parity.spec.ts` (rewritten) and `web/e2e/jira.spec.ts` (new) pass
`tsc` and `eslint` and were not run. All three committed snapshots would
change and were not refreshed: `shell-system-dark`, `shell-explicit-light`
and `settings-responsive`. Each is taken on the work board, which now has the
**+ New item** button, the stage, tags and assignee facets and the sort
control. `jira.spec.ts` needs `python` on the path to be the environment that
has TCW and the test packages installed, or `TCW_PYTHON` set to one.

## Found and not fixed here

- **26 capability records still carry the retired `Planning doc` field**,
  `web/choose-a-theme` among them; the spec leaves that record unchanged, so
  it still fails the capabilities check for that field.
- **Other guides still describe the 2.x viewer**: `docs/guide/work.md`
  (hooks, interrupted starts and Recover, aggregation, "the same document
  `tcw serve`'s API returns"), `docs/guide/jira.md` (moves and refusals in
  `tcw serve`), `docs/guide/configuration.md:252`,
  `docs/guide/linking-and-validation.md:26` and `docs/guide/multi-repo.md:86`.
  They are TCW-75's.

## Documentation

| Entry | Handled |
| --- | --- |
| `README.md` [Public-API] | Deferred to TCW-75, which owns the web app section and the install note that names Node.js. |
| `docs/guide/jira.md` [Tracker-Change] | Does not fire: no tracker command or key changes. Its `tcw serve` sentences are TCW-75's. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | `docs/guide/web-viewer.md` rewritten (Task 13). The guides listed above are TCW-75's. |
| Release notes (upcoming) | Written (Task 13). |
| Changelog (upcoming) | Written (Task 13). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Handed to TCW-74: `skills/setup/SKILL.md:8` and `skills/setup/references/install.md:71-74` still name Node.js as a prerequisite of `tcw serve`. |
| `skills/configure/references/` [Configuration-Key-Change] | Does not fire: no configuration key changes. |

The documented-surface allowance list (`tests/doc_allowance.py`, TCW-74's
file) still needs `tcw work list --include-descendants`: other guides name it,
so nothing was removed from it.

## For later children

- **TCW-74:** the setup skill's two Node.js sentences.
- **TCW-75:** `README.md`'s web app section and install note; the guides
  listed under "Found and not fixed here".
- **End of the epic:** run `pnpm test:e2e`, refresh the three snapshots, and
  run `jira.spec.ts` against the launcher.
- **Originating issue:** none; TCW-77 came from Jira, not GitHub.
