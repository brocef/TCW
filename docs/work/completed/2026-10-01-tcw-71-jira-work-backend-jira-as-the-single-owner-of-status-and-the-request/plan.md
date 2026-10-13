# Plan — Jira work backend: Jira as the single owner of status and the request

This plan follows the spec as revised after the 2026-10-02 review. Each task
below is one commit, and the suite is green after each one. The order is the
spec's five steps (Risks, "Size"): client and configuration (Tasks 2–6), the
backend (Tasks 7–9), tickets and delegation (Tasks 10–11), validation (Tasks
12–13), then the scenario, the live check, records and documentation (Tasks
14–17). There is no removal step of its own: TCW-70 removes the 2.x tracker
(see below), and Task 14 proves nothing of it is left.

## Before the first task

**TCW-70 must be finished first.** This item is blocked by it. Every task below
builds on what TCW-70's plan creates: `tcw/work/fs_backend.py`,
`tcw/work/open.py` (`open_backend`, `open_project`, `delegate`,
`open_for_update`, `uncommitted_changes`), `tcw/work/record.py`,
`tcw/findings.py`, the new `tcw/work/cli.py` with `resolve_item`,
`tests/work/projects.py`, and the contract module
`tests/work/test_backend_contract.py`. Before Task 1, re-read TCW-70's finished
code against the names used here; where they differ, TCW-70's code wins, and
the first task that uses a name fixes it in this plan in the same commit.

**What TCW-70 already removed.** TCW-70's plan deletes `tcw/tracker/`, every
`tcw work tracker` command, the `work.tracker` parser, the tracker tests, and
the six tracker capability records with the `external-work-tracker` term. It
moves `tcw/tracker/jira.py` to `tcw/work/jira/client.py`, `tests/tracker_fake.py`
to `tests/work/jira/fake.py`, and the transport tests to
`tests/work/jira/test_client.py`. Check that each of those is true before Task
1 (`ls tcw/tracker` fails; `git log --follow tcw/work/jira/client.py` reaches
`tcw/tracker/jira.py`). If the client or the fake is missing, restore it from
the commit before its deletion with `git checkout <commit>^ -- <path>` and `git
mv` it into place, so `git log --follow` still shows where it came from (spec
Design 14). If any other part of the removal list in spec Design 14 survives,
delete it in Task 14 and add what it removes to the documentation allowance
there.

**Which source runs, and the board.** As in TCW-70's plan: the epic branch's
virtual environment, with the checkout as the current directory; the board
edited by hand (`CLAUDE.md`, "Exception"); this item moved to `active` by hand
before Task 1, and its Jira ticket, TCW-71, moved to In Progress by hand.

**Shared names this plan relies on, from TCW-69:** `advance.py`'s post-move
step is private in TCW-69's plan (`_run_post`). Task 10 makes it public as
`run_post` so that `adopt` reuses it (spec Design 7.2) rather than copying it.
`hook_env` and `binding_applies` were made public by TCW-70's Task 6.

**No test reaches the network.** Every test installs the fake in place of the
client's `_request`, as `tests/work/jira/fake.py` already does
(`FakeJira.install`). The only exception is the live scenario run, which
needs `TCW_JIRA_LIVE=1` (Task 15).

## Task 1: The `TCWTEST` checklist (spec Design 15.4, R7)

This comes first so the owner can prepare `TCWTEST` while the code is
written; the live run in Task 15 waits for it.

- **Create**
  `docs/work/backlog/<this item>/tcwtest-checklist.md`, written for a person
  to carry out and tick off, one step per line, each saying how to confirm it:
  1. In `TCWTEST` ("TCW Bridge Test" on proposit.atlassian.net), make sure
     these statuses exist: `Triage`, `To Do`, `Specifying`, `Planning`,
     `In Progress`, `In Review`, `In QA`, `Done`, `Won't Do`. These are the
     names TCW-76 gives TCW's own project (its spec, the `work.stages` block);
     TCW-69 has no default status names, so the spec's "TCW-69's default
     status name" is read as TCW-76's.
  2. Remove any `Start` and `Accept` transitions.
  3. Add one global transition (one that can start from any status) into
     each of those nine statuses, with no screen, except the one into
     `Planning`, whose screen holds only the comment field.
  4. Create the text fields `TCW Project` and `TCW Item`, and put both on the
     create and edit screens of the `Task` type and of the sub-task type.
  5. Create `Effort` and `Complexity` as single-choice lists with the options
     `low`, `medium`, `high`, `very-high` (TCW-69's `SIZES`), on the same
     screens. (They let the scenario edit every property; the spec allows
     both fields to be left unset, but then the scenario could not test them.)
  6. Confirm the `Blocks` issue link type exists.
  7. Name one account whose profile language is not English, or record that
     none is available.
  8. Confirm the account whose credentials run the scenario can create, edit,
     transition and comment in `TCWTEST`, and record whether it is a Jira
     administrator (it decides whether the workflow definition can be read).
- End the checklist with the `work.jira` and `work.stages` configuration the
  scenario uses: site `https://proposit.atlassian.net`, project `TCWTEST`,
  credentials `TCW_JIRA_EMAIL` / `TCW_JIRA_API_KEY` (the variables this
  machine already exports from `~/.bashrc`), the four fields above, and every
  optional stage enabled with the nine statuses of step 1. The project id is
  `tcw-test-live`, which the `~` question of Design 15.4 needs.
- **Proof:** none in the suite; it is a document. Ask the owner to apply it
  and say when it is done.

## Task 2: The client (spec Design 14; part of AC 20)

- **Modify** `tcw/work/jira/client.py`:
  - `JiraClient(config)` reads `site`, `credentials` and `timeout` from the
    `JiraConfig` of Task 3 by attribute, as it reads `TrackerConfig` today
    (`jira.py:115-124` before the move). The docstring naming
    `TrackerConfig` and the messages naming `work.tracker` (`:119`, `:146`,
    `:421`) name `JiraConfig` and `work.jira`.
  - **Changed:** `search(jql, fields)` posts to `/rest/api/3/search/jql` and
    follows `nextPageToken` until the last page, returning every issue;
    `transitions(key)` quotes the key and always sends
    `expand=transitions.fields`, returning each transition's id, name,
    destination status and screen field ids; `create_issue(fields)` takes the
    whole `fields` mapping; `apply_transition(key, transition_id, comment=None)`
    adds the comment in `update` when given; `recent_comments` becomes
    `comments(key, limit)`, paging with `startAt`/`maxResults` newest first
    and returning author account id, author display name, `created` and
    body.
  - **Added:** `edit_issue(key, fields=None, update=None)`,
    `add_link(type_name, inward_key, outward_key)`, `delete_link(link_id)`,
    `user(account_id)`, `assignable_users(project, query, limit)`,
    `project(key)`, `project_statuses(key)`,
    `create_metadata(project, issue_type_id)`, `link_types()`,
    `workflows(project, issue_type)`.
  - **Dropped:** `assign`, `description`, and the module's
    `_document_text` (replaced by Task 4's `document_text`).
  - `_request`, the error classes, `_for_status` and the shape guards are
    unchanged. Every new method goes through `_request`, and every path segment
    taken from data goes through `urllib.parse.quote(…, safe="")`.
- **Modify** `tests/work/jira/test_client.py`: one test per new or changed
  method, through a recorded `_request` stub, asserting method, path (with a
  key containing a character that needs quoting), query and body; paging for
  `search` (three pages) and `comments` (150 comments in pages of 50); and the
  existing "every operation passes a timeout" test (`:285` before the move)
  extended to every public method.
- **Proof:** `pytest tests/work/jira -q`.

## Task 3: `work.jira` configuration (spec Design 1, 8 step 1; AC 1)

- **Create** `tcw/work/jira/config.py` with:
  - `JiraConfig` (frozen): `site`, `project`, `email_env`, `token_env`,
    `fields` (`project`, `item`, `effort`, `complexity`), `priorities` (a full
    mapping, with the five defaults filled in), `issue_type` (default
    `Task`), `inbox_query`, `timeout` (default 15);
  - `parse_jira_config(mapping) -> tuple[JiraConfig | None, list[ConfigProblem]]`,
    using TCW-69's `ConfigProblem` and key paths under `work.jira`, with every
    rule of Design 1's table, unknown keys refused at every level, and a
    malformed credential name reported by key and rule, never by value;
  - `DelegationTarget` (frozen: `site`, `project`, `inbox_status`, `email_env`,
    `token_env`, `project_field`) and `parse_delegation_block(mapping, where)`
    for the optional `jira` block of a connected-project entry (Design 8 step
    1), with the same rules.
- **Modify** `tcw/store/base.py` `parse_connected_entry` (around 2719-2840) to
  accept an optional `jira` key and keep its value, unparsed, on
  `ConnectedProject.jira` (a new field, default `None`). The store layer
  imports nothing from `tcw.work`, so its shape is checked by
  `parse_delegation_block` when delegation reads it (Task 11) and by offline
  `validate` (Task 12).
- **Modify** `tcw/work/open.py` `open_backend`: for `backend: jira`, run
  `parse_jira_config` on `work.jira` and raise `BackendError` naming every
  problem. It still raises "arrives with the Jira backend" after a clean parse
  until Task 7.
- **Create** `tests/work/jira/test_config.py` (AC 1), including the test that
  no parse result or problem message contains a credential variable's value
  (set the variable to a sentinel, parse, and search every field and message).
- **Proof:** `pytest tests/work -q`, plus `tests/test_project_registry.py` for
  the connected-entry change.

## Task 4: Text and property mapping (spec Design 3, 14; AC 16's round trip)

- **Create** `tcw/work/jira/mapping.py` with:
  - `text_document(text)`, `document_text(node)` and `normalize_text(text)`,
    exactly as Design 14 describes;
  - `read_props(fields, config, field_ids, registered_tags, enabled_stages)`
    turning a ticket's `fields` into title, stage (exact status-name match, or
    `None`), `created` (converted to UTC, then its date), priority (`None` when
    unmapped or absent), effort and complexity (option value lower-cased with
    spaces as `-`, `None` when not a scale name), tags (the registered labels,
    in Jira's order), assignee (account id), and the raw parent and blocker
    keys for Task 7 to resolve;
  - `write_fields(changes, config, field_ids, has_priority)` and
    `label_updates(added, removed)` building the `fields` and `update`
    sections of one edit (Design 4.2), and the create body (Design 4.1 step
    2).
- **Create** `tests/work/jira/test_mapping.py`: AC 16's two text cases and
  the fixed list of texts; `created` with three offsets landing on the same
  UTC date and one crossing midnight; every row of Design 3's table, including
  the `None` readings.
- **Proof:** `pytest tests/work/jira -q`.

## Task 5: JQL and the fake's query evaluator (spec Design 6, 7.1, 15.1; AC 12)

- **Create** `tcw/work/jira/jql.py` with `quote(text)` (wrap in `"`, escape
  `\` and `"`), and the builders `item_query(config, field_ids, query,
  stage_statuses)`, `inbox_query(config, field_ids, inbox_status)` (with the
  `(<default>) OR (<inbox-query>)` union), `keys_query(keys)` (at most 100)
  and `sample_query(project, issue_type, status)` for Task 13. Custom fields
  appear only as `cf[<id>]`; no builder emits `~`.
- **Create** `tests/work/jira/fake_jql.py`: a parser and evaluator for exactly
  the shapes `jql.py` emits (`=`, `IN`, `NOT IN`, `IS EMPTY`, `IS NOT EMPTY`,
  `AND`, `OR`, parentheses, `ORDER BY created`), with `labels IN` matching any
  listed label, and a switch to compare labels without regard to case. Any
  other shape raises, so a new clause in `jql.py` cannot pass silently.
- **Create** `tests/work/jira/test_jql.py` (AC 12): escaping; every builder,
  over a table of inputs covering each clause alone and all combined, produces
  a query `fake_jql` parses; no query contains `~` (AC 11's last line);
  `cf[` appears for custom fields and no field display name does.
- **Proof:** `pytest tests/work/jira -q`.

## Task 6: The fake Jira (spec Design 15.1)

- **Modify** `tests/work/jira/fake.py` so `FakeJira` answers every endpoint
  the client calls after Task 2: create, edit (fields and label `update`
  operations), read, comments with paging, links (create, delete, read back on
  both tickets), transitions with screen fields, project, statuses, create
  metadata per issue type (with a switch to drop Priority), edit metadata,
  link types, users and assignable users, `myself`, workflow definitions, and
  `search/jql` with `nextPageToken` paging through `fake_jql`.
- Its switches, each a keyword or method: workflow definitions answer 403;
  refuse a transition that carries a comment; require a screen field on a
  named transition; drop the connection after applying the next write; refuse
  a whole `key in` search that names a missing key with 400; leave tickets
  written in the last N requests out of searches while still answering direct
  reads; leave a field off an issue type's edit screen, so `editmeta` omits it
  and an edit of it answers 400; answer every request as unreachable; answer
  401; answer 429 with `Retry-After`.
- Issue types carry hierarchy levels (Epic 1, Task 0, a sub-task type flagged
  `subtask` and named `Subtask`, so no test passes by matching `Sub-task`).
- It keeps a log of write requests (`writes()`, as today) so "nothing written"
  is checkable.
- **Create** `tests/work/jira/test_fake.py`: a small check of each switch, so
  a later test that relies on one is not relying on a switch that does nothing.
- **Proof:** `pytest tests/work/jira -q`.

## Task 7: `JiraBackend`, reading (spec Design 2, 3, 6, 10; AC 3, 4, 11, 20, the reads of AC 26)

- **Create** `tcw/work/jira/backend.py` with:
  - `KEY_FOLDER` and `KEY` patterns (Design 2.1, 2.4).
  - `JiraBackend(project, work_path, config, jira_config, *, client=None,
    report=None)`, with `external_stages = frozenset({request, qa})` taken from
    the stage table by name lookup (`model.stage(...)`), never as literals in
    logic, and `inbox_items = False`. Per command it reads, once and lazily, the
    project (`project`), its issue types with their levels, and the create
    metadata of the configured issue type, from which it resolves field
    display names to ids (Design 12) and learns whether Priority exists. It
    reads `myself` at most once.
  - **One place that turns client errors into `tcw/errors.py` classes**
    (Design 10's table): a context manager `_jira()` wrapped around every
    client call. A 429 becomes `Unreachable` naming `Retry-After`; there is no
    retry.
  - `lookup(name)` (no network), `read(folder)` with the different-key warning,
    `list(query)` (Design 6: paging, the default and `all` status clauses, the
    tag rule with no request when no given tag is registered, TCW Project
    matched after the search, tickets whose folder is missing left out and
    named on stderr), `read_request`, `read_comments` and `current_user` (R3:
    `None` with no request when a variable is unset; `None` with one stderr
    line naming the cause when `myself` fails).
  - `_resolve_keys(keys)` (Design 3.1): folder lookup first; then `key in`
    searches of up to 100; a search refused with 400 falls back to one direct
    read per key; any key a search did not return is read directly; leftover
    keys are `untracked`, parent first, no key twice.
  - Each `Item` built through Task 4's `read_props`.
- **Modify** `tcw/work/open.py`: `open_backend` returns `JiraBackend` for
  `backend: jira`; `open_project` opens a Jira-mode project on this machine the
  same way (Design 8; a declared but absent one is still `Unreachable`).
- **Modify** `tcw/work/cli.py` `resolve_item`: in Jira mode, text matching
  `KEY` goes through `lookup`, and `None` is `NotFound` (Design 2.6, R6). In
  filesystem mode the branch is not taken.
- **Create** `tests/work/jira/conftest.py` with a `jira_project` fixture: a
  `make_project` fixture project in Jira mode whose `tcw-config.yaml` names the
  fake's site, project, fields and the nine statuses of Task 1, with the fake
  installed and the credential variables set; and `fake` for direct setup.
- **Create** `tests/work/jira/test_read.py` (AC 3 including the R6 typing
  cases through `tcw work show`, AC 4, the reads of AC 26) and
  `tests/work/jira/test_list.py` (AC 11, including the request-count budget:
  250 items over pages of 100 make exactly three item searches and one `key
  in` search, and no single-issue `GET`), and `tests/work/jira/test_errors.py`
  (AC 20: each row of the table through `read`, and a 429 making exactly one
  request).
- **Proof:** `pytest tests/work -q`.

## Task 8: `JiraBackend`, writing (spec Design 4, 5, 11, 13; AC 5–9, 15, 16)

- **Modify** `tcw/work/jira/backend.py`, adding:
  - `choose_transition(transitions, target_status) -> Transition | Refusal`,
    the choice rule of Design 5 step 2, as a public function: `create`,
    `adopt`, delegation and `validate --remote` all call it.
  - `child_issue_type(parent_level)` and the parent check of Design 11.
  - `_resolve_assignee(value)` (Design 4.2: account id first, then assignable
    users; none is `NotFound`, several `Refused` listing up to ten).
  - `create` in the seven steps of Design 4.1, each stopping point raising the
    outcome its table gives, with the key or slug carried so the CLI prints it
    on stdout (`Refused(name=key)`; `BackendError` carrying the key for steps
    4–7).
  - `update` (Design 4.2: one edit request, then link requests; links that
    already exist or are already gone are skipped after reading the current
    links; the partial-failure message naming each link made and not made).
  - `comment` (one request, ADF through `text_document`).
  - `rename` (Design 4.4: TCW Item first, then the folder, then a best-effort
    restore; other mentions of the old slug reported, none edited).
  - `set_stage` (Design 5: read transitions, choose, apply with the note,
    read back; the 400 and dropped-connection paths exactly as the spec
    lists them, with the note found by comparing `normalize_text` of the
    newest ten comments).
- **Create** `tests/work/jira/test_write.py` (AC 5, 6, 7, 8, 15, and AC 16's
  `comment` and multi-line-note cases) and `tests/work/jira/test_set_stage.py`
  (AC 9, every bullet, each asserting through the fake's write log that
  nothing else was written).
- **Proof:** `pytest tests/work -q`.

## Task 9: `advance` in Jira mode, and the shared contract (spec Design 15.3a; AC 10, part of AC 25)

- **Create** `tests/work/jira/test_advance.py` (AC 10): through
  `tcw work advance`, `discard` and `path` against the fake; the qa rules come
  from TCW-69's `advance`, unchanged.
- **Modify** `tests/work/test_backend_contract.py`:
  - the `backend` fixture gains a third parameter, `JiraBackend` over the
    fake;
  - each case that depends on a declared fact reads the fact and skips with a
    reason naming it (`pytest.skip(f"{type(b).__name__}: inbox_items is
    false")`), never by naming the backend: a case that creates an item at
    the inbox stage runs only when `inbox_items` is true; a case that writes or
    reads a stage's files runs only when that stage is not in
    `external_stages`; a case that depends on a folder's name takes it from
    what `create` returned;
  - the fixture gives each backend a way to put an item in no stage (the
    memory backend's `stage=None`, a hand-written `stage:` value for the
    filesystem, an unmapped status in the fake), so the no-stage cases run on
    all three rather than being skipped.
  - **The skip list.** TCW-70's contract module does not exist yet, so the
    exact cases cannot be named here. Expected from TCW-69's and TCW-70's
    plans: only the cases that place an item at the inbox stage (the default
    listing's inbox item, and `Query(stages={inbox})`) skip for `JiraBackend`,
    by `inbox_items`; none skips by `external_stages`, because the contract
    reads the request through `read_request`. At implement, list every case
    skipped for `JiraBackend`, with its reason, in the implement round. A case
    skipped for any other reason, or marked to fail, fails AC 25 and is fixed
    instead.
- **Proof:** `pytest tests/work -q`.

## Task 10: The Jira inbox and display helpers (spec Design 7; AC 13, 14, the helpers of AC 26)

- **Modify** TCW-69's `tcw/work/advance.py`: make `_run_post` public as
  `run_post(backend, config, layout, project_root, slug, *, stage,
  from_stage)`, unchanged in behavior, and have `advance` call it. Its tests
  in `tests/work/test_advance.py` still pass.
- **Create** `tcw/work/jira/tickets.py` with:
  - `inbox(backend) -> list[dict]` (Design 7.1: the query, the union with
    `inbox-query`, then only what `adopt` would accept without a further
    request);
  - `adopt(backend, key, *, config, layout, project_root) -> tuple[str, int]`
    (Design 7.2: read; the step 2 refusals; resuming; set both fields in one
    edit; folder and `item.yaml`; move to request with the choice rule and read
    back; `run_post` once, giving exit 6 when it fails; stdout slug);
  - `ticket_link(folder)`, `user_name(account_id)` (answered from names seen
    in this command's responses first) and `assignable_users(query, limit=20)`
    (Design 7.3).
- **Modify** `tcw/work/cli.py`: add `tickets list [--json]` and
  `tickets adopt <KEY>`. In filesystem mode both are usage errors (exit 2).
  `tickets list` prints one key per line, its `--json` the fields of Design
  7.1 with `description` through `document_text`; stderr carries the count and
  the JQL.
- **Create** `tests/work/jira/test_tickets.py` (AC 13, 14 including every hook
  case, and AC 26's helper bullet).
- **Proof:** `pytest tests/work -q`.

## Task 11: Delegation into a Jira-mode project (spec Design 8; AC 17)

- **Modify** `tcw/work/jira/tickets.py`, adding `delegate_to_jira(target,
  title, request, priority, *, here) -> str`, the five steps of Design 8. The
  target's settings come from its tracked `tcw-config.yaml` when it is on this
  machine, otherwise from the delegator's connected-project `jira` block
  through `parse_delegation_block`; site and credential names always come
  from the same one. The "create the item" step uses TCW-70's
  `uncommitted_changes`.
- **Modify** `tcw/work/open.py`:
  - `delegate`: the branch for a declared, absent target with a `jira` block
    calls `delegate_to_jira`, replacing the "arrives with the Jira backend"
    error; a Jira-mode target on this machine calls it too (TCW-70's spec
    Design 6.5);
  - `open_for_update`: a Jira-mode target on this machine returns its
    `JiraBackend`; a target known only through a `jira` block stays refused
    (exit 3).
  - With `--project` against a Jira target, any property flag other than
    `--priority` is already a usage error in TCW-70's command; nothing changes.
- **Modify** TCW-70's `tests/work/test_open.py`: the cases that expected
  "arrives with the Jira backend" now expect the delegated ticket (exit 0,
  key on stdout); the `open_for_update` refusal for a `jira`-block-only target
  is unchanged.
- **Create** `tests/work/jira/test_delegate.py` (AC 17), with two
  `make_project` projects, the target in Jira mode, and the fake answering
  for the target's site.
- **Proof:** `pytest tests/work -q`.

## Task 12: Offline `validate` and work links in Jira mode (spec Design 9.1, R20; AC 2, 19)

- **Modify** `tcw/work/jira/backend.py`, adding
  `jira_store_problems(work_path, jira_config) -> list[Finding]`, a plain
  function (no network): each folder against `KEY_FOLDER`; `item.yaml` with
  exactly one key `ticket`, its site equal to `work.jira.site` and its key
  equal to the folder's (errors); duplicate keys (error); a `request/` or
  `qa/` folder in an item (warning saying Jira owns that stage and the folder
  is ignored). It uses `tcw/findings.py`'s `Finding`.
- **Modify** `tcw/validate.py` `_work_findings` (TCW-70): in Jira mode it
  returns the `work.jira` parse problems (Task 3), each connected-project
  `jira` block's problems, and `jira_store_problems`, and nothing that needs
  Jira.
- **Modify** `tcw/refs.py` `_resolve_work` (TCW-70): a work link into a
  Jira-mode project is resolved by the folder scan `lookup` uses, never by
  `read` (R20), through a function `link_exists(work_path, folder)` in
  `backend.py`.
- **Create** `tests/work/jira/test_validate_offline.py` (AC 2 and AC 19).
  Both install a `_request` that fails the test if called, and unset the
  credential variables.
- **Proof:** `pytest tests/work -q`.

## Task 13: `tcw validate --remote` (spec Design 9.2; AC 18)

- **Create** `tcw/work/jira/remote.py` with `remote_findings(backend,
  layout, reader) -> tuple[list[Finding], list[str]]` (findings, and stderr
  narration of what passed or was skipped), running checks 1–8 of Design 9.2
  in order:
  1. access (`myself`, then `project`); a rejected credential stops this
     project's remaining checks, with a stderr line;
  2. fields, on the create screen (create metadata for the configured type
     and the sub-task type) and the edit screen (`editmeta` on one sample
     ticket per checked type, found with `jql.sample_query`; no sample gives
     an `unchecked:` warning naming the type); the field kinds and options;
     priority names; the `Blocks` link type;
  3. statuses per checked type;
  4. and 5. the needed moves, from the workflow definition when it can be read
     (a global transition counts from every status), else from sample
     tickets; several candidates are decided by a sample ticket and the choice
     rule; no sample is an `unchecked:` warning naming source, target and
     issue type; a needed transition whose screen requires a field is an
     error; when only the definition was read, stderr says screen fields were
     not checked;
  6. checked types: the configured type plus each type an existing item's
     ticket has;
  7. items and tickets, with `key in` batches and direct reads for anything
     missing or in a refused batch, then the six checks;
  8. TCW-69's `stage_problems`, `reference_problems` and
     `records_problems(…, finished=False)` over items at a non-terminal stage,
     each turned into a `Finding` with TCW-73's severity (Design 6.2 of
     TCW-73: records problems errors, the other two warnings).
  On `Unreachable` it stops and returns what it has plus one `unresolved`
  finding for the project.
- **Modify** `tcw/cli.py`: `tcw validate` gains `--remote`. In filesystem mode
  it is a usage error (exit 2, as TCW-73's spec says). In Jira mode the
  offline checks run as before; then `remote_findings`, whose findings are
  printed on stdout with `str(finding)` and whose narration goes to stderr.
  Exit 5 when Jira could not be reached, else 1 with any error, else 0.
  (TCW-73 later moves every `validate` finding to stdout; until then, only
  `--remote`'s findings are there, because this flag is new and follows
  TCW-73's form from the start.)
- **Note for TCW-73's plan.** TCW-73's spec (its Design 6.1 step 6) says
  TCW-71 runs two of the three model checks and TCW-73 adds
  `records_problems`; TCW-71's spec, revised later at its review, runs all
  three. This task runs all three, so TCW-73 has nothing to add there; its
  plan should say so.
- **Create** `tests/work/jira/test_validate_remote.py` (AC 18, every bullet,
  with "no write request" asserted from the fake's log in each case).
- **Proof:** `pytest tests/work -q`.

## Task 14: The scenario against the fake, and the guards (spec Design 15.4, 16; AC 21, 22, the fake half of AC 23, AC 25)

- **Create** `tests/work/jira/scenario.py`: the ten steps of Design 15.4 as
  one function `run(project_root, *, live)` that drives the commands through
  `tcw.cli.main` and asserts what each ticket shows after each step. Step 1's
  `list` retries once a second for up to 60 seconds and returns how long it
  took. Step 10's `validate --remote` result is returned for the record.
- **Create** `tests/work/jira/test_scenario.py`: one test runs the scenario
  against the fake; a second runs it against the real site, skipped unless
  `TCW_JIRA_LIVE=1` and the credential variables are set, reading its
  configuration from Task 1's checklist values.
- **Create** `tests/work/jira/test_guards.py`:
  - AC 21: `tcw/tracker` does not exist; no `.py` file under `tcw/`
    contains `work.tracker`, `tracker_strict`, `tracker.yaml`, `tcw.tracker`
    or `TrackerConfig` (`tcw/serve/dist/` is not scanned, being no `.py`);
    `tcw work tracker --help` exits 2; a config with `work.tracker` names the
    migration guide.
  - AC 22: no module in `tcw/work/jira/` imports `subprocess` or refers to
    `os.system` or `os.popen` (an `ast` walk); and, in a temporary git
    repository with one commit, `create`, `rename` and `tickets adopt` against
    the fake leave `git rev-parse HEAD` and `git for-each-ref` unchanged and
    `git status --porcelain` showing only the item folders they wrote, as
    untracked.
  - Mutation-check each by hand (add `import subprocess` to
    `tcw/work/jira/mapping.py`; add the string `tracker.yaml` to
    `tcw/work/jira/backend.py`), and record the results in the implement round.
- If anything on Design 14's removal list is still present (see "Before the
  first task"), delete it here and add each removed command or key to
  `tests/doc_allowance.py`.
- **Proof:** `pytest -q`, the full suite (AC 25).

## Task 15: The live check against `TCWTEST` (spec Design 15.2, 15.4; AC 23, 24)

This task waits for the owner to confirm that Task 1's checklist was applied.

- **Create** `tests/work/jira/capture.py`, a helper the live test uses when
  `TCW_JIRA_CAPTURE=<dir>` is set: it wraps `_request`, and writes each
  endpoint's response body (one file per endpoint and status) after replacing
  account ids, email addresses, display names and the site's host with fixed
  values.
- **Run**, from the branch checkout, with the credentials loaded
  (`source ~/.bashrc >/dev/null 2>&1; TCW_JIRA_LIVE=1
  TCW_JIRA_CAPTURE=tests/work/jira/recorded pytest
  tests/work/jira/test_scenario.py -k live -s`). Save its output in the
  implement round.
- **Record in the implement round** an answer to each of the ten questions of
  Design 15.4, each with the evidence from the run. The scenario prints what
  it needs for each (the link as Jira reports it on both tickets; the response
  to a comment on a transition with no screen; the response to a
  cross-project parent; whether `workflows` answered or was refused; the
  `fields` of the no-screen and comment-only transitions; a search with
  `cf[<TCW Project>] ~ "tcw-test-live"` against tickets valued
  `tcw-test-live`, `tcw-test` and `live`; a `key in` naming a missing key; the
  measured lag; the offset on `created`; status names read with the
  non-English account, if one exists).
- **Where an answer contradicts the design** (for example `Blocks` read the
  other way round), fix the code and its fake in this task if the change stays
  inside one function; otherwise stop, return to the spec, and say so.
  Translated status names, if Jira translates them, become a new work item
  rather than a fix here (spec Risks).
- **Create** `tests/work/jira/test_recorded_shapes.py` (AC 24): for each
  recorded endpoint, every key path the backend reads from it is present, at
  the same nesting, in the fake's answer to the same request; no recorded file
  contains `@` or `proposit.atlassian.net`.
- **Commit:** `tests/work/jira/recorded/`, `capture.py` and the shape test.
- **Proof:** `pytest tests/work/jira -q`; the live run itself, by hand.

## Task 16: Capability and taxonomy records (spec "Capability changes"; part of AC 21)

Written by editing files, as in TCW-70's Task 12.

- **Check first** that the six tracker records and `external-work-tracker` are
  gone (TCW-70's Task 12). Any left is deleted here.
- **Create** `docs/capabilities/work/keep-work-items-in-jira/`,
  `adopt-a-jira-ticket/` and `check-a-jira-project-against-the-stage-mapping/`,
  each with a new unused `cap-` id, `Status: Supported`, a `Subject` naming
  `work-item`, and a description of what the spec's table says.
- **Modify** `docs/capabilities/work/delegate-a-work-item-to-another-project/`
  (TCW-70's new record) to cover Jira-mode targets: the ticket in the target's
  inbox, the item created when the target's folder can be, and the
  connected-project `jira` block for a target not on this machine.
- **Taxonomy:** **create** the Feature `docs/taxonomy/jira-work-backend/`; link
  the three new records to it. **Modify** `docs/taxonomy/configure-skill/meta.yaml`
  to name `jira-work-backend` in `relatesTo`. TCW-70 already dropped its
  reference to `external-work-tracker`; the spec's "must name
  `jira-work-backend` instead" is read as adding it.
- **Create** `docs/work/backlog/<this item>/capabilities.yaml` in TCW-69's
  declaration schema: `new` (the three records), `changed` (the delegation
  record), and `taxonomy` `new: [jira-work-backend]`, `changed:
  [configure-skill]`. Check it with TCW-69's records gate by calling
  `records_problems(layout, slug, ledger_reader(...), finished=True)` from a
  short Python snippet against this repository's ledgers (this repository's
  board is still 2.x, so `advance` cannot run it), and record the output in
  the implement round.
- Run the released 2.8 `tcw validate` from the branch checkout
  (`pipx run --spec tcw-cli==2.8.1 tcw validate`), as TCW-70's Task 12 does,
  and record the result.
- **Proof:** `pytest -q`.

## Task 17: Documentation sync and the full suite (spec Design 17; AC 25, 27)

**Documentation Sync.** Each documentation entry, evaluated against this
change:

| Entry | Trigger | Fires? | Action |
| --- | --- | --- | --- |
| `README.md` | Public-API | Yes: Jira mode, `tickets list`, `tickets adopt`, `validate --remote`. | Deferred to TCW-75 (spec Non-goals). |
| `docs/guide/jira.md` | Tracker-Change | Yes: the whole Jira integration changes. | Deferred to TCW-75 (spec Non-goals). |
| `docs/guide/<topic>.md` | Guide-Topic-Change | Yes: `work.jira`, the connected-project `jira` block, what `item.yaml` holds in Jira mode. | Deferred to TCW-75. |
| `docs/release-notes/upcoming/<slug>.md` | Public-API | Yes | **Create** `docs/release-notes/upcoming/2026-10-01-tcw-71-jira-work-backend-jira-as-the-single-owner-of-status-and-the-request.md`, first non-blank line a `##` heading, plain language: Jira as the one home of status and the request, ticket-first items, one transition per move, the Jira inbox and adoption, QA on the ticket, delegation into a Jira project, `validate --remote`, and that `work.jira` replaces `work.tracker`. |
| `docs/changelogs/upcoming/<slug>.md` | Any-Code-Change | Yes | **Create** `docs/changelogs/upcoming/2026-10-01-tcw-71-jira-work-backend-jira-as-the-single-owner-of-status-and-the-request.md` with `## Added` (the `tcw/work/jira/` modules, `tickets list`/`adopt`, `validate --remote`, the connected-project `jira` block), `## Changed` (the client's methods, `run_post` made public, `resolve_item`'s key branch, Jira delegation) and `## Internal` (the fake, the JQL evaluator, recorded responses, the scenario). |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | Yes | Deferred to TCW-74 (spec Non-goals). |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | Yes: `work.jira` is new. | Deferred to TCW-75 (spec Non-goals). |

Then:

- AC 27: the release-notes entry passes `tests/test_upcoming_entries.py`
  (TCW-70's Task 13); every command or key this slice removes is either in no
  document or in `tests/doc_allowance.py`, whose guard test passes.
- run the `documentation-sync` skill over the finished diff and confirm the
  table;
- run `pytest -q` bare from the branch checkout (AC 25).

**Commit:** the two entry files.

## Verification

**What the suite cannot check:**

- **The live run** (AC 23) is by hand, once at implement (Task 15) and again
  at review. Its output and the ten answers are kept in the implement round;
  the review run's output in the review round.
- **The fake can still be wrong about Jira** in ways the recorded shapes do
  not catch (behavior, not shape: which transition Jira offers after a move,
  how it orders comments). The scenario run against `TCWTEST` is the check;
  when the live run and the fake disagree on a step, the fake is changed to
  match Jira, never the scenario's assertion.
- **Mutation checks** for the guards in Task 14, recorded in the implement
  round.
- **A hand trace** in a scratch Jira-mode project on `TCWTEST`: `tickets
  list`, `tickets adopt`, `advance` to qa, a rejection with a reason, an
  acceptance, and `validate --remote`. Paste it into the implement round. It
  can be the live scenario's output if that shows each step.

## Notes

- **Blockers.** This item is blocked by TCW-70, and TCW-73 by this item;
  nothing new to record.
- **The owner's part.** Task 1's checklist must be applied to `TCWTEST` before
  Task 15. Everything else runs without the owner.
- **Completing this item.** By hand, as for TCW-69 and TCW-70, with the
  Jira ticket TCW-71 moved by hand.
- **Choices this plan makes that the spec leaves open**, for review:
  1. The connected-project `jira` block is kept unparsed by the store layer
     (`ConnectedProject.jira`) and checked by `tcw/work/jira/config.py`, so
     `tcw/store/` keeps importing nothing from `tcw.work`.
  2. TCW-69's `_run_post` is made public as `run_post`, so `adopt` reuses the
     post-move step rather than copying it (spec Design 7.2 says "reuses").
  3. `choose_transition` is one public function in `backend.py`, used by
     `create`, `adopt`, delegation and `validate --remote`.
  4. `tcw validate --remote` prints its findings on stdout from the start, in
     TCW-73's form, while the offline findings stay where TCW-70 left them
     until TCW-73 moves them.
  5. The `TCWTEST` statuses are TCW-76's names, since TCW-69 defines none; the
     checklist adds `Effort` and `Complexity` fields so the scenario can edit
     every property.
  6. `configure-skill` gains `jira-work-backend` in `relatesTo`, reading the
     spec's "instead" as an addition now that TCW-70 has dropped the old one.
- **Cross-slice note for TCW-73's plan:** this plan runs all three model
  checks under `--remote` (Task 13); TCW-73's spec still says it adds the
  third.
- **Self-review.** Every acceptance criterion maps to a task:
  - AC 1: Task 3;
  - AC 2: Task 12;
  - AC 3, 4: Task 7;
  - AC 5–8: Task 8;
  - AC 9: Task 8;
  - AC 10: Task 9;
  - AC 11: Task 7 (its last line, no `~`, also Task 5);
  - AC 12: Task 5;
  - AC 13, 14: Task 10;
  - AC 15, 16: Task 8 (the round trip in Task 4);
  - AC 17: Task 11;
  - AC 18: Task 13;
  - AC 19: Task 12;
  - AC 20: Task 7 (the client's side in Task 2);
  - AC 21: Task 14 and Task 16;
  - AC 22: Task 14;
  - AC 23: Task 14 (fake) and Task 15 (live), with the checklist in Task 1;
  - AC 24: Task 15;
  - AC 25: Task 9 (contract) and Tasks 14 and 17 (whole suite);
  - AC 26: Task 7 (reads) and Task 10 (helpers);
  - AC 27: Task 17.

  Task 6 is infrastructure for every test from Task 7 on.
