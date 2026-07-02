# Spec — Local read-only web viewer (`tcw serve`)

## Capability changes

- **New:** `web#browse-tcw-content-in-a-local-web-app` (currently `Missing`).
  A user runs `tcw serve` and browses the Work board, Taxonomy tree, and
  Capabilities ledger read-only in a localhost web UI. Flips to `Supported` at
  completion. No existing capability changes — this is an additional
  presentation surface, not a change to `work#view-the-board`,
  `taxonomy#browse-the-term-forest`, or `capabilities#browse-capabilities-by-status`.

## Problem

TCW content is only reachable through the `tcw` CLI. People who don't live in
the terminal (or who just want to skim a board and read an item's request) have
no low-friction way to look at it. We want a simple local web view — without
compromising the storage-abstraction that lets TCW run against a non-filesystem
backend later.

## Goals

- `tcw serve` → localhost server rendering **Work / Taxonomy / Capabilities**,
  read-only.
- Architecture that makes **full interaction a later additive step, not a
  rewrite**: a JSON API over the store is the stable contract; reads wire GET,
  writes later add POST/PATCH calling the same store methods the CLI uses.
- Stay a **one-runtime-dependency** project (PyYAML). No web framework, no build
  step, no new Python dependency.
- **Litmus-clean:** the web layer calls only store-interface methods and
  serializes dataclasses; a future `JiraWorkStore` could back the identical UI.

## Non-goals (v1)

- In-browser editing or lifecycle transitions (the "open in editor" link stands
  in for editing).
- Inline rendering of `spec.md`/`plan.md`/`outcome.md`/`refined-outcome.md`
  (links only).
- Authentication / non-local binding / multi-user concerns.
- A frontend framework or bundler.

## Constraints

- Bind **127.0.0.1 only**.
- No `docs/` access from the web layer — everything through the store interface.
- Markdown rendering: one **vendored** `marked.min.js` (checked into the package;
  no CDN fetch at runtime, no npm, no Python markdown dep).

## Current-state findings

- **Subcommand wiring** (`tcw/cli.py`): `build_parser()` adds subparsers; the
  three component modules register via `add_subparser(sub)`. `serve` is a single
  command (not a group), so it registers its own parser directly in
  `build_parser()` with `set_defaults(func=…)` — it does **not** need the
  `NAME/SUBCOMMANDS/DEFAULT_SUBCOMMAND` protocol (those drive `_normalize`'s
  `show`-shorthand, irrelevant to `serve`).
- **Store surface already abstract & serializable:**
  `WorkStore.board()/get()`, `TaxonomyStore.list()`, `CapabilitiesStore.list()`
  return dataclasses (`WorkItem`, `Term`, `Capability`) → `dataclasses.asdict`
  is the JSON.
- **Body surface:** `WorkItem.body` maps to `initial-request.md`
  (`FsWorkStore.body_path`, `tcw/store/fs.py:910`). `Term` already carries a
  bounded `attachments` list; `Capability` carries `body`.
- **Artifact gap (the one real design point):** the lifecycle artifacts
  (`spec/plan/outcome/refined-outcome`) are **not** on the store interface. The
  board enumerates them in the CLI via a filesystem read — `stages()` in
  `tcw/work/cli.py:203` calls `st.path(slug)` (a Path leak) and probes hardcoded
  filenames. This is a bounded, *named* set (R/S/P/O/F), not open globbing.

## Proposed behavior

### 1. `tcw serve` command
`tcw serve [--port N] [--host 127.0.0.1] [--no-open]`. Starts a
`ThreadingHTTPServer` on 127.0.0.1; unless `--no-open`, opens the browser
(`webbrowser.open`). Ctrl-C stops it. Resolves the TCW node the same way the CLI
does (nearest `tcw-config.yaml`); errors with the standard "no tcw node here"
message if absent.

### 2. Consolidated artifact surface (store change)
Add to `WorkStore` (ABC) an abstract enumeration of an item's lifecycle
artifacts, e.g.:

```
@dataclass
class Artifact:
    name: str        # "initial-request" | "spec" | "plan" | "outcome" | "refined-outcome"
    present: bool     # has non-empty content
    locator: str | None  # opaque handle the store can "open"; FS → file path

def artifacts(self, slug: str) -> list[Artifact]: ...
def open_artifact(self, slug: str, name: str) -> None: ...   # reveal via the adapter
```

- `FsWorkStore.artifacts` realizes the bounded R/S/P/O/F set by reading the item
  folder (the coupling now lives *in the adapter*, not the CLI). The `locator` is
  **derived from the resolved item folder + a fixed artifact name** — client
  input is never joined into a path (see Risks: traversal).
- `FsWorkStore.open_artifact` hands the file to the platform **GUI** opener
  (`open` / `xdg-open` / `os.startfile`) via a **detached, non-blocking**
  `subprocess.Popen`. Deliberately **not** `$VISUAL`/`$EDITOR`: a TTY editor
  (e.g. `vim`) launched from a server thread with no controlling terminal would
  hang that handler thread indefinitely. The GUI opener returns immediately and
  lets the desktop pick the user's default app for `.md` (review finding).
- The board's `stages()` is refactored to call `st.artifacts(slug)` — **board
  output is unchanged** (a regression check pins this).

### 3. HTTP surface (the write-ready contract)
Read-only endpoints for v1:

| Method | Path | Store call |
|---|---|---|
| GET | `/` | static `index.html` (+ `app.js`, `style.css`, `marked.min.js`) |
| GET | `/api/work` | `board()` (all statuses) |
| GET | `/api/work/<slug>` | `get()` + `artifacts()` |
| GET | `/api/taxonomy` | `TaxonomyStore.list()` |
| GET | `/api/capabilities` | `CapabilitiesStore.list()` |
| POST | `/api/work/<slug>/open?artifact=<name>` | `open_artifact()` → 204 |

Store instances are constructed **per request** (always fresh — reflects
concurrent CLI/agent edits; no cache-invalidation logic). JSON via
`dataclasses.asdict`. Later writes add `POST /api/work`, `PATCH /api/work/<slug>`
against `create`/`set_field`/`start`/`complete` — additive, same handler.

### 4. Frontend
One static page: three tabs (Work / Taxonomy / Capabilities), list → detail.
Vanilla JS `fetch`. Work detail shows item fields + inline-rendered
`initial-request` (via `marked`) + a link row for each **present** artifact;
clicking a link POSTs `…/open`. No SPA framework.

## Acceptance criteria

- `tcw serve` serves the three axes read-only on 127.0.0.1 and opens a browser
  (suppressible with `--no-open`).
- Work detail inline-renders `initial-request`; spec/plan/outcome/refined-outcome
  appear as links that open the file in the user's editor via the local endpoint.
- The web layer contains **no** `docs/` path access — only store calls +
  `dataclasses.asdict`.
- `tcw work list` board output is byte-identical before/after the `stages()`
  refactor.
- `python -m pytest` green, including new backend tests (endpoints + `artifacts`
  + open-endpoint input validation) and the board-parity regression test.
- No new entry in `pyproject.toml` `dependencies`.

## Risks / dependencies

- **Editor-launch is local-only:** browsers can't launch an editor from an
  `http://` page, so it must be a server endpoint. Realization is FS-specific
  (a remote store would return a URL to open) — kept behind `open_artifact`.
- **Trust boundary (traversal / injection):** the open endpoint takes `slug` +
  `artifact` from the client. Traversal is structurally prevented, not merely
  filtered: `slug` resolves through `FsWorkStore._find`, which **matches a slug
  against the names of enumerated item directories** (`_item_dirs()`), so a value
  like `../../etc` matches no item and returns 404 — it is never path-joined.
  `artifact` must be a member of the fixed `WORK_ARTIFACTS` tuple (else 400). The
  opener receives a path *derived from the resolved item folder + the fixed
  name*, and is invoked with an **argument vector** (`Popen([opener, path])`, no
  shell), so neither value can inject a command. (Review finding — both local
  models flagged the endpoint; the safety holds but the spec now states the
  mechanism.)
- **Concurrency (CLI edits during a GET):** the server and a `tcw work` command
  can run at once; a transition (`git mv`) mid-read could make one request see a
  transient state. Accepted degradation for a single-user local tool: each
  request is wrapped so an exception yields a **500 for that request only** — the
  `ThreadingHTTPServer` keeps serving, and a browser refresh recovers. No locking
  is built (`ponytail`: the failure mode is a refresh, not data loss).
- **Vendored `marked.min.js`:** license (MIT) + a note on how it was vendored,
  so it's auditable and updatable.
- No dependency on other open work items.

## Open questions & decisions to finalize

Surfaced by the dual review (bllm-review-many: qwen25 + gemma4). All resolved.

**Decided by the user:**

- **Default port** → `8765`, overridable with `--port`.
- **GUI-opener-only for artifacts** → accepted. `$EDITOR`/`$VISUAL` dropped (a TTY
  editor launched from a server thread hangs it); artifacts open in the desktop's
  default GUI app (`open`/`xdg-open`/`os.startfile`). A terminal-editor user won't
  get *their* editor from the web link — accepted trade-off.

**Resolved with a default (during review):**

- **Per-request store construction** — kept (always fresh, no cache/invalidation
  logic). Ceiling: an `rglob` per request; negligible for local boards of
  dozens–hundreds of items. Revisit only if it measurably drags.
- **Opener-failure status** → `500` (was `502`; `502` is for upstream proxies).
- **Concurrency** — no locking; a mid-edit request degrades to a 500 + refresh
  (see Risks).
- **`marked.min.js`** — vendored into the package (no runtime CDN fetch), with a
  `VENDOR.md` recording source + version + MIT license.

## Documentation-sync triggers expected to fire

- `README.md` [Public-API] — new `tcw serve` command + quickstart.
- `docs/release-notes/upcoming.md` [Public-API] — user-facing note.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Added/Changed entries.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — the new `artifacts()`
  store surface changes the work component's model/CLI-adjacent behavior; note
  `serve` and the artifact surface if the skill references board `stages`.
- Capability flip: `web#browse-tcw-content-in-a-local-web-app` → `Supported`.
