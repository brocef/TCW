# Spec - Interactive local web editor for TCW objects

## Capability changes

- **Declared for this work:** `web/editing#edit-tcw-content-in-a-local-web-app` (currently
  `Missing`). A user can create and edit TCW Work, Taxonomy, and Capabilities
  objects through the local `tcw serve` web app, including Markdown bodies,
  lifecycle artifacts, YAML-backed metadata, and bounded sidecars. Flip to
  `Supported` at completion.
- **Feature:** `local-web-app` (already registered by this planning item) over
  the existing `work-item`, `term`, `capability`, and `node` vocabulary entries.
- **Related existing capability:** `web#browse-tcw-content-in-a-local-web-app`
  remains `Supported`; this work extends the same web surface from read-only
  browsing to explicit local editing and creation.

## Problem

`tcw serve` now gives users a local read-only web view of Work, Taxonomy, and
Capabilities. That removes the need to browse everything through the CLI, but it
still sends users back to the terminal or editor for the actual TCW workflow:
creating objects, editing Markdown artifacts, adjusting metadata, and evolving
capabilities.

The next step is a write-capable local web app. The hard part is not just adding
forms: TCW's portability depends on the model staying storage-abstracted. The
web layer must not become a second filesystem adapter that edits `docs/` paths
directly.

## Goals

- Let users edit existing TCW objects from the browser:
  - work item `state.yaml` fields exposed through the work model;
  - work item body and lifecycle artifacts (`initial-request.md`, `spec.md`,
    `plan.md`, `outcome.md`, `refined-outcome.md`);
  - work sidecars such as `capabilities.yaml` through a bounded attachment or
    named-sidecar surface;
  - taxonomy descriptions and `meta.yaml` fields (`name`, `kind`, `relatesTo`,
    `vocabulary`);
  - capability bodies and inline metadata fields (`Status`, `Planning doc`,
    `Feature`, `Subject`, etc.).
- Let users create new TCW objects from the browser:
  - work items, with priority, effort, complexity, blockers, parent, and
    initiative fields where supported;
  - taxonomy Vocabulary and Feature entries, including feature vocabulary refs;
  - capability entries, including status and metadata.
- Provide rich Markdown editing for Markdown-required lifecycle files and other
  Markdown body surfaces. MDX Editor is the reference candidate.
- Route all writes through abstract store operations. Filesystem-specific
  Markdown/YAML details stay in `Fs*Store` adapters.
- Keep the app local-first: loopback binding, no auth scope expansion, no remote
  CDN requirement at runtime.

## Non-goals

- Multi-user collaboration, merge conflict UI, or live concurrent editing.
- Remote tracker adapters. The design should be implementable by a future remote
  adapter, but this work still ships filesystem adapters only.
- A general filesystem browser or arbitrary file editor.
- Replacing the CLI lifecycle commands. The web app can invoke equivalent store
  operations, but the CLI remains supported.
- Worktree management in the browser. If lifecycle actions are included, they
  use the existing store semantics; branch/worktree creation and merge conflict
  handling remain CLI-only unless separately specified.

## Constraints

- Apply the abstraction litmus test before adding store methods. If a future
  non-filesystem store could not implement the operation, keep it as a private
  filesystem-adapter detail or redesign it.
- All web write endpoints must validate structured input before mutating stores.
- The server continues to bind to `127.0.0.1` only.
- Markdown editing must preserve Markdown files as Markdown. MDX syntax support
  is acceptable, but the stored artifact remains `.md` text unless the project
  deliberately changes that contract.
- If MDX Editor is used, package it so installed `tcw serve` works without
  fetching from a CDN at runtime.
- Editable object/detail payloads carry a revision token. Update requests must
  include the revision they were based on; stale writes return `409` instead of
  silently overwriting concurrent CLI/editor changes.
- Store methods own final validation and write atomicity. The HTTP layer may do
  request-shape checks, but it must not be the only enforcement point.
- Requests have a documented maximum body size; oversized writes are rejected
  before reading the whole payload into editor/store code.

## Current-state findings

- `tcw serve` currently lives in `tcw/serve/__init__.py` with a
  `ThreadingHTTPServer`, static files under `tcw/serve/static/`, and read-only
  JSON endpoints for work, taxonomy, and capabilities.
- The frontend is vanilla JS in `tcw/serve/static/app.js`; `marked.min.js` is
  vendored for read-only Markdown rendering.
- `WorkStore` already exposes `create`, `get`, `query`, `artifacts`,
  `artifact_locator`, `set_field`, and lifecycle transition primitives. It does
  not yet expose artifact read/write or named sidecar write operations.
- `TaxonomyStore` exposes `add`, `remove`, `get`, `list`, `search`, and
  `check`, but no update method for an existing term's description or metadata.
- `CapabilitiesStore` exposes `add`, `remove`, `set`, and read/search/check
  methods. `set` handles inline metadata fields, but body updates need an
  abstract operation if the browser edits capability prose.
- The completed read-only viewer spec already selected the write-ready API
  direction: later writes add POST/PATCH routes that call store methods instead
  of discovering files by path.

## Proposed behavior

### 1. Store write surfaces

Add the smallest abstract write operations needed for the UI:

- `WorkStore`:
  - create new items with the same supported inputs as `tcw work new` and
    `tcw work edit`: title, body, priority, effort, complexity, blockers,
    parent, and initiative;
  - update body/overview text and allowed fields through a typed allowlist, not
    arbitrary `set_field` keys;
  - read and write lifecycle artifact content by bounded artifact name;
  - read and write bounded named sidecars/attachments where the model supports
    them, starting with `capabilities.yaml`;
  - expose lifecycle actions only through semantic operations (`start`,
    `complete`, `drop`) that preserve blocker, DoD, and legal-transition checks.
- `TaxonomyStore`:
  - update existing term fields and description;
  - validate Feature vocabulary refs through existing taxonomy resolution.
- `CapabilitiesStore`:
  - update capability body text;
  - continue using `set` for metadata fields;
  - create capability objects in a new file or, when explicitly requested, add a
    new heading to an existing capability file through a portable abstract
    operation. Do not pretend `add(file_id)` can append to an existing file.

The filesystem adapter owns the exact YAML/Markdown file layout. The web layer
talks in object ids, field names, artifact names, sidecar names, and content.
Each abstract write method validates the full requested change before writing;
validation failures must leave the backing store unchanged.

The bounded registries live with the store model, not the web layer:

- lifecycle artifacts use the existing `WORK_ARTIFACTS` registry;
- work sidecars get an explicit registry such as `WORK_SIDECARS`, starting with
  `capabilities.yaml`, including expected media type and validation rules;
- capability metadata continues to use `CAP_FIELDS`/`CAP_STATUSES`;
- taxonomy editable fields are declared in the taxonomy store contract.

Where a CLI command already performs the same operation, refactor it to call the
new abstract store method or a shared helper behind that method. The web app
must not introduce a divergent write path with different validation semantics.

### 2. HTTP API

Add write routes beside the existing GET routes. Exact route names can be tuned
during implementation, but the contract should stay resource-oriented:

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/work` | Create a work item. |
| PATCH | `/api/work/<slug>` | Update allowed work fields and body. |
| GET | `/api/work/<slug>/artifacts/<name>` | Read a Markdown lifecycle artifact. |
| PUT | `/api/work/<slug>/artifacts/<name>` | Replace a Markdown lifecycle artifact. |
| GET | `/api/work/<slug>/sidecars/<name>` | Read a bounded sidecar. |
| PUT | `/api/work/<slug>/sidecars/<name>` | Replace a bounded sidecar. |
| POST | `/api/work/<slug>/actions/start` | Start a work item through `WorkStore.start`. |
| POST | `/api/work/<slug>/actions/complete` | Complete a work item through `WorkStore.complete`. |
| DELETE | `/api/work/<slug>` | Drop an inbox/backlog work item through `WorkStore.drop`. |
| POST | `/api/taxonomy` | Create a Vocabulary or Feature entry. |
| PATCH | `/api/taxonomy/<ref>` | Update an existing taxonomy entry. |
| POST | `/api/capabilities` | Create a capability entry. |
| PATCH | `/api/capabilities/<ref>` | Update capability metadata and/or body. |

Server behavior:

- request bodies are JSON;
- reject oversized request bodies before parsing; the exact limit should be
  documented in the implementation and covered by tests;
- editable text resources use JSON envelopes:
  `{ "name": "...", "content": "...", "mediaType": "text/markdown|application/yaml|text/plain", "revision": "..." }`;
- object update requests use `{ "revision": "...", "fields": {...}, "body": "..." }`.
  Omitted keys mean no change; `null` clears nullable fields only where the
  store contract permits it; empty strings are preserved as explicit values;
- `<slug>`, `<ref>`, and `<name>` path parameters are single URL path segments
  encoded with `encodeURIComponent` semantics. Refs containing `/` or `#` must
  be percent-encoded by the client and decoded exactly once by shared route
  helpers. Subresource routes must be matched before the existing work-detail
  catch-all route;
- validation failures return 400 with a useful message;
- missing ids return 404;
- stale revision tokens return 409 and do not write;
- store or check failures return 409/422 where the user can fix input;
- permission, disk-full, or other write I/O failures return a clear 500-class
  response and should not corrupt the previous committed file content;
- unhandled errors remain per-request 500s and do not stop the server.

### 3. Frontend editing experience

The first screen remains the usable TCW app, not a landing page. The existing
three-axis layout should gain:

- Edit and Create commands in each axis.
- Form controls for structured fields, using selects/toggles/text inputs where
  the value space is bounded.
- Rich Markdown editor panes for Markdown bodies and lifecycle artifacts.
- Raw YAML editor panes for bounded YAML sidecars/metadata only where a
  structured form would hide necessary expressiveness. Prefer structured forms
  for known fields and reserve raw YAML for advanced editing.
- Save, cancel, dirty-state, validation-error, and refresh states.
- Browser close, hard refresh, and tab/view switches warn or block when there
  are unsaved edits.

MDX Editor is the preferred rich Markdown editor if it can be packaged cleanly.
Because it is a React package rather than a drop-in script, implementation must
choose one of:

- introduce a small frontend build pipeline that produces static assets shipped
  inside the Python package; or
- vendor a prebuilt editor bundle with license/source documentation similar to
  `marked.min.js`.

### 4. Safety and validation

- Keep loopback-only serving.
- Do not add arbitrary path inputs. Artifact and sidecar names must come from
  bounded registries.
- Validate request bodies before mutation. For raw YAML sidecars, parse and
  validate the expected bounded shape before replacing content.
- Filesystem writes use a temp-file plus atomic replace pattern for single-file
  updates. Multi-file operations prevalidate all proposed changes before the
  first write and share as much write machinery with CLI operations as possible.
- Re-run taxonomy/capability checks after relevant writes. Writes that would
  create unresolved taxonomy/capability references should be rejected before
  persistence where that validation can be computed from the proposed value.
  Whole-ledger check failures discovered after a successful local write are
  surfaced as warnings with a repair path, not hidden.
- For work lifecycle transitions, call the same store operations and preserve
  blocker/DoD semantics.
- Preserve CSP and avoid inline scripts. If the editor requires additional CSP
  allowances, document the specific reason and keep them narrow.
- Route static assets recursively enough to serve the chosen editor bundle; keep
  package-data coverage in sync with the emitted asset tree.

## Acceptance criteria

- Users can create Work, Taxonomy, and Capability objects in the local web app.
- Users can edit existing Work, Taxonomy, and Capability objects in the local
  web app, including Markdown bodies/artifacts and metadata fields.
- Markdown lifecycle files use a rich Markdown editing experience and are stored
  as Markdown.
- Write endpoints mutate stores through abstract interfaces, not direct `docs/`
  path manipulation in `tcw/serve`.
- Multi-field writes are prevalidated and fail without partial persistence on
  validation errors.
- Stale writes are rejected with `409` via revision-token checks.
- Encoded refs containing `/` and `#` work for taxonomy and capability routes.
- Bounded artifact/sidecar registries are enforced in store tests and API tests.
- CLI commands and web routes share the new abstract write semantics where their
  operations overlap.
- Oversized request bodies are rejected deterministically.
- Existing read-only browse behavior remains intact.
- Validation failures are displayed in the UI and do not leave partial writes.
- `python -m pytest` passes, including API tests for create/update routes and
  store-level tests for the new abstract operations.

## Risks and decisions

- **Frontend dependency shape:** MDX Editor likely means React and a build step.
  This is acceptable only if the built static assets are shipped recursively
  with TCW, static routing serves them from the installed package, license/source
  notes are recorded, and `tcw serve` works without npm or a CDN at runtime.
- **YAML editing:** raw YAML can expose invalid states. Prefer structured
  metadata forms for known fields and use raw YAML only for bounded sidecars or
  advanced metadata where the validation story is clear.
- **Abstraction creep:** an operation like "edit this path" fails the litmus
  test. The abstract operation is "update artifact named `spec` for item X" or
  "set taxonomy field `relatesTo` for term Y".
- **Concurrent local edits:** concurrent CLI/editor changes can race with the
  browser. This work requires cheap revision tokens for editable payloads and
  stale-write rejection, not silent last-write-wins.

## Documentation-sync triggers expected to fire

- `README.md` [Public-API] - new interactive `tcw serve` behavior.
- `docs/release-notes/upcoming.md` [Public-API] - user-facing editing/create
  note.
- `docs/changelogs/upcoming.md` [Any-Code-Change] - API, store, and frontend
  changes with commit ranges.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] - web-created/edited work
  items and lifecycle artifact write surface.
- `skills/tcw-capabilities/SKILL.md` [Skill-Driven-Component] - capability
  create/edit through the web app if the capability workflow changes.
- `skills/tcw-taxonomy/SKILL.md` [Skill-Driven-Component] - taxonomy create/edit
  through the web app if the taxonomy workflow changes.
- Capability flip: `web/editing#edit-tcw-content-in-a-local-web-app` to
  `Supported` at completion.
