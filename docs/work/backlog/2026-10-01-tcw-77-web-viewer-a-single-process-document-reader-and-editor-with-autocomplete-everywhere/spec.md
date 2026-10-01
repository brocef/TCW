# Spec — Web viewer: a single-process document reader and editor with autocomplete everywhere

## Capability changes

This slice ships user-facing behavior, so it changes the ledger. The planned
declaration, in the schema TCW-69 settled for `<item>/capabilities.yaml`:

```yaml
new:
  - web/pick-references-and-known-values-from-suggestions
  - web/see-jira-owned-work-read-only
changed:
  - web
  - web/editing
  - cli/reference-a-tcw-object
  - cli/read-from-an-upstream-project
taxonomy:
  changed:
    - local-web-app
```

What each change says:

- **`web`** ("Browse TCW content in a local web app",
  `docs/capabilities/web/meta.yaml`). Its description promises that
  `tcw serve` requires Node.js 22.12 and aggregates descendant work boards
  (`docs/capabilities/web/description.md:3-6`), filters work by status and sorts
  by last-modified time (`:14-15`). It is rewritten: one Python process with no
  Node.js, one project, the filters by stage (finished items hidden by default),
  tags and assignee, inherited entries marked, and work rows dated by creation.
  Its `Feature` field moves from `connected-project-registry` to
  `local-web-app`, the Feature that actually describes it
  (`docs/taxonomy/local-web-app/meta.yaml`).
- **`web/editing`** ("Edit TCW content in a local web app"). Today it describes
  sidecars, generated sidecars, the complete dialog with the Definition-of-Done
  checklist, plan-stage documents and git refusals
  (`docs/capabilities/web/editing/description.md:17-39`). It is rewritten around
  stage documents, rounds, handoffs, the declaration form, add-only comments,
  creating items, taxonomy entries and capabilities, adopting inbox tickets, and
  the absence of every lifecycle action.
- **`web/pick-references-and-known-values-from-suggestions`** (new). Every
  editable field autocompletes or is a fixed choice, per the table in Design 9.
- **`web/see-jira-owned-work-read-only`** (new). In Jira mode the request,
  comments, stage and properties are shown read-only with an "Open in Jira"
  link; files on disk stay editable while Jira is unreachable.
- **`cli/reference-a-tcw-object`** and **`cli/read-from-an-upstream-project`**:
  only their sentences about `tcw serve` change
  (`docs/capabilities/cli/reference-a-tcw-object/description.md:6-8`, `:13`,
  `:23-26`; `docs/capabilities/cli/read-from-an-upstream-project/description.md:12-15`).
  The viewer no longer has "hosted" boards or changing routes into other
  projects; a reference to another project is a labelled link. Other parts of
  those records (finished-work references, the `completed/` spelling) belong to
  the slices that change slugs (TCW-70, TCW-73).
- **`web/choose-a-theme`** is unchanged.
- **Taxonomy `local-web-app`** (`docs/taxonomy/local-web-app/description.md:1`)
  says "served from the local TCW node for browsing or changing TCW project
  data". It becomes "a local web app, run by `tcw serve`, for reading and
  editing a project's TCW documents and creating TCW objects; it makes no
  lifecycle moves". Its `node` vocabulary entry follows TCW-73's node-to-project
  sweep, not this slice.

Records that mention `tcw serve` but describe 2.x behavior other slices remove,
named so they are not missed: `work/configure-the-work-lifecycle`
(`description.md:10`, "`tcw serve` runs no hooks"),
`work/require-tracker-backed-work` (`:43-46`),
`work/synchronize-external-tracker-work` (`:97`),
`work/manage-external-tracker-intake` (`:45-48`),
`work/archive-a-resolved-item-before-it-is-deleted` (`:29`) and
`work/read-a-work-item` (`:22-23`). The last one's promise, that the API returns
the same document as `tcw work show --json`, is kept by this slice (Design 5.1).

## Problem

`tcw serve` is today a second front end to the whole of TCW 2.x, lifecycle
included, built from two runtimes. Six problems follow.

1. **It needs Node.js to run, and two processes.** `run_server` checks for
   Node 22.12 (`tcw/serve/runtime.py:25`, `:38-60`), starts the Python API as a
   private "sidecar" on a random port with a secret token (`runtime.py:136-144`),
   then starts the bundled Fastify server as a child process
   (`runtime.py:169-176`), which proxies every `/api` request to the sidecar
   (`web/server/src/server.ts:50-80`) and serves the client
   (`server.ts:82-93`). Supervising both is a third of `runtime.py`
   (`:63-116`). The build bundles the server separately with esbuild
   (`scripts/build_web.mjs:7-15`). A TCW user must install Node for this one
   command (`README.md:109-110`, `docs/guide/web-viewer.md:13-18`,
   `skills/setup/SKILL.md:8`).
2. **Its protections are split across the two layers.** The Fastify layer
   checks `Host`/`Origin` on every `/api` request (`server.ts:50-52`) but lets
   a request with neither header through (`server.ts:21`). The Python layer
   checks them only on writes (`tcw/serve/__init__.py:365-389`); its reads are
   guarded only by the sidecar token (`__init__.py:484-490`, `:578-584`). Remove
   Fastify and the reads are unguarded, so the check has to move, not just stay.
3. **It is built on the 2.x work store, which TCW-70 removes.** Every work route
   calls `FsWorkStore` (`__init__.py:25-29`, `:492-498`): status-folder
   boards, the 2.x artifact list (`WORK_ARTIFACTS`, `tcw/store/base.py:3101-3102`),
   sidecars (`__init__.py:697-773`), plan stages (`:673-695`), interrupted claims
   (`:567-574`, `:781-786`), strict-tracker refusals (`:216-251`), owed tickets
   (`:254-286`) and git commits after a create (`:994-998`). The client
   hard-codes the 2.x statuses (`web/client/src/model/types.ts:5-11`), the 2.x
   document tabs (`web/client/src/ui/work-document-tabs.tsx:31-33`) and the
   `initiative` field (`content-views.tsx:916-921`). None of this exists in 3.0.
4. **It makes lifecycle moves that skip the lifecycle.** The API starts,
   completes and drops items (`__init__.py:1016-1088`, `:1552-1575`) and shows a
   Definition-of-Done checklist (`:858`), but runs no hooks
   (`docs/capabilities/work/configure-the-work-lifecycle/description.md:10`;
   `README.md:789-794`). In 3.0 a move is `advance`, which runs gates and hooks
   (TCW-69 Design 6). A browser move would either skip them or run project
   scripts inside the web server.
5. **It combines child projects' boards, half-way.** `tcw serve` always
   aggregates descendant boards (`tcw/cli.py:469-479`; `__init__.py:540-565`),
   which needs qualified slugs, read-only refusals for upstream projects
   (`__init__.py:511-524`) and a list of "hosted" projects for links
   (`:526-538`). Taxonomy and capabilities are not aggregated, an open defect
   (`docs/work/backlog/2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`).
6. **Autocomplete is partial.** A reference field accepts any typed text on
   Enter (`web/client/src/ui/reference-input.tsx:93-100`). Tags are a checkbox
   list (`content-views.tsx:936-965`), priority is a number box (`:893-897`), a
   new capability's path is free text (`:1061`), negation is offered for `When`
   but not `Roles` although the store accepts it on both
   (`content-views.tsx:1094`; `tcw/store/fs.py:3269-3272`), and there is no
   assignee field, no completion of `tcw://` links, and no form for the
   declaration file.

## Goals

1. **One Python process** serves the prebuilt client and a JSON API on
   `127.0.0.1`, with no Node.js at install time or runtime, and starts no other
   process.
2. **Every Fastify protection, in that one process**, applied to reads as well
   as writes.
3. **No logic of its own.** Every read and write goes through an operation the
   CLI also uses: TCW-69's backend operations and layout, TCW-71's ticket
   functions, the delegation function behind `new --project`, and the taxonomy
   and capabilities stores. Item payloads are the CLI's own JSON documents.
4. **Documents.** Read and edit the files the item-folder layout names: stage
   documents, rounds, handoffs and the declaration file; create the missing ones
   for enabled stages through `path`. Read and edit taxonomy and capability
   records.
5. **Creating objects.** Work items (including into another project, and at the
   inbox stage where the backend allows it), taxonomy entries and capabilities.
   In Jira mode, list inbox tickets and adopt them.
6. **The Jira-mode rule.** What the backend owns is shown read-only with a link
   to the ticket; what is on disk stays editable, including while Jira is
   unreachable.
7. **Autocomplete everywhere**, as the table in Design 9 sets out, with
   "refused" enforced by the server and not only by the form.
8. **No lifecycle.** No control in the client and no route in the API moves an
   item, discards it or checks its Definition of Done.
9. **One project.** No combined boards; inherited taxonomy and capability
   entries shown and offered, marked as inherited.

## Non-goals

- **Lifecycle moves of any kind** (`advance`, `discard`, the 2.x start,
  complete and drop), forced-move reasons, gates, hooks and Definition-of-Done
  checklists. They are the CLI's (TCW-69, TCW-73).
- **Renaming** a work item, taxonomy entry or capability. Editing a title changes
  the title only. Renaming rewrites references across items and stays in the CLI
  (`tcw work rename`, TCW-70).
- **Deleting** anything. There is no delete route for any object or file.
- **Combining child projects' boards**, or reading and writing another project's
  records beyond the cross-project suggestions in Design 9.
- **Editing inherited** taxonomy and capability entries.
- **The backend operations, ticket functions and delegation** themselves. This
  slice calls them. Where they lack something the viewer needs, this spec says so
  as a cross-slice finding (Notes) rather than building a private version.
- **`README.md`'s web app section** (TCW-75 owns it); this slice rewrites
  `docs/guide/web-viewer.md`.
- **A hosted or multi-user server.** It binds the loopback address only.
- **Watching files for changes** made outside the viewer. A stale edit is
  caught at save (Design 10), not pushed to the page.
- **Running the Playwright and client unit test suites in CI.** They stay
  contributor tools that need Node; CI keeps checking that the committed bundle
  matches its source.

## Design

### 1. The command and the process

`tcw serve [--port <n>] [--no-open]`, as TCW-73 lists it.

1. It finds the project from the current directory, as every command does. Not
   inside a project: exit 1 with the message every command gives (TCW-73).
2. It binds a `ThreadingHTTPServer` (Python's built-in HTTP server, one thread
   per request) to `127.0.0.1:<port>`, default 8765 (today's `DEFAULT_PORT`,
   `tcw/serve/__init__.py:38`). **[Decision]** `--port 0` asks the operating
   system for a free port; the printed URL carries the port actually bound. This
   gives tests and scripts a collision-free start.
3. A port already in use, or any other bind failure: exit 1, naming the port on
   stderr (TCW-73).
4. **stdout carries only the URL** (`http://127.0.0.1:<port>/`), one line,
   flushed as soon as the socket is listening. Everything else goes to stderr.
   Today it prints `Serving TCW at <url>` on stdout (`runtime.py:178`).
5. Unless `--no-open`, it opens the URL in the default browser from a
   background thread (`webbrowser`, as `runtime.py:179-180` does today).
6. Ctrl-C or `SIGTERM` stops it with exit 0 and one line on stderr.
7. **What "single process" rules out.** The server process starts no other
   process, at startup or per request:
   - no Node.js and no Fastify (`runtime.py`, `web/server/` and the bundled
     `server.cjs` are deleted);
   - no private API "sidecar", so no sidecar token (`__init__.py:93-95`,
     `:484-490`);
   - **[Decision]** no desktop file opener. Today `POST …/open` runs `open` or
     `xdg-open` on a document (`__init__.py:98-106`, `:1580-1650`). The route
     goes: the viewer shows the document itself, and the CLI's
     `tcw work path` names the file for anyone who wants their own editor;
   - no hooks, no git, no `generate:` scripts. Nothing the viewer calls runs a
     hook, because hooks run only on `advance` (TCW-69 Design 6), and nothing in
     3.0 touches git state.

   Opening the browser is a library call, not a child process the server
   manages.
8. **[Decision] Configuration is read per request,** as the stores are opened
   per request today (`__init__.py:492-498`). A tag registered with
   `tcw work tags add` while the server runs is offered on the next request,
   and an invalid configuration returns an error to the page instead of stopping
   the server.
9. **Writes are serialized.** One lock in the process covers every write the
   viewer makes, so the check for a stale edit and the write it guards happen
   without another viewer write in between (Design 10).

### 2. The client and how it ships

1. The client stays a React single-page app (one HTML page whose script draws
   every view) in `web/client/`, built by Vite.
2. **The build** (`pnpm build`, `scripts/build_web.mjs`) keeps only the client
   step: Vite builds `web-dist/client`, which is copied to
   `tcw/serve/dist/client`. The esbuild server bundle (`build_web.mjs:7-15`)
   and `tcw/serve/dist/server.cjs` are deleted.
3. **Shipping** is unchanged: the built client is committed and packaged as
   package data (`pyproject.toml:32-33`), so installing TCW needs no Node and no
   network. `pnpm check:build` (`scripts/check_web_build.mjs:3-6`) and its CI job
   (`.github/workflows/test.yml:78-104`) stay as they are.
4. **`package.json`** loses `fastify` (`package.json:21`) and keeps the
   contributor `engines.node` floor (`:6`).
5. **Static files.** The server serves files from the packaged `dist/client`
   folder, found through `importlib.resources` as `runtime.py:155-161` does
   today:
   - a request path that names a file in that folder returns it, with a content
     type from a fixed table (`.html`, `.js`, `.css`, `.json`, `.svg`, `.png`,
     `.ico`; anything else `application/octet-stream`), as `server.ts:12-18`
     does;
   - the resolved file must lie inside the folder; a path that escapes it
     (`..`, an absolute path, an encoded `%2e%2e`) is treated as not found;
   - any other non-`/api` `GET` returns `index.html`, so a deep link such as
     `/work/<folder>` loads the app (the "single-page-app route fallback");
   - an unknown `/api/...` path is a JSON 404, never `index.html`.
6. A missing `dist/client` (a broken install) is exit 1 at startup with
   "packaged web assets are missing; reinstall TCW", as `runtime.py:160-161`
   says today.

### 3. Security

Every rule the Fastify layer gave is kept, in the one process:

1. **Loopback only.** The socket binds `127.0.0.1`; no option binds anything
   else.
2. **[Decision] Host and Origin on every request**, not only `/api`. A request is
   refused (403, JSON body) unless its `Host` header names a loopback address
   (`127.0.0.1`, `localhost`, `[::1]`, with any port) and its `Origin`, when
   present, does too. A request with no `Host` is refused. This is the Python
   rule today (`_is_loopback_origin`, `__init__.py:319-362`), now applied to
   reads, which blocks DNS rebinding (a hostile site making its own name resolve
   to `127.0.0.1` so the browser sends it this server's pages). The ticket asks
   for `/api`; applying it to the static files as well costs nothing and leaves
   one rule.
3. **JSON on writes.** `POST`, `PUT` and `PATCH` need
   `Content-Type: application/json` (charset allowed), as
   `_validate_mutating_request` does (`__init__.py:365-389`). The API has no
   `DELETE`.
4. **1 MiB body cap**, checked against `Content-Length` before reading and
   again after (`__init__.py:42`, `:395-440`). A larger body is 413.
5. **`Content-Security-Policy: default-src 'self'`** on every response,
   including errors and static files (`__init__.py:465-467`).
6. **Jira credentials stay in the server.** They are read from the environment
   variables the configuration names (TCW-71), used only for the server's own
   requests to Jira, and never appear in a response body or header. A Jira error
   is passed to the page as TCW-71's message, which names the problem and never
   the token.

### 4. What the server calls

The viewer is a thin layer over operations the CLI already uses. Each route in
Design 5 names its operation. In full:

| Need | Operation | Owner |
| --- | --- | --- |
| The board | `backend.list(Query)`, rendered as `tcw work list --json` | TCW-69, TCW-73 |
| One item | `backend.read`, rendered as `tcw work show --json` | TCW-69, TCW-73 |
| Edit properties | `backend.update(folder, Changes)` | TCW-69 |
| Add a comment | `backend.comment(folder, text)` | TCW-69 |
| Request text, comments and ticket link | **proposed** `backend.record(folder)` (Design 4.2) | TCW-69 (change needed) |
| Create an item | the function behind `tcw work new`, including `--project` delegation and `--stage inbox` | TCW-70, TCW-71, TCW-73 |
| Inbox tickets, adopt | the functions behind `tcw work tickets list` and `tickets adopt` | TCW-71 |
| A Jira key in a URL | `backend.lookup(name)` | TCW-69 |
| Stage table, enabled stages, external stages | `model.STAGES`, the parsed `work.stages`, `backend.external_stages`, `backend.inbox_items` | TCW-69 |
| Paths of documents, rounds, handoffs | `layout.path(slug, stage, next=…, handoff=…)` | TCW-69 |
| Verdicts | `layout.round_verdict`, `layout.current_verdict` | TCW-69 |
| The declaration file | TCW-69's `capabilities.yaml` parser (Design 7 of its spec) | TCW-69 |
| Validation after a save | the per-object rules `tcw validate` applies | TCW-73 |
| Taxonomy and capability records | `FsTaxonomyStore`, `FsCapabilitiesStore`, as today | unchanged |
| `tcw://` links | `resolve_tcw_ref` (`tcw/refs.py`), as today (`__init__.py:1158-1221`) | TCW-73 (3.0 slug form, see Notes) |
| Assignable Jira users | **proposed** Jira-only function next to `tickets list` | TCW-71 (change needed) |

1. **Who owns the item record.** **[Decision]** The viewer decides what is
   read-only from a backend fact, not a backend name: when the request stage is
   in `backend.external_stages`, the backend owns the item record (request,
   comments, stage and properties) and the viewer shows all of it read-only.
   That is exactly TCW-71's Jira backend, which keeps the request and qa
   externally (TCW-69 Design 4.12). The filesystem backend has no external
   stages, so everything is editable but the stage.
2. **The proposed `record` operation.** **[Decision, needs TCW-69 to change]**
   The viewer must show the request, comments and a link to the ticket. TCW-69's
   eight operations return none of them: `read` returns an `Item`, which has no
   request text, comments or URL (TCW-69 Design 2.1, 5). This spec proposes a
   ninth operation:

   ```python
   def record(self, folder: str) -> ItemRecord: ...
   # ItemRecord(request: str | None,          # text when the request stage is external, else None
   #            comments: tuple[Comment, ...], # oldest first; Comment(at: datetime, author: str | None, text: str)
   #            link: Link | None)             # Link(label: str, url: str), e.g. ("Jira", "https://…/browse/TCW-77")
   ```

   The filesystem backend reads its comment files (TCW-70) and returns no
   request (the request is the layout's `request/request.md`) and no link. The
   Jira backend reads the ticket's description and comments and builds the
   ticket URL. Both pass the litmus test. TCW-73's `show` and TCW-74's implement
   prompt, which reads the latest qa rejection comment in Jira mode, need the
   same reads. If the owner prefers another shape, only Design 5's
   `GET /api/work/<folder>` route changes.

### 5. The API

All routes are under `/api`, take and return JSON, and apply Design 3. A
`<folder>` is an item's folder name in the served project. Errors are mapped by
Design 11.

**Project**

- `GET /api/project` returns what the client needs to draw itself, so the client
  holds no TCW rules:
  - `id`; `recordOwner`: `"local"` or `"backend"` (Design 4.1);
  - `stages`: the enabled stage table rows in table order, each with `name`,
    `kind`, `artifact`, `verdict`, `onReject`, `external`, `completion`,
    `discard`;
  - `inboxItems`; `tags` (the registry); `scales` (priority and size names, in
    order, from TCW-69's `PRIORITIES` and `SIZES`);
  - `user` (filesystem mode: TCW-72's `user.name`, or `null`);
  - `projects`: connected project IDs, for the create form's target;
  - `axes`: which of taxonomy, capabilities and work this project keeps.
    **[Decision]** An axis with no store shows "this project keeps no taxonomy"
    (or capabilities, or work) instead of an empty tree, so "nothing here" and
    "not configured" look different. This is the complaint in the open
    aggregation item, answered for one project.

**Work**

1. `GET /api/work[?all=1]` → the board: TCW-73's `tcw work list --json`
   document for `Query()` (unfinished items and items with no stage), or for
   `Query(all=True)` with `all=1`. **[Decision]** Item payloads are the CLI's
   JSON documents unchanged, keeping the promise in
   `work/read-a-work-item` (`description.md:22-23`) that the API and the CLI
   cannot drift.
2. `GET /api/work/<folder>` → `{item, record, files, verdicts}`:
   - `item`: `tcw work show --json`;
   - `record`: Design 4.2's `ItemRecord`, or `{"unavailable": "<reason>"}` when
     the backend is unreachable (Design 7);
   - `files`: for each enabled, non-external stage whose artifact is not
     `none`, its document (path, revision, present) or its rounds and handoffs
     (each path and revision), plus the declaration file;
   - `verdicts`: `current_verdict` for each enabled verdict stage that is not
     external (`none`, `invalid`, `stale`, `accepted` or `rejected`). The
     detail shows it beside the stage's rounds.
3. `GET /api/work/<folder>/files/<path>` → `{content, revision}`.
4. `PUT /api/work/<folder>/files/<path>` with `{content, revision}` → writes the
   file (Design 10). `revision: null` creates a file that must not exist yet.
   Returns the new revision and any validation notices.
5. `POST /api/work/<folder>/files` with `{stage, kind}`, `kind` one of
   `document`, `round`, `handoff` → `{path, template}`: the path `layout.path`
   gives (`stage`, `next=True`, or `handoff=True`) and the starting text. The
   file is created by the `PUT` that follows, so a page that is closed creates
   nothing. **[Decision]** A round in a verdict stage starts with TCW-69's
   front matter, `judges` filled in (the current highest round of the stage's
   `on_reject` stage, Design 4.6 of TCW-69) and `verdict:` left empty. The
   verdict is a fixed choice above the editor (`accepted` or `rejected`) that
   writes that line; a round saved without one gets the validation notice that
   it is `invalid`.
6. `GET`/`PUT /api/work/<folder>/declaration` → the declaration file as
   structured lists (Design 6.4).
7. `PATCH /api/work/<folder>` with `{changes, expected}` → `backend.update`.
   `changes` is TCW-69's `Changes` (set, clear, add and remove per property);
   `expected` holds the values the form loaded for each property it changes
   (Design 10). Refused (403) when the record owner is the backend.
8. `POST /api/work/<folder>/comments` with `{text}` → `backend.comment`.
   Refused (403) when the record owner is the backend.
9. `POST /api/work` with `{title, properties, request, project?, stage?}` →
   the `new` function. Returns the CLI's stdout product as JSON: `{slug}`, or
   `{ticket}` when delegation stopped at the target's inbox (TCW-71).
10. `GET /api/tickets` and `POST /api/tickets/<KEY>/adopt` → TCW-71's functions.
    In filesystem mode both are 400, as the CLI's Jira-only commands are a usage
    error there (TCW-73).
11. `GET /api/options/<field>?q=<text>` → suggestions computed on the server,
    for the two sources the client cannot hold: Jira assignable users, and
    items in connected projects (Design 9).

**[Decision] Which files `files/<path>` accepts.** Only paths the layout
names, checked against the stage table:

- `<stage>/<stage>.md` for an enabled document stage, including the side stage
  (`postmortem/postmortem.md`);
- `<stage>/round-N.md` for an enabled rounds stage (TCW-69's pattern
  `^round-([1-9][0-9]*)\.md$`);
- `<stage>/handoff-<YYYYMMDDTHHMMSSZ>.md` for an enabled stage with a folder;
- `capabilities.yaml` at the item root.

A stage in `external_stages` (request and qa in Jira mode) has none. Anything
else (`item.yaml`, `comments/…`, a file someone dropped in a stage folder) is
404: it is either backend storage the viewer reaches only through operations,
or not part of the model. This is the litmus test's "bound the store folder"
rule (`docs/lifecycle/abstraction.md`), and it keeps the editor away from
`item.yaml`, whose properties go through `update`.

**Taxonomy and capabilities** keep today's routes, minus what 3.0 removes:
`GET /api/taxonomy`, `GET /api/taxonomy/<ref>`, `POST /api/taxonomy`,
`PATCH /api/taxonomy/<ref>` (`__init__.py:864-885`, `:1091-1123`,
`:1298-1338`), and the same four for `/api/capabilities` (`:889-910`,
`:1128-1152`, `:1341-1374`). A `PATCH` to an inherited entry is 403
(Design 8).

**Links:** `POST /api/resolve` stays (`__init__.py:1158-1221`), without the
"hosted projects" branch (`:1209-1215`): a reference to another project is
reported as `other-project` with its project ID, and the client draws it as a
labelled link that does not navigate.

**Removed routes:** `POST /api/work/<slug>/actions/<action>` (start, complete),
`DELETE /api/work/<slug>` (drop), `GET /api/work/interrupted-claims`,
`/api/work/<slug>/artifacts/…`, `/api/work/<slug>/sidecars/…`,
`/api/work/<slug>/plan-stages/…` (including their `DELETE` and `/open`), and
`GET /api/work/tags` (folded into `/api/project`).

### 6. Work items in the client

1. **URLs.** `/work/<folder>`, `/taxonomy/<ref>`, `/capabilities/<path>`.
   **[Decision]** A path naming a Jira key (`/work/TCW-77`) is resolved through
   `backend.lookup` and replaced by the folder's URL, since TCW-73 accepts a
   Jira key as slug input.
2. **The board.** A collapsible tree by `parent`, filters and a text search, as
   today (`docs/guide/web-viewer.md:52-70`).
   - **Filters:** stage (the enabled stages, plus "no stage" when the backend
     can report one; finished stages unselected by default, as `list` hides
     them), tags (the registry), assignee (names on the loaded items, plus
     `user`). Unticking every finished stage uses `Query()`; ticking one loads
     `Query(all=True)`.
   - **[Decision] Dates.** Work rows show and sort by creation date. 3.0 items
     have `created` and no modified time (TCW-69 Design 2.1); a Jira item's
     "updated" field is not part of the model. Taxonomy and capability rows keep
     their modified time.
   - Copy-slug, deep links, history, resizable panes and the light/dark setting
     stay.
3. **The detail.** Title, stage, properties, the request, comments and one tab
   per enabled stage that has an artifact, in table order, drawn from
   `/api/project`'s `stages`:
   - a document stage: its document, or "not written" with a **Create** button;
   - a rounds stage: its rounds newest first with their verdicts, the current
     verdict, its handoffs, and **New round** / **New handoff**;
   - the side stage (postmortem): its document, in the same way;
   - an external stage: a line saying the backend keeps it, with the link.
4. **The stage is shown, not edited.** **[Decision]** No button, menu or
   dialog moves an item. The stage line carries one sentence of plain text:
   "Move it with `tcw work advance <slug>`." The 2.x start, complete and drop
   dialogs, the Definition-of-Done checklist, the interrupted-claims banner and
   the tracker field go (`content-views.tsx:1155-1365`,
   `shared-components.tsx:195-235`, `:255-290`).
5. **Documents** open in today's editor with live preview
   (`shared-components.tsx:497-540`). Typing `tcw://` offers objects from all
   three axes (Design 9).
6. **The declaration file** (`<item>/capabilities.yaml`). **[Decision]** It is
   edited through a form with TCW-69's full schema: capability `new`,
   `changed` and `removed` lists and taxonomy `new`, `changed` and `removed`
   lists. The ticket's form named only the capability lists; TCW-69's schema
   adds the taxonomy ones, and a form without them would drop them on save.
   - The server parses the file with TCW-69's parser and returns the six
     lists; it writes them back in schema order, omitting empty lists.
   - A file the parser rejects (unreadable YAML, an unknown key) opens as plain
     text in the document editor with the parser's message, so it can be
     fixed; the form takes over once it parses.
   - Comments inside the YAML are not kept by a form save. The form says so.
7. **Properties.** In filesystem mode: title, priority, effort, complexity, tags,
   assignee, parent, blocked-by and blocks, each as Design 9 sets out. `blocks`
   is written as an update to the other item's `blocked-by` (TCW-69 Design
   2.5), through the same function `edit --blocks` uses, with its delegation
   conditions when the other item is in another project (TCW-70).
8. **Comments.** Listed oldest first. In filesystem mode a box adds one through
   `backend.comment`; comments cannot be edited or removed, because they carry
   forced-move and discard reasons.
9. **Creating.** A **New item** form: title, the request text, priority, effort,
   complexity, tags, assignee, parent, blocked-by, a target project (connected
   projects; default this one) and, where `inboxItems` is true, "start at
   inbox". **[Decision]** In Jira mode the effort and complexity fields appear
   only when TCW-71's field mapping configures them, since otherwise the CLI
   refuses those flags.
10. **Inbox tickets (Jira mode).** A **Tickets** view lists TCW-71's default
    inbox (or the configured `inbox-query`); **Adopt** runs TCW-71's adopt and
    opens the new item.

### 7. Jira mode at runtime

1. **The board is one request to Jira**, TCW-71's batched `list`, not one per
   item.
2. **Read-only content.** The request, comments, stage and properties come from
   Jira and are read-only, each with "Open in Jira" (`record.link`). Property
   fields appear only on the create form (Design 6.9).
3. **Unreachable.** When an operation raises `Unreachable` (TCW-69 exit 5):
   - the item's files stay readable and editable; they are the layout's files on
     disk and need no network;
   - `record` and properties show "Jira is unreachable" with **Retry**;
   - **[Decision]** the board falls back to the item folders found under the work
     path, each shown by its folder name with its stage "unavailable", with a
     banner and **Retry**. Listing those folders is a layout read, not a backend
     operation; TCW-69's layout has no such function yet (see Notes).
4. **Credentials missing.** **[Decision]** `tcw serve` still starts. Jira-owned
   content shows as unavailable with TCW-71's message naming the missing
   environment variable, so a user can still read and edit the files.
5. **No stage.** Items in an unmapped Jira status have `stage: null` and appear
   under the "no stage" filter value (TCW-69 Design 5.1 keeps them in the
   default query).

### 8. Taxonomy and capabilities

1. Reading, creating and editing work as today, through the same stores, with
   validation notices after a save (`__init__.py:168-180`) and the existing
   refusal of an unresolved capability reference at save
   (`docs/capabilities/web/editing/description.md:10-15`).
2. **Inherited entries** (`extends`) are listed with a marker naming the
   project they come from (today's `origin`, `content-views.tsx:632`,
   `shared-components.tsx:477-488`) and are offered in autocomplete.
   **[Decision]** They are read-only in the viewer: their edit control is
   absent and the server refuses a `PATCH` (403). An override is a deliberate
   act the CLI already offers (`capabilities/override-inherited`).
3. **[Decision] Removed capability fields.** `Planning doc` and `Tracker` are
   not offered by any form (`content-views.tsx:51-64`, `:1096`). They are still
   in the ledger schema (`CAP_FIELDS`, `tcw/store/base.py:844-847`) and in many
   records, so a record that carries one shows it read-only in the detail, and a
   save never sends or clears it (today's `PATCH` sends only changed fields,
   `web/client/src/ui/app.tsx:602-610`). Removing them from the schema is not
   this slice's (Notes).

### 9. Autocomplete everywhere

Every editable field either offers suggestions or is a fixed choice. One
component, today's `ReferenceInput` (`reference-input.tsx`), gains a mode for
what happens to text that matches no suggestion: **refuse** (the value cannot be
committed; the field shows why), **warn** (committed, with a warning under the
field) or **allow**. Fixed sets are selects.

| Field | Offered | Something else | Source |
| --- | --- | --- | --- |
| Work: parent | items in this project, minus the item and its descendants | refused | board (`all`) |
| Work: blocked-by, blocks (filesystem) | items in this project, and items in connected filesystem-mode projects found on this machine | a full `project/folder` slug for another project is allowed with a warning; anything else refused | board; `/api/options` |
| Work: blocked-by (Jira, create form) | items with a TCW Item in this project | refused | board (`all`) |
| Work: tags | the registry, as chips | refused | `/api/project` |
| Work: assignee (filesystem) | names on items, plus `user` | allowed (free text) | board; `/api/project` |
| Work: assignee (Jira, create form) | assignable users | refused | `/api/options` |
| Work: priority, effort, complexity | the fixed scales | select only | `/api/project` |
| New item: target project | this project and connected projects | refused | `/api/project` |
| New item: start at inbox | shown only when `inboxItems` | — | `/api/project` |
| Filters: stage, tags, assignee | enabled stages (+ "no stage"), registry, known assignees | — | as above |
| Taxonomy: parent, relates, a feature's vocabulary | existing entries including inherited (vocabulary entries only, for a feature's vocabulary) | refused | taxonomy list |
| Taxonomy: kind | Vocabulary, Feature | select only | fixed |
| Capability: path | existing path segments, one segment at a time | new segments allowed | capability list |
| Capability: feature; subject | taxonomy features; vocabulary | refused | taxonomy list |
| Capability: roles, when | existing `roles/…` and `conditions/…` capabilities; a leading `!` negates, on both | refused | capability list |
| Capability: blocked-by, superseded-by | existing capabilities | refused | capability list |
| Capability: status, priority, lifecycle | their fixed sets (`CAP_STATUSES`, `CAP_PRIORITIES`, `CAP_LIFECYCLES`, `base.py:841-843`) | select only | `/api/project` |
| Capability: name, gaps | free text | — | — |
| Declaration: capability `new` | capability paths | may be new | capability list |
| Declaration: capability `changed`, `removed` | capability paths | must exist; refused | capability list |
| Declaration: taxonomy `new` | entries | may be new | taxonomy list |
| Declaration: taxonomy `changed`, `removed` | entries | must exist; refused | taxonomy list |
| Markdown editor: typing `tcw://` | any object in the three axes, inherited included | saves; the link renders as unresolved | all three lists |

1. **"Refused" is enforced by the server too.** **[Decision]** The server checks
   the same lists before calling the operation, and answers 400 naming the field
   and value. A form cannot be bypassed by sending the request by hand. Where
   the operation already refuses (an unregistered tag, a non-slug blocker, a
   parent cycle: TCW-69 Design 2.4; an unresolved capability reference: the
   store), the operation's message is used.
2. **Cross-project suggestions.** **[Decision]** For blocked-by in filesystem
   mode, the server lists items in each connected project whose backend is
   filesystem and whose path resolves on this machine, by opening that project's
   backend and calling `list`. Connected Jira-mode projects are not queried:
   that would need their credentials and the network for a suggestion. A slug
   typed for them is accepted with the warning.
3. **Matching** stays today's ranking by name and identifier
   (`reference-search.ts:131-159`), ten results at most.

### 10. Saving, stale edits and validation

1. **Files** (documents, rounds, handoffs, the declaration file). The revision
   is a SHA-256 hash of the file's bytes. A `PUT` holding the write lock reads
   the current file; if its hash differs from the `revision` sent (or the file
   exists when `revision` is `null`), it answers 409 with
   `code: "stale-revision"`, which the client already answers with its conflict
   banner while keeping the draft (`web/client/src/model/api.ts:43-49`).
   Otherwise it writes and returns the new hash. Files are written whole, as
   UTF-8, through a temporary file renamed into place.
2. **Taxonomy and capability records** keep their stores' revisions
   (`core_revision`, `__init__.py:1322-1323`, `:1354-1355`) and 409.
3. **[Decision] Item properties.** `backend.update` takes no revision (TCW-69
   Design 5). The server, holding the lock, reads the item and compares each
   property the request changes with the `expected` value the form loaded; any
   difference is 409 `stale-revision`, naming the property. Properties the form
   did not change are not sent, so they are never overwritten. A change made by
   the CLI between that read and the update is not caught; that window is one
   read long and is accepted (Risks).
4. **Validation on save.** After a successful write the server runs the
   object-level rules `tcw validate` applies to that object, offline, and returns
   any findings as `warnings`. They never undo the save; the client keeps them
   as a "Saved with validation issues" notice, as today
   (`__init__.py:168-180`). For item files this includes: `tcw://` links that do
   not resolve; a round in a verdict stage whose verdict is `invalid`; the
   mid-work records check on the declaration file
   (`records_problems(finished=False)`, TCW-69 Design 7); and the reference
   checks on `parent` and `blocked-by` after a property change (TCW-69 Design 9).
   Validation needs no network in either mode.

### 11. Errors

| Cause | HTTP status | Body `code` |
| --- | --- | --- |
| `UsageError` (2), a malformed request, a value outside a "refused" list | 400 | `usage` |
| Host/Origin check failed; a write to backend-owned content or an inherited entry | 403 | `forbidden`, `read-only` |
| `NotFound` (4), an unknown route or file | 404 | `not-found` |
| `Refused` (3), e.g. a name collision or delegation conditions | 409 | `refused` |
| Stale edit | 409 | `stale-revision` |
| Body over 1 MiB | 413 | `too-large` |
| `Unreachable` (5) | 503 | `unreachable` |
| `BackendError` (1), any other failure | 500 | `error` |

Every error body is `{"error": "<message>", "code": "<code>"}` and the message
is the operation's own. A 500 never carries a Python traceback.

### 12. Kept, cut and added

| | Item |
| --- | --- |
| **Kept** | The React client, its tree, filters, search, copy-slug, deep links and history, resizable panes, light/dark setting, editor with live preview, validation notices, 409 conflict banner; taxonomy and capability reading, creating and editing; `tcw://` link rendering; the packaged prebuilt bundle and `check:build`; every security rule. |
| **Cut** | Node.js and Fastify (`runtime.py`, `web/server/`, `server.cjs`); the sidecar and its token; aggregation of child projects (`cli.py:469-479`, `__init__.py:500-565`); start, complete, drop, recover, the Definition-of-Done checklist and interrupted claims; strict-tracker refusals and owed tickets; git commits; plan-stage documents and sidecars; the desktop opener; the 2.x status and artifact lists; `initiative`; the `Planning doc` and `Tracker` capability form fields; delete routes; work rows' modified time. |
| **Added** | One-process static serving with route fallback; Host/Origin checks on reads; stage tabs from the stage table; rounds with verdicts, handoffs and "create" for each; the declaration form; comments (add-only in filesystem mode); assignee; Jira mode (read-only record, "Open in Jira", tickets and adopt, unreachable handling); creating at inbox and into another project; the refuse/warn/allow autocomplete modes, tag chips, path-segment and `tcw://` completion, `!` on roles. |

### 13. No stage names outside the table

TCW-69 forbids stage names as literals outside its stage table (TCW-69 Design
3.2, criterion 5). **[Decision]** The viewer follows the same rule: the Python
in `tcw/serve/` and the TypeScript in `web/client/src/` contain no stage name
as a string literal, docstrings and comments excepted. Tabs, filters and file
rules come from `/api/project`'s `stages`. A project-defined stage added later
then appears in the viewer with no viewer change.

### 14. Documentation

- `docs/guide/web-viewer.md` is rewritten (this slice owns it): one Python
  process, no Node; what can be read, edited and created; the Jira-mode rule;
  the autocomplete table in plain words; the security rules; no lifecycle
  actions, with the CLI command to use instead; contributor build notes.
- **[Decision]** The two sentences that make Node a prerequisite of
  `tcw serve` in the setup skill (`skills/setup/SKILL.md:8`,
  `skills/setup/references/install.md:71-74`) are corrected here, because this
  slice is what makes them false. TCW-74 rewrites that skill; whichever lands
  second keeps the correction.
- `README.md`'s web app section (`README.md:768-805`) and install note
  (`:109-110`) are TCW-75's, per its ticket.
- A release-notes and a changelog entry under `upcoming/`, named by this item's
  folder name.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| Board, item, properties, comment, create, lookup | **Backend interface** (TCW-69). Both backends implement each. |
| `record` (request text, comments, link) | **Backend interface**, proposed. Jira: issue description, comment list, browse URL. Filesystem: comment files, no request, no link. |
| Tickets list, adopt, assignable users | **Jira-only functions** outside the interface, as TCW-69 already places `tickets` (Design 5.6). Filesystem mode answers 400 or derives the list. |
| Documents, rounds, handoffs, declaration file | **Shared layout** (TCW-69). Git owns them in both modes; reading and writing them is a file operation in both. |
| Board fallback while unreachable | **Shared layout** read of item folder names; needs a layout listing function (Notes). |
| Stale-edit check on files | **Shared layout** (content hash). On properties: read-then-update over the interface, so any backend supports it. |
| Taxonomy and capabilities | The existing filesystem stores, unchanged. |
| What is read-only | Derived from `external_stages`, a declared backend fact, never from a backend name. |

The viewer adds no operation of its own; each route calls one of these.

## Harness compatibility

`tcw serve` is a CLI command and behaves the same under Claude and Codex. No
requirement here depends on a skill, hook or injected context. The setup skill
change (Design 14) is text both harnesses read.

## Acceptance criteria

Python criteria are pytest tests in `tests/serve/`, which start the server on
`--port 0` in a thread and send real HTTP requests. "Filesystem fixture" is a
project built with the 3.0 CLI in a temporary directory. "Jira-mode fixture"
uses TCW-69's in-memory backend (`tests/work/memory_backend.py`) configured
with `external_stages = {request, qa}` and `inbox_items = False`, and a stub
`record` that returns a request, two comments and a link. Browser criteria are
Playwright tests in `web/e2e/`.

1. **One process, no Node.**
   - With `PATH` holding no `node`, `tcw serve --no-open --port 0` starts and
     `GET /` returns `index.html`.
   - While it serves with `--no-open`, after one request to every route,
     `ps -o pid= --ppid <server pid>` (or `pgrep -P <server pid>`) lists no
     child process.
   - `tcw/serve/dist/server.cjs`, `tcw/serve/runtime.py` and `web/server/` do
     not exist; `package.json` has no `fastify`.
   - No module under `tcw/serve/` imports `subprocess`, `os.system`,
     `os.popen` or the git helpers in `tcw/store/fs.py`.
2. **stdout and exit codes.**
   - stdout is exactly one line matching `^http://127\.0\.0\.1:\d+/$`, and its
     port answers.
   - A second `tcw serve --port <that port>` exits 1 with the port on stderr and
     nothing on stdout.
   - Outside a project it exits 1.
   - `SIGTERM` exits 0.
3. **Static files.**
   - `GET /work/anything` and `GET /taxonomy` return `index.html`.
   - `GET /assets/<built js file>` returns it as `application/javascript`.
   - `GET /../pyproject.toml`, `GET /%2e%2e/pyproject.toml` and
     `GET /assets/..%2f..%2findex.html` do not return a file outside
     `dist/client`.
   - `GET /api/nope` is a JSON 404.
4. **Security.**
   - `GET /api/work` with `Host: evil.example` is 403; with
     `Host: 127.0.0.1:<port>` and `Origin: http://evil.example` it is 403; with
     no `Host` it is 403. `GET /` with `Host: evil.example` is 403.
   - `POST /api/work` with `Content-Type: text/plain` is 400 and creates nothing.
   - A body of 1 MiB + 1 byte is 413 and creates nothing.
   - Every response, a 404 and a 403 included, carries
     `Content-Security-Policy: default-src 'self'`.
   - In a Jira-mode fixture whose credential variables hold a marker string, no
     response body or header from any route contains the marker.
5. **No lifecycle.**
   - `POST /api/work/<f>/actions/start`, `…/actions/complete` and
     `DELETE /api/work/<f>` are 404 and the item's stage is unchanged.
   - With the memory backend recording its calls, a pytest run that sends one
     valid request to every route records no `set_stage` call, and no module
     under `tcw/serve/` imports TCW-69's `advance` module.
   - A Playwright test finds no control labelled start, advance, complete,
     drop, discard or reopen on an item's page, and the text
     "`tcw work advance`" beside the stage.
6. **Files.**
   - `GET /api/work/<f>` lists a tab entry for each enabled stage with an
     artifact; with `plan` disabled there is no plan entry.
   - `POST …/files {stage: review, kind: round}` returns
     `review/round-3.md` when rounds 1 and 2 exist, and the same path as
     `tcw work path <slug> review --next`. Its template has `judges:` equal to
     the highest implement round.
   - `PUT` with `revision: null` creates the file; a second identical `PUT` is
     409 `stale-revision`.
   - `PUT` with a stale revision is 409 and the file is unchanged.
   - `GET`/`PUT` of `item.yaml`, `comments/x.md`, `spec/notes.md`,
     `spec/spec.md` with `spec` disabled, and `qa/round-1.md` in the Jira-mode
     fixture are 404.
   - `POST …/files {stage: completed, kind: document}` is 400 (no artifact).
7. **Declaration form.**
   - A file with all six lists round-trips through `GET` and `PUT` with the same
     lists.
   - `PUT` with `changed: [no/such/path]` is 400 naming the path;
     `new: [no/such/path]` is accepted.
   - A file with an unknown key returns the parser's message, and the client
     opens it as plain text (Playwright).
   - The written file has no empty lists and keys in schema order.
8. **Properties and comments (filesystem).**
   - `PATCH` with `{changes: {priority: high}, expected: {priority: medium}}`
     updates; repeating it with `expected: {priority: medium}` is 409 naming
     `priority`.
   - A `PATCH` setting `tags: [unregistered]` is 400 and the item is unchanged.
   - A `PATCH` setting a `parent` that is not an item in this project is 400.
   - `POST …/comments` adds one comment, and `GET /api/work/<f>`'s
     `record.comments` ends with it. There is no route that edits or removes a
     comment.
9. **Jira mode (memory backend).**
   - `GET /api/project` says `recordOwner: "backend"`.
   - `PATCH /api/work/<f>` and `POST …/comments` are 403 `read-only`, and the
     backend records no `update` or `comment` call.
   - `GET /api/work/<f>` carries `record.request`, both comments and
     `record.link`.
   - With the backend raising `Unreachable` on `list`, `read` and `record`:
     `GET /api/work` answers 200 with `fallback: true` and one row per item
     folder, each with stage `unavailable`; `GET`/`PUT` of `spec/spec.md` still
     succeed; `GET /api/work/<f>` answers 200 with `record.unavailable` set.
   - `POST /api/work` creates through the backend's `create` with the request
     text, and `/api/tickets` routes are 400 in the filesystem fixture.
10. **Jira mode in the browser.** Playwright runs against a fixture project whose
    `work.jira.site` points at a stub Jira HTTP server started by the suite. It
    checks that the request, comments and properties have no edit control and
    each shows "Open in Jira" with the ticket URL; that the board loads with one
    search request to the stub; that adopting a stub inbox ticket opens the new
    item; and that stopping the stub shows "Jira is unreachable" with Retry while
    `spec/spec.md` stays editable.
11. **Autocomplete (Playwright and client unit tests).**
    - Each "refused" field in Design 9's table will not commit an unknown value,
      and each server route answers 400 for it when sent by hand (pytest, one
      case per field).
    - In filesystem mode a typed `other-project/2026-01-01-x` blocked-by is kept
      with a warning.
    - Tags render as chips from the registry; priority, effort, complexity,
      taxonomy kind and capability status, priority and lifecycle are selects.
    - Typing `tcw://` in a markdown editor offers objects from all three axes,
      and choosing one inserts its link.
    - `!` negation is accepted on Roles and When.
    - A capability path field offers existing segments one at a time and accepts
      a new segment.
12. **One project.**
    - In a fixture with a registered child project holding items, `GET /api/work`
      returns only the served project's items.
    - A `tcw://` link to another project's item resolves as `other-project` with
      that project's ID.
    - An inherited capability is listed with its origin, offered in
      autocomplete, and `PATCH` to it is 403.
13. **No stage names.** A test scans `tcw/serve/**/*.py` and
    `web/client/src/**/*.{ts,tsx}` (tests excepted) and finds no string literal
    equal to, or containing as a whole word, a name from TCW-69's `STAGES`.
14. **Validation notices.**
    - Saving `spec/spec.md` with a `tcw://T/no-such-term` link returns 200 with a
      warning naming the link, and the file holds the saved text.
    - Saving a review round without a verdict returns a warning that it is
      invalid.
15. **Build.** `pnpm build` produces `tcw/serve/dist/client` and nothing else
    under `tcw/serve/dist`; `pnpm check:build` passes on the committed tree.
16. **Removed tests.** `tests/test_serve_runtime.py`,
    `tests/test_serve_descendants.py`, `web/server/src/server.test.ts`, the
    Playwright tests "runs Work start and complete lifecycle controls" and
    "drops a backlog Work item through the confirmation modal"
    (`web/e2e/parity.spec.ts:632`, `:687`) and the `lifecycle-dialog` snapshot
    are deleted. The full pytest suite passes.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Command and process | 1, 2 |
| 2 Client and shipping | 3, 15 |
| 3 Security | 4 |
| 4 Operations, ownership | 5, 9 |
| 5 API, file rules | 6, 7, 8, 9 |
| 6 Client (work) | 5, 6, 7, 11 |
| 7 Jira at runtime | 9, 10 |
| 8 Taxonomy, capabilities | 11, 12 |
| 9 Autocomplete | 11 |
| 10 Saving, validation | 6, 8, 14 |
| 11 Errors | 4, 6, 8, 9 |
| 13 Stage names | 13 |

## Risks

- **Built on four unfinished slices.** The viewer needs TCW-69's model, both
  backends, TCW-72's `user.name` and TCW-73's JSON documents and validation.
  Mitigation: the plan does the process change first (Design 1-3, against
  today's API, which needs none of them), then the 3.0 item model once TCW-70
  lands, then Jira mode once TCW-71 lands.
- **The proposed `record` operation may not be accepted.** Without it the viewer
  cannot show the Jira request or comments, nor filesystem comments. Mitigation:
  it is raised as a cross-slice finding before planning; only one route depends
  on its shape.
- **Stale-edit protection on properties has a gap.** A CLI edit landing between
  the server's read and its update is overwritten for the properties the form
  changed. Mitigation: the lock closes the gap between viewer requests; only the
  properties the user changed are written; the window is one read long.
- **Form saves drop YAML comments** in the declaration file. Mitigation: the form
  says so, and the file can still be fixed as plain text when malformed.
- **Moving the Host/Origin check into Python changes who enforces it.** A mistake
  re-opens DNS rebinding. Mitigation: criterion 4 covers reads, writes, static
  files and a missing `Host`.
- **The Playwright suite is not in CI.** A client regression can ship.
  Mitigation: `check:build` keeps the bundle honest, and the pytest API tests
  cover every rule the server enforces, including "refused" fields.
- **A large client change.** Most views change. Mitigation: the plan keeps
  today's components (tree, editor, `ReferenceInput`) and changes their data,
  rather than rewriting them.

## Notes

- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  1. No lifecycle control at all; the stage line names `tcw work advance` in plain
     text (Design 6.4).
  2. "Single process" also rules out child processes per request; the desktop
     opener route goes (1.7).
  3. `--port 0` picks a free port (1.2).
  4. Configuration is read per request (1.8).
  5. The Host/Origin check applies to every request, static files included (3.2).
  6. What is read-only follows `external_stages`, not the backend's name (4.1).
  7. A ninth backend operation, `record(folder)`, for request text, comments and
     the ticket link (4.2), which needs TCW-69 to change.
  8. Each axis without a store says so instead of showing an empty tree (5).
  9. API item payloads are `list --json` and `show --json` unchanged (5.1).
  10. A new verdict round starts with `judges` filled in and the verdict a fixed
      choice (5.5).
  11. `files/<path>` accepts only the paths the layout names (5).
  12. A Jira key in a URL redirects to the folder (6.1).
  13. Work rows show and sort by creation date (6.2).
  14. The declaration form covers TCW-69's taxonomy lists too, and a malformed
      file opens as plain text (6.6).
  15. Jira-mode create form shows effort and complexity only when mapped (6.9).
  16. While Jira is unreachable, the board falls back to folder names (7.3).
  17. Missing Jira credentials do not stop the server (7.4).
  18. Inherited entries are read-only (8.2).
  19. `Planning doc` and `Tracker` leave the forms but stay visible and untouched
      on records that carry them (8.3).
  20. "Refused" is enforced by the server (9.1).
  21. Cross-project suggestions come only from connected filesystem-mode projects
      found locally (9.2).
  22. Property edits carry the expected old values for a stale-edit check (10.3).
  23. No stage-name literals in `tcw/serve/` or the client (13).
  24. This slice corrects the setup skill's Node sentences (14).
- **Answers to the ticket's implicit questions.** Lifecycle moves are absent from
  the UI entirely, not hidden behind a setting (decision 1). The declaration file
  is TCW-69's `<item>/capabilities.yaml`, not `spec/capabilities.yaml`
  (decision 14).
- **Changes other slices need** (nothing has been posted to their tickets):
  - **TCW-69:** add `record(folder)` (or an equivalent read of the request,
    comments and link); add a layout function listing the item folders under the
    work path (TCW-71's `lookup` already implies one); expose the `judges` number
    for a new verdict round as a public function (its spec's Risks say prompts
    "get the number from `path` output", but `path` returns only a path).
  - **TCW-71:** implement `record`; add a Jira-only `assignable_users(query)`
    beside `tickets list`; accept an `http://127.0.0.1:<port>` site (or offer a
    test seam) so the browser tests can use a stub Jira.
  - **TCW-73:** keep a per-object entry point to `validate`'s rules (today
    `ValidationTarget(axis, ref)`, `__init__.py:168-173`) that covers item files;
    settle the 3.0 form of `tcw://W/…` references to `project/folder` slugs and
    Jira keys, which no sibling ticket names and `tcw/refs.py` must change for.
  - **TCW-74:** the setup skill's Node sentences (decision 24); its implement
    prompt needs the same `record` read for Jira qa rejections.
  - **TCW-75:** the README's web app section and install note are false once this
    lands; both should ship in the same release.
  - **TCW-76 / unowned:** the `Planning doc` and `Tracker` capability fields stay
    in `CAP_FIELDS` (`base.py:844-847`). TCW-69 gave `Planning doc` to TCW-76;
    no slice owns `Tracker`.
- **Sibling tickets that disagree.** The TCW-77 ticket, and TCW-73's, TCW-74's and
  TCW-75's tickets, still say `spec/capabilities.yaml`; TCW-69's confirmed spec
  and TCW-76's update section say `<item>/capabilities.yaml`. This spec follows
  TCW-69.
- **Open items this slice makes obsolete.**
  `docs/work/backlog/2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`
  (no combined boards in 3.0) and the web-app part of
  `docs/work/inbox/2026-09-30-follow-renames-in-the-web-app-tracker-verbs-and-the-capability-drift-check.md`
  (3.0 keeps no rename aliases). Both should be discarded with a reason pointing
  here when this item completes.
- **Questions only the owner can answer.**
  - Is `record(folder)` the right way to add the missing reads, or should they
    be separate operations or fields on `Item`?
  - Should the process change (Design 1-3) land as its own early change against
    today's API, possibly in a 2.x release, or only on the 3.0 branch?
  - Is losing a modified time on work rows acceptable, given that 3.0 items have
    none?
  - Should inherited taxonomy and capability entries really be read-only here, or
    should the viewer offer the CLI's override?
  - Who removes `Planning doc` and `Tracker` from the capability schema?
- **Size.** This is one item, planned in phases: process and security first, the
  3.0 work views second, Jira mode third, autocomplete across all of them. The
  first phase can land before TCW-70.
- **Assumption:** TCW-73 keeps `list --json` and `show --json` as stable JSON
  documents suitable for the API; their exact fields are TCW-73's.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, per `CLAUDE.md`.
