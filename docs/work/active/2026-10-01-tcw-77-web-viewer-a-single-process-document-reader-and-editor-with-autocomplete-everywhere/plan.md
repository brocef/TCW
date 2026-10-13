# Plan — Web viewer: a single-process document reader and editor with autocomplete everywhere

This plan follows the spec as reviewed on 2026-10-02. Each task is one commit
on `work/2026-10-01-tcw-77-web-viewer-a-single-process-document-reader-and-editor-with-autocomplete-everywhere`,
made from `epic/tcw-3.0` at `58da5913`, and the tests the task names pass
after it. The order is the spec's own phasing: first the work-layer helpers
the viewer calls (Task 1), then the one-process server with its security and
its static files, still serving today's client (Task 2), then the work API in
three steps, reads, files and writes (Tasks 3–5), then the taxonomy and
capability rules (Task 6), then the client (Tasks 7–9), then the guards that
read both halves (Task 10), the Jira browser fixture and the browser tests
(Task 11), and the records and documents (Tasks 12–13). Mutation checks and
the collection check close it (Task 14).

## Before the first task

**What the earlier children left, read on the branch at `58da5913`.**

- `tcw/serve/runtime.py` still checks for Node 22.12, starts the Python API
  as a private sidecar with a token, starts `dist/server.cjs` under Node and
  prints `Serving TCW at <url>` on stdout without flushing (`runtime.py:178`).
  Its "no tcw node here" message predates TCW-73's `NO_PROJECT`.
- `tcw/serve/__init__.py` holds the taxonomy, capability and `/api/resolve`
  routes and TCW-70's stub (`_work_stub`): `GET /api/work` and
  `GET /api/work/tags` answer `[]`, every other `/api/work…` is 404. It still
  reads `include_descendants` and `_hosted_projects` for `/api/resolve`.
  Writes check `Content-Type` and `_is_loopback_origin`; reads are guarded
  only by the sidecar token. A failed write check answers 400.
- `tcw/cli.py:_cmd_serve` raises `BackendError(NO_PROJECT)` outside a
  project, checks the project graph, ends the per-command configuration cache
  (TCW-72 Design 2.3, kept here) and calls `serve(..., include_descendants=True)`.
- The 3.0 work layer: `tcw/work/backend.py` (`WorkBackend`, `Query` with
  `tags`, `Comment`), `tcw/work/model.py` (`STAGES`, `PRIORITIES`, `SIZES`,
  `Changes`, `Slug`, `inbox_stage`, `start_stage`), `tcw/work/layout.py`
  (`Layout.path`, `next_round`, `round_verdict`, `current_verdict`,
  `handoff_path`; no folder listing), `tcw/work/record.py` (`item_record`),
  `tcw/work/open.py` (`open_backend`, `open_project`, `delegate`,
  `open_for_update`, `work_path`, `read_work_config`), `tcw/work/gates.py`
  (`parse_declarations`, `records_problems`), `tcw/work/jira/tickets.py`
  (`inbox`, `adopt`, `ticket_link`, `user_name`, `assignable_users`, each
  refusing a non-Jira backend with `UsageError`), `tcw/validate.py`
  (`ValidationTarget(axis="work", ref=<folder>, item=<Item>)`).
- `tcw/work/cli.py` holds the logic behind `new` and `edit --blocks` inside
  its argument handlers (`_new`, `_edit`), and `_readable` (every readable
  item, for `blocks` and `children`) inside the CLI.
- The client (`web/client/src/`) is still the 2.x work client: 2.x statuses,
  the start, complete and drop dialogs, sidecars, plan stages, the desktop
  opener, `initiative`, the tracker field, a checkbox tag list and a numeric
  priority box. The lifecycle Playwright tests and the `lifecycle-dialog`
  snapshot the spec's criterion 17 names are already gone; three snapshots
  remain (`settings-responsive`, `shell-explicit-light`, `shell-system-dark`).
- `tests/test_static_guards.py` and `tests/test_no_node.py` skip `tcw/serve/`
  "until TCW-77 rewrites it". `tests/conftest.py` patches
  `tcw.serve.runtime.webbrowser.open`. `tests/test_upstream_projects.py` and
  `tests/test_literal_store_names.py` each start a `TcwServer` with 2.x
  arguments.

**Which source runs.** A private virtual environment at
`<scratch>/tcw77/venv` (`python -m venv --system-site-packages`, then
`pip install -e <worktree> --no-deps`); pytest and the CLI run with the
worktree as the current folder, the venv first on `PATH` and
`PYTHONDONTWRITEBYTECODE=1`. The CLI and the server are tried by hand only
from scratch folders, with `HOME` and `XDG_CONFIG_HOME` pointed at scratch
folders, on ports other than 8765, and every server started is stopped. The
board on `main` is driven by the released 2.8.1 `tcw`, never by the
worktree's code. `pnpm install --frozen-lockfile` has been run in the
worktree, so `pnpm build`, `pnpm test`, `pnpm typecheck` and `pnpm lint` run
there.

**Tests, per the owner's rule for this epic.** The full suite is not run.
Each task runs the files it names, `tests/serve/`, and always the standing
guard files `tests/test_cli_contract.py`, `tests/test_cli_help_standard.py`,
`tests/test_static_guards.py`, `tests/test_cli_handler.py`,
`tests/test_tree_store_raises.py`, `tests/test_no_node.py`,
`tests/test_ledger_3_0.py` and `tests/test_documented_cli_surface.py`. Client
tasks also run `pnpm typecheck`, `pnpm lint`, `pnpm test` and `pnpm build`,
and commit the rebuilt `tcw/serve/dist/client`. The Playwright run and the
snapshot refresh are deferred to the end of the epic by the owner: the
browser tests are written (Task 11) but not run, and the snapshots are not
refreshed. A 2.x test that breaks because 2.x behavior is removed is deleted
or rewritten, and each one is listed in `outcome.md`.

**Parallel work.** TCW-74 changes `tcw/work/prompts/`, `skills/`, procedure
text and `tests/doc_allowance.py` on its own branch at the same time. None of
those files is touched here; what the spec asks of them is handed over in
`outcome.md`.

## Where the spec predates TCW-72 or TCW-73, and the later decision wins

1. **"node" is "project"** (TCW-73). The spec already says so for the rewrite
   (Design 13); test names and fixtures say "project" too.
2. **`connected-projects` is `projects`** (TCW-73 Design 9.3). `/api/project`'s
   `projects` lists the IDs the `projects` key declares.
3. **Outside a project** the message is TCW-73's `NO_PROJECT`, printed by
   `tcw.cli.main` as `serve: <message>`, exit 1 (Design 1.1).
4. **The line on stopping.** Design 1.6 asks for "one line on stderr";
   TCW-73 Design 1.3 says a stderr line on success never starts with the
   command's words. The line is `stopped`, with no prefix.
5. **A refused write check is 403, not 400.** Today's `_validate_mutating_request`
   answers 400 for a non-loopback origin; Design 3.2 and 11 make every
   Host/Origin failure 403 `forbidden`. A wrong `Content-Type` stays 400.
6. **`JiraBackend.current_user()` raises when Jira cannot answer** (TCW-72
   review finding C5), where the spec's Design 4.2 expected `None` and only
   tolerated a raise. The tolerance is what is built: any raise gives
   `user: null` and the rest of `/api/project` still answers.
7. **The lifecycle Playwright tests and `lifecycle-dialog` snapshot** that
   criterion 17 says must not exist were already removed by TCW-70;
   `tests/test_tracker_*.py`, `tests/test_unreadable_*.py` and
   `tests/test_scaffold.py` no longer exist either. What criterion 17 still
   finds is `tests/test_serve*.py`, `tests/test_upstream_projects.py`'s
   serve cases and `tests/test_literal_store_names.py`'s serve case.
8. **The item record** is `tcw/work/record.py:item_record`, which TCW-73 left
   as the one record `show --json` and `list --json` print.

## Choices this plan makes

1. **The server reaches every operation through one `Services` value**
   (`tcw/serve/services.py`): `open_backend`, `open_project`, `delegate`,
   `open_for_update`, and the Jira-only `ticket_link`, `user_name`,
   `assignable_users`, `inbox`, `adopt` and `create_fields`. The defaults are
   the real functions; the tests pass TCW-69's in-memory backend and the
   spec's stubs through it (the "Jira-mode fixture"). The server holds no
   second implementation of any of them.
2. **Configuration and layout come from the project, not the backend.** Per
   request the server reads `read_work_config(root)` (tags, enabled stages)
   and builds `Layout(work_path(root), config.enabled,
   backend.external_stages)`. The in-memory backend has no `config` or
   `layout`, and the rule is the same for every backend.
3. **The board is one backend read when no tag is ticked.** Without tags the
   server calls `list(Query(all=True))` once and takes the default board from
   it with the model's own `Query().matches`; `blocks` and `children` are
   computed from that same read, so Jira mode sends one search (criterion
   11). With tags it calls `list(Query(all=…, tags=…))` and reads every item
   for `blocks` and `children` the way `tcw work list --json` does. Either
   way `items` equals what the CLI prints (criterion 8).
4. **The CLI's logic moves out of its argument handlers so both call it**
   (Task 1): `new_item(backend, title, changes, *, stage, request)` holds
   `_new`'s stage rules; `blocks_target(slug, target, backend, root)` holds
   `_edit`'s per-target open and read; `readable(backend)` (in
   `tcw/work/record.py`) is today's `_readable`, returning the unreadable
   names instead of printing them.
5. **`create_fields(backend)`** is added beside `ticket_link` in
   `tcw/work/jira/tickets.py`: which of priority, effort and complexity the
   Jira project's create screen has (Design 6.9). It is the one Jira-only
   helper the spec needs and TCW-71 did not provide; it reads the metadata
   the backend already caches. `/api/project` carries it as `createFields`,
   degraded to `{"unavailable": …}` when Jira cannot answer. In filesystem
   mode it is a usage error, so `createFields` is all three.
6. **Display names only when the record owner is the backend.** `people` is
   filled with `user_name` only when `recordOwner` is `"backend"` (Design
   4.1's rule), and is `{}` otherwise; no backend name is consulted.
7. **The declaration's "must exist" check covers only entries a save adds.**
   A `changed` or `removed` path already in the file is not re-checked, so a
   capability removed mid-work does not make the file unsavable (the same
   rule review decision R12 set for tags).
8. **Validation notices are `Finding`s** (`{severity, where, message}`) on
   every route, taxonomy and capability saves included; the client prints
   them as `severity: where: message`.
9. **A static path that escapes the client folder is a JSON 404**, not
   `index.html`: "treated as not found" (Design 2.5), and it never serves
   anything from outside the folder.
10. **A Jira key in a URL**: `GET /api/work/<KEY>` answers the item found
    through `backend.lookup`, with `folder` set to its folder; the client
    replaces the URL with `/work/<folder>`. Every detail answer carries
    `folder`.
11. **`projects` entries carry `upstream`** beside `present`, so the create
    form can say why a target will be refused. Delegation still refuses an
    upstream target itself (409).
12. **Comments**: the server asks `read_comments(folder, 200)` (newest first,
    by the interface) and returns them oldest first, with `commentsLimited:
    true` when 200 came back, so the page can say "showing the newest 200".
13. **No dictionary in an API answer is keyed by a stage name.** `files` and
    `verdicts` are lists of objects carrying `stage`, so "no key equal to a
    stage name" (criterion 8) holds at every depth.
14. **Error mapping** follows Design 11 by exception class. A plain
    `ValueError` from a tree store (a store that cannot be opened) is 400
    `usage`; `MultipleMatch` is 409 `refused`; anything else not a
    `TcwError` is 500 `error` with its message and no traceback.
15. **Writes into Jira-owned content are refused before any backend call**:
    `PATCH`, `POST …/comments` and `POST …/blocks` answer 403 `read-only`
    when `recordOwner` is `"backend"`.
16. **`tcw/serve/` joins the static guards.** `tests/test_static_guards.py`
    and `tests/test_no_node.py` stop skipping it once it is rewritten
    (Task 10).
17. **The file editor's starting text** for a document, an implement round
    and a handoff is empty (Design 5.5); a verdict round's is
    `---\njudges: N\nverdict:\n---\n`.

## Tasks

### Task 1: The work-layer helpers the viewer calls

- **Modify `tcw/work/layout.py`**: `Layout.item_folders() -> list[str]`, the
  names of the directories directly under the work path, sorted, leaving out
  names starting with `.` (the rule `work_store_problems` uses); an absent
  work path gives `[]`. Reads no `item.yaml`.
- **Modify `tcw/work/record.py`**: `readable(backend) -> tuple[list[Item],
  list[str]]`, today's `_readable` without the printing (filesystem: every
  readable item and the unreadable paths; otherwise `list(Query(all=True))`
  and `[]`).
- **Modify `tcw/work/cli.py`**: `new_item(backend, title, changes, *, stage,
  request)` (the `--stage` and `inbox_items` rules, then `backend.create`);
  `blocks_target(slug, target, backend, root) -> (backend, Item)` (refuses
  a self-block, opens another project's backend through `open_for_update`,
  reads the target). `_new`, `_edit`, `_list`, `_show` and `_prompt_target`
  call them; `_readable` keeps its stderr warning on top of `readable`.
- **Modify `tcw/work/jira/tickets.py`**: `create_fields(backend) ->
  tuple[str, ...]` (choice 5).
- **Modify `tests/work/test_layout.py`**: `item_folders` lists folders in
  order, skips files and hidden folders, and is `[]` for a missing path.
- **Modify `tests/work/jira/test_jira_tickets.py`**: `create_fields` names
  `priority` only when the fake's create screen has it, and the effort and
  complexity fields when configured; a filesystem backend is a usage error.
- Proof: those files; `tests/work/test_cli_items.py`,
  `tests/work/test_cli_surface.py`, `tests/work/jira/test_jira_delegation.py`
  and the standing files, unchanged and passing.

### Task 2: One process: the server core, security and static files

- **Create `tcw/serve/server.py`**: `TcwServer(ThreadingHTTPServer)` holding
  the project root, the client folder, the `Services` and one write lock;
  the handler: the Host/Origin rule on every request (Design 3.2, 403
  `forbidden`, a missing `Host` refused whatever the `Origin`); JSON
  `Content-Type` on `POST`/`PUT`/`PATCH` (400); the 1 MiB cap before and
  after reading (413 `too-large`); `Content-Security-Policy: default-src
  'self'` on every response; a JSON 404 for every unknown `/api` path and
  every method the API lacks (`DELETE` included); static files with the
  fixed content-type table, the inside-the-folder check and the route
  fallback (Design 2.5, choice 9); the error mapping of Design 11 (choice
  14). `run(root, port, open_browser)`: bind `127.0.0.1:<port>` (`0` asks
  for a free one), print the URL alone on stdout and flush, open the browser
  from a daemon thread unless `--no-open`, stop on Ctrl-C or `SIGTERM` with
  exit 0 and `stopped` on stderr. A bind failure or missing client folder
  raises `BackendError` naming the port or "packaged web assets are missing;
  reinstall TCW" (exit 1).
- **Create `tcw/serve/services.py`** (choice 1) and
  **`tcw/serve/records.py`**: the taxonomy, capability and `/api/resolve`
  routes moved from `__init__.py` unchanged in behavior except that a
  reference to another project's item is reported as
  `{"ok": false, "reason": "other-project", "project": <id>}` (no hosted
  projects), and the notices are `Finding`s (choice 8). TCW-70's work stub
  moves with them, unchanged, until Task 3 replaces it, so today's client
  keeps loading.
- **Rewrite `tcw/serve/__init__.py`**: exports `DEFAULT_PORT`, `HOST`,
  `MAX_BODY_BYTES`, `TcwServer`, `serve(root, port, open_browser)`; no
  sidecar token, no `hmac`, no `include_descendants`.
- **Delete** `tcw/serve/runtime.py`, `web/server/`,
  `tcw/serve/dist/server.cjs`; **modify** `scripts/build_web.mjs` (client step
  only), `package.json` (drop `fastify`; drop `esbuild` if nothing else uses
  it), `pnpm-lock.yaml` (regenerated), `eslint.config.mjs` and
  `tsconfig.json` if they name `web/server`.
- **Modify `tcw/cli.py`**: `_cmd_serve` calls `serve(root, port, open)`; the
  aggregation comment goes; `--port` help says `0` picks a free port.
- **Modify `tests/conftest.py`**: the browser patch targets
  `tcw.serve.server.webbrowser.open`.
- **Create `tests/serve/__init__.py`, `tests/serve/conftest.py`** (a
  filesystem fixture project built by the branch's `init` in a git
  repository, with `user.name` in its local file; a `served` fixture starting
  `TcwServer` on port 0 in a thread; a raw-socket request helper that can
  omit `Host`), **`tests/serve/test_process.py`** (criterion 1's static
  parts: the deleted files, no `fastify`, no `subprocess` import and no
  `os.system`/`os.popen` under `tcw/serve/`; criterion 2: stdout is one URL
  line and its port answers, a second server on that port exits 1 naming it
  with nothing on stdout, outside a project exits 1 with `NO_PROJECT`,
  `SIGTERM` exits 0; `PATH` without `node` still serves `index.html`;
  `pgrep -P` lists no child after start), **`tests/serve/test_static.py`**
  (criterion 3), **`tests/serve/test_security.py`** (criterion 4 except the
  Jira marker, which is Task 5), **`tests/serve/test_records.py`** (the
  taxonomy and capability cases of today's `tests/test_serve_write.py`,
  `tests/test_serve.py` and `tests/test_serve_resolve.py` that still apply,
  rewritten against the new server and error bodies).
- **Delete** `tests/test_serve.py`, `tests/test_serve_write.py`,
  `tests/test_serve_resolve.py`, `tests/test_serve_runtime.py`; the serve
  cases of `tests/test_upstream_projects.py` (aggregation and upstream
  boards, 2.x); **rewrite** the serve case of
  `tests/test_literal_store_names.py` against the new server (a traversal in
  a work URL is a 404).
- Proof: `tests/serve/`, `tests/test_upstream_projects.py`,
  `tests/test_literal_store_names.py`, the standing files; `pnpm build` then
  `git diff --exit-code tcw/serve/dist` (criterion 16).

### Task 3: The work API: project, board and item reads

- **Create `tcw/serve/work.py`**: `GET /api/project` (Design 5, choices 2,
  5, 11), `GET /api/work[?all=1][&tag=…]` (Design 5.1, choice 3, the
  fallback of Design 7.3 with `fallback`, `unavailable` and `{slug, path}`
  rows), `GET /api/work/<folder>` (Design 5.2: `folder`, `item`,
  `requestText`, `comments`, `commentsLimited`, `people`, `link`, `files`,
  `verdicts`, `warnings`; degrading on `Unreachable` and `BackendError` when
  the record owner is the backend; 404 for a folder not in
  `layout.item_folders()`; choice 10 for a Jira key). The work stub goes.
- **Create `tests/serve/memory.py`**: the spec's Jira-mode fixture: a
  recording wrapper over `tests/work/memory_backend.py` (every call, reads
  included, with its arguments; switches to raise a given exception from
  `list`, `read`, `read_request`, `read_comments`), configured with
  `external_stages = {request, qa}`, `inbox_items = False`,
  `current_user() == "acc-me"`, and stubs for `ticket_link`, `user_name`,
  `assignable_users`, `inbox`, `adopt` and `create_fields`; its project is a
  Jira-mode `tcw-config.yaml` (TCW-71's test configuration) whose item
  folders carry Jira keys, so `validate`'s offline Jira check reads them as
  items.
- **Create `tests/serve/test_work_read.py`**: criterion 6's first bullet;
  criterion 8's `user` (set and unset), tags (`?tag=a&tag=b` returns the
  three tagged items and equals `tcw work list --tag a --tag b --json`'s
  `items`), and `item` equal to `tcw work show <f> --json`'s `item` with no
  key equal to a stage name at any depth; criterion 10's read bullets
  (`recordOwner`, `user`, `people`, one `list` call with `Query.tags ==
  {"a"}`, `requestText`, both comments, `link`, one `read_comments` with
  limit 200; `Unreachable` and `BackendError` naming `TCW_JIRA_TOKEN`
  degrading the board and the detail; `NotFound` 404; a missing folder 404);
  criterion 13's first bullet (a child project's items are not on the
  board); an unreadable `item.yaml` fails the board with 500 naming the file;
  a Jira key URL answers the folder.
- Proof: `tests/serve/`, the standing files.

### Task 4: The work API: files, rounds, handoffs and the declaration

- **Create `tcw/serve/files.py`**: the file rules (which `<path>` a stage
  allows, Design 5's list, everything else 404, external and disabled stages
  404); `GET`/`PUT /api/work/<folder>/files/<path>` with the SHA-256
  revision, the stale check and the write under the lock, written whole
  through `tcw.store.fs._atomic_write_all` (a temporary file beside the
  target, then `os.replace`), creating the enabled stage's folder for
  `revision: null`; `POST /api/work/<folder>/files` (`document`, `round`,
  `handoff`; 400 for a stage with no artifact, a disabled or external stage,
  or a kind the stage does not have; choice 17); `GET`/`PUT
  /api/work/<folder>/declaration` (the six lists through
  `parse_declarations`, written in schema order without empty lists, the
  parser's message and the raw text for a file it rejects, choice 7's
  existence check, the revision of the file); validation after every write
  through `validate(..., target=ValidationTarget("work", folder, item))`,
  passing the item when the backend could be read and `None` otherwise.
- **Create `tests/serve/test_files.py`**: criterion 6 (the round path equal
  to `tcw work path <slug> review --next` with its `judges:` and empty
  `verdict:`; the handoff path equal to `tcw work path <slug> implement
  --handoff` with the clock fixed; the creating `PUT` and its 409 repeat; a
  stale `PUT`; the `os.replace` recorder; each 404 path and no folder made;
  `completed` 400), criterion 7 (round trip, `changed: [no/such/path]` 400,
  `new: [no/such/path]` accepted, an unknown key returning the parser's
  message, schema order and no empty lists), criterion 15 (a dangling
  `tcw://T/no-such-term` link warned about and the file saved; a review round
  with no verdict warned invalid; Jira mode unavailable gives no warning),
  and the Jira-mode `qa/round-1.md` 404.
- Proof: `tests/serve/`, `tests/test_validate_target.py`, the standing files.

### Task 5: The work API: properties, comments, creating, blocks, tickets, options

- **Modify `tcw/serve/work.py`**: `PATCH /api/work/<folder>` (`changes` in
  JSON as Design 5.7 sets out, `expected` compared under the lock, 409
  `stale-revision` naming the property; the "refused" checks of Design 9.1:
  a local `parent` or `blocked-by` must be an item here, another project's
  full slug is accepted with a warning, tags are the operation's own check);
  `POST /api/work/<folder>/comments`; `POST /api/work` (this project through
  `new_item`, another through `delegate` with only `priority`, 400 naming any
  other property, 409 `refused` carrying `ticket`; the target must be this
  project or a declared one, 400 otherwise); `POST
  /api/work/<folder>/blocks` (`blocks_target`, the `expected` check under the
  lock, one target per request); `GET /api/tickets`, `POST
  /api/tickets/<KEY>/adopt`; `GET /api/options/<field>?q=` for `assignee`
  (`assignable_users(q, 10)`) and `work` (items of connected
  filesystem-mode projects found here, Design 9.2). Choice 15 for every write
  to backend-owned content.
- **Create `tests/serve/test_work_write.py`**: criterion 8's `PATCH`,
  unregistered tag, since-unregistered tag, parent, `blocks` and upstream
  `blocks`, and comment bullets; criterion 9; criterion 10's write bullets
  (403 with no `update` or `comment` recorded; `/api/tickets` 400 in the
  filesystem fixture; `create` raising `Refused` with `ABC-9`); criterion 12's
  server half for every work field the table refuses (one case per field);
  `GET /api/options/assignee?q=al` calling the stub with limit 10; criterion
  4's credential marker (every route in the Jira-mode fixture, no body or
  header holding it).
- **Create `tests/serve/test_no_process.py`**: criterion 1's run-time parts
  (a `subprocess.Popen` recorder over one valid request to every route,
  including a create into a connected project and a `blocks` link into it,
  records only `git rev-parse` and `git --no-optional-locks … status`; the
  server started as a child process lists no child through `pgrep -P` after
  one request to every route) and criterion 5 (the start, complete and drop
  routes are 404 and the stage is unchanged; no `set_stage` recorded over
  every route; no module under `tcw/serve/` imports `tcw.work.advance`).
- Proof: `tests/serve/`, `tests/work/test_cli_items.py`, the standing files.

### Task 6: Taxonomy and capabilities: refused values and inherited entries

- **Modify `tcw/serve/records.py`**: before calling the store, the "refused"
  checks of Design 9's table, each a 400 naming the field and value:
  taxonomy `parent` (create), `relates_to`, `vocabulary` (vocabulary entries
  only); capability `Feature` (a Feature entry), `Subject` (vocabulary
  entries), `Roles` (`roles/…` capabilities) and `When` (`conditions/…`),
  each accepting a leading `!`, `Blocked by` and `Superseded by` (existing
  capabilities); inherited entries count. A `PATCH` to an inherited term or
  capability is 403 `read-only`. `Planning doc` and `Tracker` are never
  written by the viewer.
- **Modify `tests/serve/test_records.py`**: one case per refused field;
  `!` accepted on `Roles` and `When`; criterion 13's inherited capability
  (listed with its origin, 403 on `PATCH`) and the `tcw://` link to another
  project's item (`other-project` with its ID).
- Proof: `tests/serve/`, `tests/test_capabilities.py`,
  `tests/test_taxonomy.py`, the standing files.

### Task 7: The client: model, board and read-only item page

- **Rewrite `web/client/src/model/types.ts`** (the project, stage row, item
  record, board, detail, file, comment and finding shapes; no 2.x status,
  tracker, sidecar, plan-stage or initiative type), **`model/tree.ts`** (the
  work tree by `parent` on folder keys; sort by name or creation date; stage
  order from the project's table; a `null` priority after `lowest`),
  **`model/api.ts`** (no `DELETE`; an `isUnavailable` test).
- **Create `web/client/src/model/work.ts`**: the folder of a slug, a person
  through `people`, the default stage filter (every stage that is not
  terminal, plus "no stage"), the board's query string.
- **Rewrite `web/client/src/ui/app.tsx`** loading `/api/project` and the
  board, the stage, tags (a backend query) and assignee filters, the
  fallback banner with Retry, routing by folder, the Jira-key URL
  replacement; **`ui/work-document-tabs.tsx`** as stage tabs from the
  project's table (a document, rounds newest first with verdicts and the
  current verdict, handoffs, the external line with the link);
  **create `ui/work-views.tsx`** (the item page: title, folder, stage with
  "Move it with `tcw work advance <slug>`.", properties, the request,
  comments oldest first, "linked tickets with no item", "Open in Jira", each
  part's `unavailable` message with Retry). **Modify
  `ui/shared-components.tsx`**: no tracker field, no interrupted-claims
  banner; `other-project` links labelled and not navigating; work rows show
  stage and creation date. **Delete** `ui/work-resource.ts` and its test.
- **Rewrite the client unit tests** that cover these files
  (`tree.test.ts`, `app.test.tsx`, `work-document-tabs.test.tsx`,
  `shared-components.test.tsx`, `api.test.ts`) and add `work.test.ts`.
- Proof: `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` (dist
  committed); `tests/serve/test_static.py`.

### Task 8: The client: editing, creating and comments

- **Modify `ui/work-views.tsx`** and **`ui/app.tsx`**: the file editor for
  documents, rounds (with the verdict as a fixed choice above the editor that
  writes the `verdict:` line) and handoffs, with **Create**, **New round** and
  **New handoff**; the properties form (filesystem mode) sending only the
  properties changed and their loaded values as `expected`; **Add** for
  `blocks` (one request per link, stopping at the first refusal and saying
  which were added); the comment box (filesystem mode); the **New item** form
  (target project, the first-stage box only when `inboxItems`, only title,
  request text and priority for another project, `createFields` in Jira
  mode); the **Tickets** view with **Adopt** (Jira mode). No control moves an
  item. The conflict banner answers `stale-revision`.
- **Create `ui/declaration-form.tsx`**: the six lists, the "comments in this
  file are not kept" note, and the plain-text fallback with the parser's
  message.
- **Modify `ui/content-views.tsx`**: no `Planning doc` or `Tracker` field in
  any form (a record holding one shows it read-only), no edit control on an
  inherited entry; the 2.x modals and the 2.x work editor go.
- **Rewrite** `content-views.test.tsx`; add `work-views.test.tsx` and
  `declaration-form.test.tsx`.
- Proof: as Task 7.

### Task 9: The client: autocomplete everywhere

- **Modify `ui/reference-input.tsx`**: a `mode` of `refuse` (an unknown value
  cannot be committed, and the field says why), `warn` (committed with a
  warning under the field, for a `<project>/<folder>` slug of another
  project) or `allow`; an optional server source called with the typed text
  (`/api/options/<field>`); tags as chips from the registry.
- **Modify `model/reference-search.ts`**: the fields of Design 9's table
  (work parent minus the item and its descendants, blocked-by, assignee
  names plus `user`; taxonomy and capability fields with inherited entries;
  capability path one segment at a time; `!` on roles and when; the
  declaration lists) and the `tcw://` source over all three axes, a work item
  inserting `tcw://W/<folder>`.
- **Modify `ui/shared-components.tsx`**: the Markdown editor offers `tcw://`
  completion where `tcw://` is typed.
- **Modify** `reference-input.test.tsx`, `reference-search.test.ts`: each
  refused field will not commit an unknown value; the warn case keeps
  `other-project/2026-01-01-x` with a warning; `!` on roles and when; the
  path segments; `tcw://` completion inserting `tcw://W/<folder>`.
- Proof: as Task 7.

### Task 10: The guards that read both halves

- **Create `tests/serve/test_no_stage_names.py`** (criterion 14): string
  literals in `tcw/serve/**/*.py` (through `ast`, docstrings excepted) and
  in `web/client/src/**/*.{ts,tsx}` (tests excepted; a tokenizer for string
  and template literals that skips comments) that equal a name from
  `STAGES` or hold one as a path segment; checked against a planted
  `"review"`, a planted `"plan/plan.md"` and `"request body too large"`.
- **Create `tests/serve/test_wording.py`** (criterion 18's code half): no
  Python string literal under `tcw/serve/` matches `\bnodes?\b`.
- **Modify `tests/test_static_guards.py`** and **`tests/test_no_node.py`**:
  read `tcw/serve/` (choice 16).
- Proof: those files and the standing files.

### Task 11: The Jira browser fixture and the browser tests

- **Create `tests/serve/jira_launcher.py`**: builds a Jira-mode fixture
  project in a given folder (TCW-71's test configuration, seeded tickets with
  assignees and comments, one inbox ticket), installs TCW-71's fake in place
  of the client's request function, appends one line per request it answers
  (method and path) to a file in the fixture, fails every request as
  unreachable while a marker file exists there, and runs `tcw serve`.
- **Create `tests/serve/test_jira_launcher.py`**: criterion 11's pytest case
  (credential variables unset: the server starts, `GET /api/work` is 200
  with `fallback: true` and a message naming the unset variable, `PUT
  spec/spec.md` succeeds), and a case with them set: the board loads with one
  search and no `/user` request.
- **Rewrite `web/e2e/parity.spec.ts`** for the 3.0 viewer (work board,
  filters including the tags query, stage tabs, files, declaration form and
  its plain-text fallback, no lifecycle controls and the `tcw work advance`
  line, autocomplete) and **create `web/e2e/jira.spec.ts`** (criterion 10's
  rendering bullet and criterion 11) using the launcher. Not run (the owner
  defers the browser run); `pnpm typecheck` and `pnpm lint` cover them.
- Proof: `tests/serve/test_jira_launcher.py`; `pnpm typecheck`, `pnpm lint`.

### Task 12: Records

- **Modify** `docs/capabilities/web/description.md` and `meta.yaml`
  (rewritten; no `Planning doc`; `Feature: local-web-app` checked),
  `docs/capabilities/web/editing/description.md` (and `meta.yaml` if it
  carries a retired field), `docs/capabilities/cli/reference-a-tcw-object/description.md`
  and `docs/capabilities/cli/read-from-an-upstream-project/description.md`
  (only their `tcw serve` sentences), `docs/taxonomy/local-web-app/description.md`.
- **Create** `docs/capabilities/web/pick-references-and-known-values-from-suggestions/`
  and `docs/capabilities/web/see-jira-owned-work-read-only/` (Feature
  `local-web-app`, status `Supported`).
- **Write `capabilities.yaml`** in the item folder on `main`, as the spec's
  Capability changes section declares.
- Proof: `tests/test_ledger_3_0.py`, `tests/test_capability_ref_wording.py`;
  `records_problems(..., finished=True)` over the item's `capabilities.yaml`
  against the branch's ledger reports nothing.

### Task 13: The guide and the release entries

- **Rewrite `docs/guide/web-viewer.md`** (Design 14): one Python process and
  no Node; what can be read, edited and created; the Jira-mode rule; the
  autocomplete table in plain words; the security rules; no lifecycle
  actions, with `tcw work advance` and `tcw work discard` named instead;
  contributor build notes. No line matches `\bnodes?\b`; it says TCW "never
  changes git state".
- **Create `docs/release-notes/upcoming/<slug>.md`** and
  **`docs/changelogs/upcoming/<slug>.md`**, each starting with a `##`
  heading.
- **Modify `tests/serve/test_wording.py`**: the guide half of criterion 18,
  and the two entries start with `##`.
- Proof: `tests/serve/test_wording.py`, `tests/test_upcoming_entries.py`,
  `tests/test_documented_cli_surface.py`.

### Task 14: Mutation checks and collection

No new behavior. Each guard below is broken on purpose, its test seen red for
the stated reason, and the code restored; the results go to `outcome.md`.
Then `pytest --collect-only -q` with no errors. No commit unless a mutation
exposes a gap, in which case the fix and its test are the commit.

## Documentation Sync

| Entry | Fires | Handled |
| --- | --- | --- |
| `README.md` [Public-API] | Yes: `tcw serve` needs no Node and changes what it does | Deferred to TCW-75, which owns the README's web app section and install note (spec Non-goals, Design 14). |
| `docs/guide/jira.md` [Tracker-Change] | No: no tracker command, ticket behavior or `work.tracker` key changes | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes: `docs/guide/web-viewer.md` | Task 13 (this slice owns that guide). Other guides that mention the viewer in passing (`multi-repo.md`'s aggregation line) are TCW-75's. |
| `docs/release-notes/upcoming/<slug>.md` [Public-API] | Yes | Task 13. |
| `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] | Yes | Task 13. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes: the setup skill names Node as a prerequisite of `tcw serve` | Handed to TCW-74 (every skill but `configure`, epic decision 3): `skills/setup/SKILL.md:8` and `skills/setup/references/install.md:71-74`. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | No: no configuration key changes | — |

## Mutation checks (Task 14)

- The Host rule accepting a missing `Host` when `Origin` is loopback:
  criterion 4's fourth case goes red.
- The static resolver skipping the inside-the-folder check: criterion 3's
  traversal cases go red.
- The stale check on files removed: the stale `PUT` and the repeated create
  go red.
- `expected` not compared on `PATCH`: the repeated priority change goes red.
- The 403 for backend-owned content removed: criterion 10's write cases go
  red (an `update` is recorded).
- Degrading turned off: criterion 10's `Unreachable` and `BackendError`
  cases go red.
- The file rules allowing `item.yaml`: criterion 6's 404 cases go red.
- The stage-name scan ignoring path segments: the planted `"plan/plan.md"`
  check goes red.
- A refused taxonomy or capability check removed: its criterion 12 case
  goes red.
- stdout printing a prefix before the URL: criterion 2's first case goes red.

## Verification

What the suite cannot see, checked by hand in a scratch folder with the
branch's code and recorded in `outcome.md`:

- `tcw serve --no-open --port 0` in a scratch project prints one URL; `curl`
  with and without a loopback `Host` gives 200 and 403; `ps` shows one
  process; Ctrl-C prints `stopped` and exits 0.
- `pnpm check:build` passes on the committed tree.
- The browser run is deferred by the owner. If a page needs checking by eye,
  it is done only in the dedicated "Chrome Claude" profile; the plan does not
  depend on it.

## Notes

- **Self-hosting.** This changes `tcw/`; the board is driven by the released
  2.8.1 `tcw` from the primary checkout, and `plan.md`, `outcome.md`,
  `capabilities.yaml` and spec notes are committed on `main`.
- **Snapshots.** The shell's text and controls change, so
  `shell-system-dark`, `shell-explicit-light` and `settings-responsive` are
  expected to need refreshing at the epic's browser run; `outcome.md` lists
  them.
- **Not done here, by the spec:** the README (TCW-75), the setup skill's Node
  sentences (TCW-74), and discarding the two items this makes obsolete
  (`2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`
  and the web-app part of the 2026-09-30 inbox entry on following renames),
  which happens when this item completes.
