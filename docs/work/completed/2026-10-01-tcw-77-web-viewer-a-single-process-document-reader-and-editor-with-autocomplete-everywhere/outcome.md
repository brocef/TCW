# Outcome — TCW-77: web viewer, a single-process document reader and editor with autocomplete everywhere

Implemented on `work/2026-10-01-tcw-77-web-viewer-a-single-process-document-reader-and-editor-with-autocomplete-everywhere`,
made from `epic/tcw-3.0` at `58da5913` and rebased onto `0e30fca5` (TCW-74) after review round 1 without conflicts, one commit per plan task, `013c9682`
to `9b3bded3`. Task 14 (mutation checks) found no gap, so it has no commit.
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
| 1 | `013c9682` | Work-layer helpers the viewer calls: `new_item` and `creation_stage` (the function behind `tcw work new`, with the inbox stage), `blocks_target`, `readable` (in `tcw/work/record.py`), `layout.item_folders()`, and `create_fields()` for the Jira create form. |
| 2 | `4f28b070` | One Python process: `tcw/serve/server.py` (`ThreadingHTTPServer`, the packaged client with a fallback to `index.html`, Host and Origin checks on every request, JSON writes of at most 1 MiB, the content security policy, errors mapped from `tcw/errors.py`). Node.js, Fastify, the sidecar and `runtime.py` removed. |
| 3 | `5edd266c` | `GET /api/project`, `GET /api/work` (with the fallback to item folders), `GET /api/work/<folder>`. |
| 4 | `316274a5` | An item's files: read, write with a SHA-256 revision, where a new document, round or handoff goes; the declaration as six lists; validation findings on save. |
| 5 | `9a638921` | `PATCH` with `{changes, expected}`, comments, `blocks`, create (here, at the inbox, into a connected project), tickets and adopt, `/api/options`. |
| 6 | `4fa751ac` | Taxonomy and capability edits refuse an inherited entry (403) and a subject that is not a vocabulary entry (400). |
| 7 | `4d39448e` | The client's 3.0 model, board, filters, stage tabs and read-only item page. |
| 8 | `a6e30cf2` | The file editor, properties, blocks and comment forms, the new-item form, the Tickets view, the declaration form and its plain-text fallback. |
| 9 | `bc1e23fb` | Refuse, warn and allow modes on every reference field, server suggestion sources, path segments, `!` on roles and conditions, scales from the project, `tcw://` completion in the Markdown editor. |
| 10 | `b1c88ede` | `tests/serve/test_no_stage_names.py`, `tests/serve/test_wording.py`; the git-word and node guards read `tcw/serve/`. |
| 11 | `ee468610` | `tests/serve/jira_launcher.py` and its tests; `web/e2e/parity.spec.ts` rewritten; `web/e2e/jira.spec.ts`. |
| 12 | `f39fc873` | Records: `web`, `web/editing`, two new `web/` records, the two `cli/` records' viewer sentences, the `local-web-app` term. |
| 13 | `9b3bded3` | `docs/guide/web-viewer.md` rewritten; changelog and release-notes entries; the guide half of the wording test. |

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
   The spec's criterion 1 now says so (review round 1, R4).
2. **An undeclared create target answers 409**, as the spec says, not 400 as
   the plan says.
3. **The blocks test uses a second child project**, `s`, beside the target.
4. **`tcw/serve/work.py` imports `tcw.work.cli`** for `new_item` and
   `blocks_target`, the functions behind `tcw work new` and `edit --blocks`,
   rather than a copy.
5. **In Jira mode, refusing an assignee** was left to the operation.
   Resolved in review round 1 (R3): the server now checks the account ID
   against Jira's assignable users before calling `new`, as Design 9.1 says.
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
    11 quoted "Jira is unreachable", which Design 7.3 gives only as an
    example; `jira.spec.ts` checks the real message. The spec's criterion 11
    now says so (review round 1, R4).
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

## Review round 1

Three adversarial reviewers (server, client, records) reported; the
orchestrator accepted the findings below as belonging to this change. Each
was checked against the code before it was fixed; none turned out wrong.
Fixed on the item's branch in six commits:

| Commit | What |
| --- | --- |
| `cf3e73d5` | Client: fields, forms and saves (C1 to C6, C8 to C11) |
| `ade78c2a` | Browser tests follow the field changes (C7, C8) |
| `89b9dae6` | Packaged client rebuilt |
| `de194614` | Server routes (S1 to S7, R2, R3, R5), with the shared-code changes named below |
| `6a17d9b7` | A Jira-mode parent in another project is kept with a warning in the create form (S5's client half); packaged client rebuilt |
| `ead20973` | Records, guide, release entries and tests (R1, R6, R7, R8) |

The spec was amended on main; its "Review round 1 amendments" section lists
each change. `capabilities.yaml` now also declares
`work/configure-the-work-lifecycle` as changed (S3).

### Server

- **S1, fixed.** In Jira mode, `read` succeeding while `list` failed answered
  400 "not enough values to unpack". The item now shows; `blocks` and
  `children` are empty and `warnings` says the other items could not be read,
  with the backend's message. `error_answer` no longer maps a bare
  `ValueError` to 400: only TCW's own usage errors are 400, and anything
  unexpected is a 500 with its message and no traceback. Three requests
  that had answered 400 through a bare `ValueError` became 500s; review round
  2 (N1) found them and made each a 400 again at the server's boundary. Tests:
  `test_jira_item_shows_when_only_the_other_items_cannot_be_read`,
  `test_an_unexpected_value_error_is_a_500_without_a_traceback`.
- **S2, fixed with a backend predicate.** Every backend now has
  `is_item_folder(folder) -> bool` (in `WorkBackend`, the filesystem and Jira
  backends, and the test memory backend), its own offline rule: a dated name
  holding `item.yaml` on files, a ticket-key name in Jira. The viewer keeps
  only the folders it recognizes, for the URL check, `parent` and
  `blocked-by` references, and the fallback board. `layout.item_folders()` is
  unchanged. Spec Design 7.3, the Design 4 table, 5.2 and the litmus row are
  amended. Tests: `test_a_write_into_a_stray_folder_is_refused`,
  `test_a_reference_to_a_stray_folder_is_refused`,
  `test_a_stray_folder_is_not_on_the_fallback_board`,
  `test_a_stray_folder_is_not_an_item`, and a contract case over all three
  backends, `test_only_its_own_item_folders_are_items`.
- **S3, fixed as decided: hooks run.** Spec Goal 1, Design 1.7 and 6.10 and
  the `work/configure-the-work-lifecycle` record now say adopting a ticket
  runs the request stage's `post` hooks, as `tcw work tickets adopt` does.
  `tickets.adopt` takes a `report` callable (stderr by default, so the CLI is
  unchanged); the route answers `{slug, code, problem}`, and the client opens
  the item and shows `problem` in a callout. Tests against TCW-71's real
  backend over its fake: `test_adopting_runs_the_request_stages_post_hook`,
  `test_a_failed_adopt_hook_keeps_the_item_and_says_what_failed`; client:
  "an item adopted whose post hook failed opens, carrying what failed".
- **S4, fixed.** Round and handoff names use `fullmatch`. Tests:
  `test_a_round_name_must_be_exactly_a_round` (`%0A`, `%0D%0A`, `.mdx`),
  `test_a_handoff_name_must_be_exactly_a_handoff`.
- **S5, fixed by following the spec.** The Jira backend can hold a parent in
  another project when it is a ticket on the same site (`ticket_key`), and
  refuses otherwise with its own message. So the server keeps such a parent
  with the warning and still refuses a cross-project blocker, naming
  `blocked-by`; the create form does the same. Tests:
  `test_jira_create_keeps_another_projects_parent_with_a_warning`; client:
  "in Jira mode another project's parent is kept with a warning, a blocker is
  not".
- **S6, fixed.** `saved()` reads no item when the backend owns the record and
  validates with `None`. Test:
  `test_a_file_save_does_not_ask_a_backend_that_owns_the_record`.
- **S7, fixed by deleting the field.** `Services.open_for_update` was unused;
  `blocks_target` opens the other project itself, as the CLI does.

### Client

- **C1, fixed.** "Refresh from server" confirms, clears the stale flag and
  rereads; the declaration form and its plain-text fallback are keyed on the
  revision, so the old draft goes. Test: "refreshing after a stale save
  replaces the draft, so the next save does not overwrite".
- **C2, fixed.** Refused text stays in the field with its reason and is
  reported to the form (`ui/refusals.ts`); every form using these fields
  refuses to save while one holds refused text, naming each. Tests in
  `reference-input.test.tsx`, `work-forms.test.tsx` and
  `declaration-form.test.tsx`.
- **C3, fixed.** The `tcw://` list re-checks the caret on select, keyup and
  click, and closes when the caret is not at the end of the link being typed;
  Enter after a complete link ends the line. Two tests in
  `shared-components.test.tsx`.
- **C4, fixed.** The Jira assignee shows the display name, sends the account
  ID, treats it as known and does not search again.
- **C5, fixed.** `requestJson` turns a request that gets no answer into a
  failed result ("Could not reach the tcw serve process …"), which every save
  site already shows. `FileEditor.reload` treats only a 404 as "the file is
  gone".
- **C6, fixed.** Opening a stage file, a new round or handoff, properties,
  New item and Tickets all ask first when anything is unsaved; unsaved state
  is tracked per part, including blocks and comment text.
- **C7, fixed.** `jira.spec.ts` checks `.detail-head .edit-btn`;
  `parity.spec.ts` "edits properties" clicks the same.
- **C8, fixed.** Enter commits exactly what was typed; only an arrow key
  picks a suggestion. The Escape steps in `parity.spec.ts` are gone.
- **C9, fixed.** The full list is read only where items are offered, never in
  Tickets or on a Jira-owned page, and kept across board reloads until a save.
- **C10, fixed.** The new item form trims single values.
- **C11, fixed.** The Vocabulary field shows only for a Feature.

### Records, docs and tests

- **R1, fixed.** `test_wording.py` no longer names this item's entries;
  `tests/test_upcoming_entries.py` globs `docs/changelogs/upcoming` as well as
  `docs/release-notes/upcoming`.
- **R2, fixed.** The capability 403 names
  `tcw capabilities set <path> --field <name>=<value>`, checked to make a
  local override and leave the inherited record alone. The taxonomy 403 says
  only "change it there". Tests parse each named command with the real
  parser, and run the capability one.
- **R3, fixed.** In Jira mode the server checks a new item's assignee with
  `tickets.is_assignable` (the assignable-users search with Jira's
  `accountId` parameter, added to the client and the fake) and answers 400
  naming `assignee`. Deviation 5 above is marked resolved. Test:
  `test_jira_create_checks_the_assignee_is_assignable`.
- **R4, fixed.** Spec criteria 1 and 11 amended.
- **R5, fixed.** Restored: an inherited term and an inherited capability read
  by an encoded slash; `tcw://base/C/shared-cap` resolving to
  `base/shared-cap`; a nested capability edited by an encoded slash; a write
  with no `Content-Length` (400, nothing written, answered without waiting
  for a body).
- **R6, fixed.** The guide and `web/see-jira-owned-work-read-only` say a tag
  filter makes two searches; `web/editing` says viewer-only refusals have
  their own wording; the changelog says "while answering" and names the
  browser opener at startup and the adopt hooks; the guide's assignee and
  "refused when sent by hand" sentences are true after R3.
- **R7, fixed.** The release notes say inherited entries are no longer edited
  in the viewer (use `tcw capabilities set`) and 2.x item links no longer
  open.
- **R8, fixed.** The stale CI comment is rewritten.

### Shared code touched

All small: `tcw/work/backend.py` (`is_item_folder` in the protocol),
`tcw/work/fs_backend.py` and `tcw/work/jira/backend.py` (its two
implementations), `tcw/work/jira/client.py` (`account_id` on
`assignable_users`), `tcw/work/jira/tickets.py` (`report` on `adopt`, a new
`is_assignable`), `tests/work/memory_backend.py`, `tests/work/jira/fake.py`
(the `accountId` parameter) and `tests/work/test_backend_contract.py`.
`tcw/work/layout.py` is unchanged.

### Mutation checks

Each new test guarding a blocking or significant fix was broken on purpose
and went red for the stated reason; the file was restored each time.

- S1: the original unpacking put back gave 500 "not enough values to
  unpack"; the sibling read left undegraded gave 503. Mapping `ValueError` to
  400 again turned the 500 test red (400).
- S2: the backend predicate ignored: the fallback board listed `tcw/notes`,
  the write into `notes/` succeeded, and `parent: notes` was accepted. (The
  URL case stayed green, since the filesystem backend's `read` already
  refuses a stray folder.)
- S3: the hook's report not captured: `problem` was null. The `post` hook
  skipped: both adopt tests red.
- R1: with this item's entries removed, as a version cut does, the old
  `test_wording.py` went red and the new tests pass; a changelog entry with
  text before its heading turned `test_upcoming_entries.py` red.
- R2: `tcw capabilities override` back in the message: red; a named command
  with an unknown flag: red at the real parser ("unrecognized arguments");
  the taxonomy message suggesting an override again: red.
- R3: the assignee check removed: "Ann Author" was created (201, not 400).
- C1 and C2 (client): the revision key removed kept the old draft;
  `useRefusals` reporting nothing let five forms save refused text, and the
  old revert-on-blur turned three tests red. S5's client test went red with
  the parent field refusing again.

### Tests run

In a private virtual environment from the worktree, with `HOME` and
`XDG_CONFIG_HOME` in scratch folders: `tests/serve/`, the nine standing
guard files, `tests/work/test_backend_contract.py`, `tests/work/jira/`,
`tests/work/test_layout.py`, `tests/work/test_fs_backend.py`,
`test_capabilities.py`, `test_taxonomy.py`, `test_findings_type.py` and
`test_literal_store_names.py`: 1778 passed, 10 skipped on the branch rebased onto `0e30fca5` (`tests/test_upcoming_entries.py` included; `test_wording.py` is `tests/serve/test_wording.py`, inside `tests/serve/`). `pytest --collect-only -q`:
4626 collected, no errors. Client: vitest 154 passed in 14 files; `tsc --noEmit`,
`eslint web --max-warnings 0` and Prettier on the changed files clean;
`pnpm check:build` passes on the committed tree. Playwright was not run and
no snapshot was refreshed; the snapshot list is unchanged (no e2e edit adds,
renames or removes a screenshot).

## Review round 2

One confirming adversarial reviewer read the six fix commits and the combined
difference after the rebase onto `0e30fca5` (TCW-74). Verdict: **DONE**. It
found no interaction between the two items in `tcw/work/cli.py` or
`tcw/work/layout.py` (TCW-74 changed only `_stage_prompt`, `_procedure` and the
front-matter helpers there, none of which `tcw/serve` uses). It confirmed S1 to
S7, R2, R3, C1, C2, C4, C5, C6 and C9 closed, and asked for the two test-result
placeholders, which were still unfilled when it ran, to be filled in; they are
now. Its three non-blocking findings belonged to this change and were fixed:

- **N1, fixed.** Removing the `ValueError`-to-400 rule (S1) had turned three
  hand-sent requests into 500s: a board tag filter that is not a tag
  (`?tag=!!`), a Jira-mode create with such a tag, and a record body holding a
  lone surrogate (`"\ud800"`), which the store failed on only while writing.
  The server now normalizes tags itself (`_tag` in `tcw/serve/work.py`, for
  the board filter and for the `tags` lists in `changes`) and refuses a request
  body holding text that cannot be written as UTF-8 (`_check_encodable` in
  `tcw/serve/server.py`); all three answer 400 `usage`. The S1 paragraph above
  is corrected. Tests: `test_a_name_that_is_not_a_tag_is_a_usage_error` (both
  backends), `test_jira_create_with_a_name_that_is_not_a_tag_is_a_usage_error`,
  `test_text_that_is_not_valid_utf8_is_refused_and_writes_nothing`.
- **N2, fixed.** Typing in the sidebar filter cleared the record of unsaved
  work before asking, so choosing to stay kept the text but lost the record,
  and the next way off the page did not ask. `navigateTo` now returns whether
  the user agreed to leave, and `updateFilter` applies the filter only then;
  the question is asked once. Test: "staying put when the filter asks keeps
  the filter and the unsaved work".
- **N3, fixed.** The callout for an adopt hook that failed is cleared when the
  browser's Back or Forward changes the page. Test: "what an adopt hook failed
  with does not follow the browser back".
- **X1, needs a separate change.** 2.x viewer and verb text in
  `skills/configure/references/tracker.md` and `projects.md`; added as item 8
  of TCW-75's `notes-from-tcw-74-and-tcw-77.md`.

Mutation checks: with the server changes removed, all four new Python cases
went red (500 instead of 400, and the Jira create reached the backend); with
the `app.tsx` change removed, both new client tests went red (the filter took
"z"; the callout stayed after Back).

Tests after round 2: vitest 156 passed in 14 files; `tsc --noEmit` and `eslint
web --max-warnings 0` clean; Prettier clean on the two changed client files
(the repository-wide `prettify:check` reports 269 unrelated files, as before);
`pnpm build` rebuilt the packaged client. Python: `tests/serve/`, `test_static_guards.py` and `test_no_node.py`, 326 passed. `pnpm check:build` passes on the committed tree. Commits: `b881aea6` (server), `5b0dcf95` (client and the packaged client).
