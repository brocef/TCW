## Changed

- `tcw serve` is one Python process (TCW-77). `tcw/serve/` is rewritten:
  `server.py` (a `ThreadingHTTPServer` that serves the packaged client from
  `tcw/serve/dist/client` with a fallback to `index.html`, and the JSON API),
  `work.py` (the work routes), `files.py` (an item's files and its
  declaration), `records.py` (taxonomy and capabilities) and `services.py`
  (the operations the routes call, replaceable in tests). The only processes
  it starts are `git rev-parse` and `git --no-optional-locks status` reads.
- Every request, reads included, must name a loopback address in `Host` and,
  when sent, in `Origin`; writes must be JSON of at most 1 MiB. Every answer
  carries `Content-Security-Policy: default-src 'self'`. Errors are
  `{"error", "code"}` mapped from `tcw/errors.py`'s classes, with no
  traceback.
- The API serves one project. `GET /api/project` gives the stage table, the
  record owner (`local` or `backend`), tags, scales, people and the user.
  `GET /api/work` takes `all` and `tag`, as `tcw work list` does, and
  falls back to the item folders on disk (`fallback: true`) when the backend
  cannot be read. Item routes are keyed by folder.
- Files: `GET`/`PUT /api/work/<folder>/files/<path>` with a SHA-256 revision
  (409 `stale-revision` on a mismatch; `null` creates), `POST …/files` for
  where a new document, round or handoff goes and its starting text, and
  `GET`/`PUT …/declaration` for `capabilities.yaml` as six lists. Saves return
  the offline validation findings as `warnings`.
- `PATCH /api/work/<folder>` sends `{changes, expected}` and answers 409 when
  a changed property no longer holds the expected value. `POST …/comments`,
  `POST …/blocks` (one target per request), `POST /api/work` (in this project,
  at the inbox stage, or delegated to a connected one), `GET /api/tickets` and
  `POST /api/tickets/<key>/adopt` call the same operations as the CLI. In Jira
  mode the item record, request and comments are read-only (403).
- `GET /api/options/assignee` and `GET /api/options/work` give suggestions the
  client cannot compute: Jira's assignable users, and items of connected
  filesystem-mode projects found on this machine.
- Taxonomy and capability edits refuse an inherited entry (403) and a
  capability subject that is not a vocabulary entry (400).
- The client is rewritten for the 3.0 work model: stage tabs from the stage
  table, rounds and verdicts, handoffs, the declaration form, properties,
  comments, the new-item form, the Tickets view, and reference fields that
  refuse, warn on or allow a value that is not a suggestion. The Markdown
  editor completes `tcw://` links.
- `layout.item_folders()` lists the item folders under the work path without
  reading them.

## Removed

- Node.js and Fastify from `tcw serve`: `web/server/`, the packaged
  `server.cjs`, `tcw/serve/runtime.py`, the API sidecar and its token.
- Aggregation of child projects' boards, the start, complete, drop and recover
  routes and dialogs, the Definition-of-Done checklist, interrupted claims,
  git commits from the viewer, plan-stage documents and sidecars, `initiative`,
  and the `Planning doc` and `Tracker` capability form fields.
- `tests/test_serve.py`, `test_serve_write.py`, `test_serve_resolve.py`,
  `test_serve_runtime.py` and the serve cases of `test_upstream_projects.py`,
  replaced by `tests/serve/`.

## Added

- `tests/serve/`: the server's tests, a recording memory backend for Jira
  mode, `jira_launcher.py` (a Jira-mode project served against TCW-71's fake
  Jira, for the browser tests), and guards that no string in `tcw/serve/` or
  the client names a stage and no string in `tcw/serve/` says "node".
- `web/e2e/jira.spec.ts`; `web/e2e/parity.spec.ts` rewritten for 3.0.
- `tests/test_static_guards.py` and `tests/test_no_node.py` now read
  `tcw/serve/`.
