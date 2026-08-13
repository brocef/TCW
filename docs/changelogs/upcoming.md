# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`intake` work artifact.** Appended to `WORK_ARTIFACTS`; readable and writable
  through the existing `read_artifact` / `write_artifact` surface, which is
  already bounded by that registry.
- **`intake` argument on `WorkStore.create` and `create_work`.** Explicitly
  separate from `body`, so an adapter can tell raw input from a request rather
  than inferring it from one overloaded field. Written only when non-empty.
- **`WorkDetail.promoted`.** True when the write that produced the detail created
  the item's `initial-request.md` where it had none. `serve`'s
  `PATCH /api/work/<slug>` surfaces it as `"promoted"`.
- **Board letter `i`** for `intake.md`, rendered ahead of `R`.

## Changed

- **`create_work` writes only the artifacts it was given.** With no `body` and no
  `intake`, an item is created with `state.yaml` alone.
- **`tcw work new` pipes stdin into `intake`** rather than `body`.
- **`inbox_accept` writes `intake.md`.** The resource manifest (including its
  `— accepted from` suffix), the attachment copying, the binary-primary fallback
  prose, and the temp-dir/`os.replace` atomicity are unchanged; the manifest entry
  for the primary resource is now named `intake.md`.
- **One presence rule.** `FsWorkStore._present` (exists and non-empty after
  `strip()`) is shared by `_read_item`, `body_path`, `artifacts()`, and the core
  revision. `_read_item` previously accepted mere existence, `artifacts()`
  required content, and `get_detail` spelled it a third way.
- **Body reads fall back** `initial-request.md` → `intake.md` → `""`. Body
  **writes** never do: `update_work(body=…)` always targets
  `initial-request.md`.
- **`body_path` returns `None`** for an item with neither artifact present, and
  resolves through the fallback otherwise. It now reads file contents, and
  tolerates a file vanishing mid-read rather than raising.
- **Core revision hashes the resolved artifact name** alongside state and body
  text, so promoting an intake to a request with identical text changes the
  token. Every existing item's core revision changes on first read after upgrade;
  the token is compared within a session and never persisted.
- **The web app's Initial Request tab gates on the artifact, not the body.**
  `WorkDocumentTabs` reads `initial-request`'s `present` flag from the
  `artifacts` prop; absent, it renders the same not-yet-present notice the Spec
  and Plan tabs use. `item.body`'s intake fallback was rendering raw intake
  under the request's label.
- **The web core editor seeds `body` from the request only.** `enterCore` opens
  an empty body when `initial-request` is absent, so saving cannot copy the
  intake into the request that replaces it.
- **`app.tsx` reads the PATCH response's `promoted`** and reports
  "Saved — Initial Request created". The field shipped unread.
- **Board letters render in lifecycle order** from the renderer's own table
  rather than in `WORK_ARTIFACTS` order, which is append-only and therefore
  cannot express lifecycle position.

## Removed

- **Both hardcoded request templates.** `create_work`'s three-heading skeleton and
  `inbox_accept`'s `TBD`-seeded variant of the same skeleton — two copies in one
  file that disagreed with each other. Nothing synthesizes a request document.

## Internal

- Six existing tests depended on the creation template for a file to read, hash,
  fail a write on, or produce a merge conflict on; each now creates the file it
  needs explicitly. Piped stdin into `tcw work new` had no test at all before.
