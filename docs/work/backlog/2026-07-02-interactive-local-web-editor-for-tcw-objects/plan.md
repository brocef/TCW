# Plan - Interactive local web editor for TCW objects

Execute in order. Phases 2 and 3 can overlap only after Phase 1 settles the
store contracts and editor packaging boundary.

## Phase 1 - Store contracts and validation shape

Touch points: `tcw/store/base.py`, `tcw/store/fs.py`, tests.

1. Prototype the MDX Editor packaging boundary before committing to the
   frontend approach. Confirm whether a build pipeline or vendored bundle can
   work with installed-package static assets and CSP; choose a fallback editor
   if not.
2. Define bounded edit surfaces in the abstract stores:
   - work body, lifecycle artifacts, allowed fields, and bounded sidecars;
   - taxonomy description and metadata fields;
   - capability body and metadata fields.
3. Define store-owned registries for bounded resources:
   - existing `WORK_ARTIFACTS`;
   - a new work sidecar registry, starting with `capabilities.yaml`;
   - capability metadata fields/statuses;
   - taxonomy editable fields.
4. Define revision-token support for editable payloads. Use a cheap
   adapter-owned token, preferably a content hash; expose it abstractly as an
   opaque string. The token changes after every successful write and after any
   external filesystem edit that changes the underlying content. Read/detail
   operations for editable objects must return revision tokens for the
   fields/bodies/artifacts they expose.
5. Define composite work create/update operations that cover title, body,
   priority, effort, complexity, blockers, parent, and initiative with full
   prevalidation before persistence. Store update semantics are partial merge:
   omitted keys are unchanged, `null` clears only nullable fields, and empty
   strings are explicit values.
6. Define lifecycle action support through semantic operations only: `start`
   and `complete`. Keep browser worktree creation/merge handling out of scope.
   Dropping a work item remains a resource deletion mapped to `WorkStore.drop`.
7. Define capability creation semantics for both new files and adding a
   capability heading to an existing capability file through a portable abstract
   operation. The API/UI must require an explicit target mode (`newFile` or
   `existingFile`) rather than inferring placement heuristically.
8. Define validation ownership: the HTTP layer checks request shape, while store
   methods enforce field allowlists, sidecar schemas, taxonomy/capability refs,
   stale revision tokens, and no-write-on-validation-failure.
9. Extend filesystem adapters to implement those operations against the current
   Markdown/YAML layout. Use temp-file plus atomic replace for single-file
   writes; prevalidate all files before any multi-file write. Propagate
   permission/disk/replace failures clearly and clean up temp files on failure
   where the OS allows it.
10. Refactor overlapping CLI write paths to use the new abstract store methods
   or shared helpers so web and CLI validation semantics do not diverge. Preserve
   existing CLI output and behavior unless the spec explicitly changes it.
11. Keep direct path logic out of `tcw/serve`. The server receives object refs,
   field names, artifact names, and sidecar names only.
12. Add unit tests for each new abstract operation, including invalid refs,
   invalid fields, invalid artifact/sidecar names, stale revision tokens, adding
   a capability to an existing file, lifecycle action guardrails, and YAML
   parse/validation failures. Assert failed validation leaves the store
   unchanged.
13. Add filesystem fault-injection tests around temp-file/atomic-replace failure
   paths, including permission/write/replace failures, and assert previous file
   content remains readable and uncorrupted.

## Phase 2 - Write API

Touch points: `tcw/serve/__init__.py`, tests.

1. Add bounded JSON request parsing with an explicit maximum body size and
   reusable response helpers for 400, 404, stale revision 409,
   semantic validation 422, oversized payload, and 500-class I/O failures.
   Enforce `Content-Length` before full body read/JSON parsing where possible;
   define malformed or missing length behavior in tests.
2. Add shared route parsing helpers that decode path parameters exactly once and
   support single-segment RFC 3986 percent-encoded refs containing `/` and `#`.
3. Match specific subresource routes before existing catch-all work-detail
   routes.
4. Add revision-bearing read/detail payloads for editable work, taxonomy, and
   capability objects before adding update routes.
5. Add resource-oriented create/update routes for work, taxonomy, and
   capabilities.
6. Add artifact and sidecar read/write routes for bounded work-item files using
   JSON envelopes with `name`, `content`, `mediaType`, and `revision`.
7. Use object update envelopes with `revision`, `fields`, and optional `body`;
   document omitted, `null`, and empty-string behavior in route tests.
8. Add lifecycle action routes for work start/complete. Preserve blocker, DoD,
   legal-transition, and force semantics from the store layer. Implement drop as
   `DELETE /api/work/<slug>` mapped to `WorkStore.drop`.
9. Add a sidecar discovery response for work detail or a dedicated endpoint so
   the UI can learn which bounded sidecars are editable and which media type and
   revision token each one has.
10. Ensure every route opens fresh stores from the startup node root captured at
   server startup, as the read-only server does today.
11. Define retry/idempotency behavior: `PATCH`/`PUT` are safe to retry only with
   the same revision token, stale retries return 409, and `POST` create routes
   fail on slug/file collisions rather than creating duplicates.
12. Add API tests using a seeded `tmp_path` node:
   - read work/taxonomy/capability detail payloads with revision tokens;
   - create and update work item fields/body/artifacts;
   - reject partial multi-field writes and verify no intermediate persistence;
   - reject stale artifact/object saves with 409;
   - reject oversized bodies via the HTTP read path before full parsing and
     before store mutation;
   - create and update taxonomy Vocabulary and Feature entries;
   - create and update capabilities metadata/body, including adding a capability
     to an existing file;
   - reject computably bad taxonomy/capability refs before persistence and
     surface whole-ledger check failures as warnings/repair messages when they
     cannot be precomputed;
   - parse encoded refs such as `store/adapter` and
     `web/editing#edit-tcw-content-in-a-local-web-app`;
   - run work lifecycle actions and resource drop through the API and assert
     guarded failure behavior;
   - retry stale `PUT`/`PATCH` requests and duplicate `POST` creates without
     duplicate writes;
   - reject unknown refs, unknown fields, invalid statuses, invalid taxonomy
     feature refs, invalid artifact names, and malformed YAML/JSON.

## Phase 3 - Frontend editor architecture

Touch points: `tcw/serve/static/`, package-data config, possibly new frontend
source/build files.

1. Implement the chosen MDX Editor packaging approach from Phase 1:
   - small build pipeline that emits package-data static assets; or
   - vendored prebuilt bundle with source/version/license documentation.
2. Update package-data and static routing for recursive bundled assets if the
   editor build emits nested or hashed files.
3. Keep installed-package runtime dependency-free from npm/CDN.
4. Define the CSP policy for the chosen editor before wiring the UI. Avoid
   `unsafe-inline` where possible; document and test any unavoidable relaxation,
   including `blob:` or style allowances.
5. Add editor states:
   - selected item view mode;
   - edit mode;
   - create mode;
   - dirty state;
   - save in progress;
   - validation errors.
6. Use structured controls for known metadata and rich Markdown editing for
   Markdown bodies/artifacts.
7. Carry revision tokens in editor state and send them with every save. On 409,
   keep the user's unsaved text in memory, show the current server version, and
   offer refresh/discard and manual copy/merge actions. Do not force-reload and
   lose local edits.
8. Warn or block on browser close, hard refresh, and tab/view switches when
   edits are dirty: use `beforeunload` for browser close/refresh and app-level
   guards for tab/view switches.
9. Add browser-level smoke or automated frontend tests for create/edit save,
   cancel, validation error rendering, stale-write recovery, and dirty
   navigation warnings.

## Phase 4 - Axis-specific UI flows

Touch points: `tcw/serve/static/app.js`, `style.css`, tests where practical.

1. Work:
   - create item form with title, priority, effort, complexity, blockers,
     parent, initiative, and body;
   - edit existing fields and body;
   - edit lifecycle artifacts with the Markdown editor;
   - edit bounded sidecars such as `capabilities.yaml`;
   - expose start/complete/drop actions only where legal. Use a confirmation
     modal for complete/drop; complete must require explicit DoD acknowledgments
     and show blocker/illegal-transition errors inline.
2. Taxonomy:
   - create Vocabulary or Feature entries;
   - edit name, description, kind where legal, `relatesTo`, and Feature
     vocabulary refs;
   - surface taxonomy check failures.
3. Capabilities:
   - create capability entries;
   - support adding a capability to an existing capability file when requested;
   - edit metadata through known fields;
   - edit body through the Markdown editor;
   - surface capabilities check failures.

## Phase 5 - Verification and docs

1. Run `python -m pytest`.
2. Run `tcw taxonomy check` and `tcw capabilities check`.
3. Smoke-test `tcw serve --no-open --port 8765` and write routes with `curl` or
   a browser.
4. Verify installed package static assets if a frontend build/vendor step is
   added, including nested/hashed editor assets.
5. Check `tcw/serve` for accidental direct `docs/` path access.
6. Verify route parsing with encoded `/` and `#` refs.
7. Verify stale writes are rejected for at least one object update and one
   artifact/sidecar update.
8. Verify validation failures leave the backing files unchanged.
9. Verify oversized request bodies are rejected before full body parsing and
   document the configured limit in the public/API docs.
10. Verify taxonomy/capability check behavior for both pre-rejected bad refs and
   post-write whole-ledger warnings.
11. Run the frontend/browser verification from Phase 3 for editor save/cancel,
   validation display, stale-write recovery, and dirty navigation warnings.
12. Add a concurrent modification test that reads an editable payload, changes
   the same object through the CLI/store, then verifies the stale web save gets
   409 and preserves the user's draft.
13. Verify temp-file cleanup and prior-content preservation after injected write
   failures.
14. Verify CLI commands that overlap with web writes still pass their existing
   tests after the shared-store refactor.
15. Update:
   - `README.md`;
   - `docs/release-notes/upcoming.md`;
   - `docs/changelogs/upcoming.md`;
   - `skills/tcw-work/SKILL.md`;
   - `skills/tcw-capabilities/SKILL.md` if capability workflow changes;
   - `skills/tcw-taxonomy/SKILL.md` if taxonomy workflow changes.
16. Run the documentation-sync skill before reporting completion.
17. Flip `web/editing#edit-tcw-content-in-a-local-web-app` to `Supported`.

## Notes for the implementer

- Run `tcw work start 2026-07-02-interactive-local-web-editor-for-tcw-objects`
  before the first code edit.
- Commit the start transition before implementation changes.
- Do not complete the item until the user has verified the result.
