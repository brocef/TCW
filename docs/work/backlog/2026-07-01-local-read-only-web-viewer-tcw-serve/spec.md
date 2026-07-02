# Spec — Local read-only web viewer (`tcw serve`)

## Capability changes

- **New:** `web#browse-tcw-content-in-a-local-web-app` (currently `Missing`).
  A user runs `tcw serve` and browses the Work board, Taxonomy tree, and
  Capabilities ledger read-only in a localhost web UI. Flips to `Supported` at
  completion. `Subject: cli` (loose pointer); **no `Feature`** — the taxonomy has
  no Feature that fits and one wasn't invented (gate consciously run). No existing
  capability changes — this is an additional presentation surface, not a change
  to `work#view-the-board`, `taxonomy#browse-the-term-forest`, or
  `capabilities#browse-capabilities-by-status`.

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
- **Litmus-clean:** the web layer discovers nothing by path — every datum and
  every openable handle comes from a store-interface call; a future
  `JiraWorkStore` could back the identical UI.

## Non-goals (v1)

- In-browser editing or lifecycle transitions (the "open in editor" link stands
  in for editing).
- Inline rendering of `spec.md`/`plan.md`/`outcome.md`/`refined-outcome.md`
  (links only).
- Authentication / non-local binding / multi-user concerns.
- A frontend framework or bundler.

## Constraints

- Bind **127.0.0.1 only** (no `--host` flag — see Risks/S4).
- The web layer calls only store-interface methods; it never globs `docs/` nor
  constructs store paths itself.
- Markdown rendering: one **vendored** `marked.min.js` (checked into the package;
  no CDN fetch at runtime, no npm, no Python markdown dep).

## Current-state findings

- **Subcommand wiring** (`tcw/cli.py`): `build_parser()` adds subparsers; the
  three component modules register via `add_subparser(sub)`. `serve` is a single
  command (not a group), so it registers its own parser directly in
  `build_parser()` with `set_defaults(func=…)` — it does **not** need the
  `NAME/SUBCOMMANDS/DEFAULT_SUBCOMMAND` protocol.
- **Node resolution:** `find_node_root()` (`tcw/store/fs.py:64`) locates the
  nearest `tcw-config.yaml` sentinel. The component CLIs' `_store()` helpers
  (e.g. `tcw/work/cli.py:35`) are print-on-failure + single-component — **not**
  reused by the server (see S3); the server resolves the node once at startup.
- **Store surface already abstract & serializable:**
  `WorkStore.board()/get()`, `TaxonomyStore.list()`, `CapabilitiesStore.list()`
  return dataclasses (`WorkItem`, `Term`, `Capability`) → `dataclasses.asdict`.
- **Body surface:** `WorkItem.body` maps to `initial-request.md`
  (`FsWorkStore.body_path`, `tcw/store/fs.py:910`). `Term` carries a bounded
  `attachments` list; `Capability` carries `body`.
- **Artifact gap (the one real design point):** the lifecycle artifacts
  (`spec/plan/outcome/refined-outcome`) are **not** on the store interface. The
  board enumerates them in the CLI via a filesystem read — `stages()`
  (`tcw/work/cli.py:203`) calls `st.path(slug)` (a Path leak) and probes hardcoded
  filenames, counting a file present only when `read_text().strip()` is truthy.
  This is a bounded, *named* set (R/S/P/O/F), not open globbing.

## Proposed behavior

### 1. `tcw serve` command
`tcw serve [--port N] [--no-open]`. Binds a `ThreadingHTTPServer` to
**127.0.0.1 only** (no `--host` — loopback is a security constraint, not a
default). Unless `--no-open`, opens the browser **after the socket binds** (not
after `serve_forever`). Ctrl-C stops it cleanly; a port already in use yields a
clean message, not a traceback. Resolves the TCW node **once at startup** via
`find_node_root()`; fails fast with the standard "no tcw node here" message and a
non-zero exit if absent.

### 2. Consolidated artifact surface (store change) — litmus-clean

The abstract surface returns **data, never a local side effect** (fix B1). Add
to `WorkStore` (ABC):

```
WORK_ARTIFACTS = ("initial-request", "spec", "plan", "outcome", "refined-outcome")

@dataclass
class Artifact:
    name: str        # a WORK_ARTIFACTS member
    present: bool     # has non-empty (stripped) content

def artifacts(self, slug: str) -> list[Artifact]: ...
def artifact_locator(self, slug: str, name: str) -> str | None: ...
```

- `artifacts()` returns **name + present only** — no filesystem path in the
  serialized payload (fix S1). `present` mirrors `stages()` exactly:
  `read_text().strip()` truthy (fix N1 — a whitespace-only file is *absent*).
- `artifact_locator()` returns an **openable handle**: `FsWorkStore` → the
  local file path (or `file://…`); a future `JiraWorkStore` → an `https://` URL.
  This is a resolvable *reference* — the abstract vocabulary — so it is
  backend-implementable, unlike a `-> None` "launch it" side effect.
- **The GUI launch is NOT a store method.** It lives in the serve layer: given a
  handle from `artifact_locator`, a local path → `subprocess.Popen([opener,
  path])` (non-blocking, argv form, no shell); an `http(s)` handle → returned to
  the browser to `window.open`. For v1 (FS only) it's always the local branch.
  `Popen`/`FileNotFoundError` (opener binary absent) are caught → 500, never a
  crash.
- The board's `stages()` is refactored to call `st.artifacts(slug)` and derive
  the R/S/P/O/F letters (the name→letter mapping + order stay in the CLI
  presentation layer). **Board output is byte-identical** (a regression check
  pins this, incl. whitespace-only / missing / all-present fixtures).

### 3. HTTP surface (the write-ready contract)
Read-only endpoints for v1:

| Method | Path | Store call |
|---|---|---|
| GET | `/` | static `index.html` (+ `app.js`, `style.css`, `marked.min.js`) |
| GET | `/api/work` | `board()` (all statuses) |
| GET | `/api/work/<slug>` | `get()` + `artifacts()` (name+present, **no path**) |
| GET | `/api/taxonomy` | `TaxonomyStore.list()` |
| GET | `/api/capabilities` | `CapabilitiesStore.list()` |
| POST | `/api/work/<slug>/artifacts/<name>/open` | `artifact_locator()` → launch → 204 |

- Node resolved **once at startup**; **fresh store instances per request** from
  the node root (always reflects concurrent CLI/agent edits; no cache). If a
  component dir is absent (partial node), that endpoint returns empty/404 rather
  than crashing (fix S3).
- JSON via `dataclasses.asdict`, dumped `json.dumps(…, default=str)` so an opaque
  `WorkItem.capabilities` blob / any stray non-native value degrades to a string
  instead of 500-ing.
- Each request is wrapped: any unhandled exception (e.g. a concurrent `git mv`
  mid-read) → **500 for that request only**; the server keeps serving.
- `/open` validates: `slug` must resolve via the store (else 404); `name` must be
  in `WORK_ARTIFACTS` (else 400); the artifact must be **present** (else 404 — no
  launching a nonexistent file, fix N2).
- Later writes add `POST /api/work`, `PATCH /api/work/<slug>` against
  `create`/`set_field`/`start`/`complete` — additive, same handler.

### 4. Frontend
One static page: three tabs (Work / Taxonomy / Capabilities), list → detail.
Vanilla JS `fetch`, **all JS in external `app.js`** (no inline scripts). Work
detail shows item fields + `marked`-rendered `initial-request` + a link row for
each **present** artifact; a link POSTs the `/open` endpoint. The server sends
`Content-Security-Policy: default-src 'self'` (fix S5 — `marked` doesn't sanitize
HTML; CSP + external-JS is the dep-free mitigation, see Risks). No SPA framework.

## Acceptance criteria

- `tcw serve` serves the three axes read-only on 127.0.0.1 and opens a browser
  (suppressible with `--no-open`).
- Work detail inline-renders `initial-request`; spec/plan/outcome/refined-outcome
  appear as links that open the file in the desktop's default app via the local
  endpoint.
- The web layer discovers nothing by path: no `docs/` globbing, no store-path
  construction — only store calls + `dataclasses.asdict`; the serialized
  `/api/work/<slug>` payload contains **no filesystem paths**.
- `tcw work list` board output is byte-identical before/after the `stages()`
  refactor (whitespace-only / missing / all-present cases exercised).
- `python -m pytest` green: endpoints; `artifacts` present-flags; `/open` input
  validation + present-guard + no-`Popen`-on-bad-input; opener-binary-missing
  handled; board-parity regression; serialization of `blocked_by`/`capabilities`.
- No new entry in `pyproject.toml` `dependencies`; static assets ship in the
  wheel (`package-data`) and resolve via `importlib.resources` when pip-installed.

## Risks / dependencies

- **Artifact-open is a local action, kept off the abstract surface:** the ABC
  exposes `artifact_locator -> handle` (abstract, remote-backable); the GUI
  `Popen` launch lives in the serve/FS tier. A remote store returns an `https`
  handle the browser opens instead. (Subagent B1.)
- **Trust boundary (traversal / injection):** `/open` takes `slug` + `name`.
  Traversal is structurally prevented: `slug` resolves through
  `FsWorkStore._find`, which **matches against enumerated item-directory names**
  (`_item_dirs()`), so `../../etc` matches nothing → 404, never path-joined.
  `name` must be in `WORK_ARTIFACTS` → 400 otherwise. The opener is invoked with
  an **argument vector** (no shell), so neither value can inject a command.
- **Markdown XSS (S5):** `marked` renders raw HTML by default; bodies may contain
  hostile markup. Mitigation without a new dep: `Content-Security-Policy:
  default-src 'self'` + all JS external. Residual risk accepted for an own-repo,
  single-user, loopback tool (full fix would vendor DOMPurify — deferred).
- **Loopback-only (S4):** no `--host`; binding is hardcoded to 127.0.0.1 so an
  unauthenticated read API + open side-effect can't be exposed to the LAN.
- **Concurrency:** server + a `tcw work` command can run at once; a mid-read
  `git mv` degrades to a 500 + browser refresh. No locking (`ponytail`: the
  failure mode is a refresh, not data loss).
- **Packaging (S2):** `tcw/serve/` is a **package** (`__init__.py`), never a bare
  `tcw/serve.py` module (it can't coexist with `tcw/serve/static/`). Non-`.py`
  assets need explicit `[tool.setuptools.package-data]` and runtime resolution
  via `importlib.resources` — verified by a test that reads an asset from the
  installed package path.
- **Vendored `marked.min.js`:** MIT license + `VENDOR.md` recording source +
  version, so it's auditable and updatable.
- No dependency on other open work items.

## Open questions & decisions to finalize

All review findings triaged and every decision is now settled — nothing open.

**Decided by you:**

- **Markdown sanitization (S5):** dep-free mitigation only — CSP (`default-src
  'self'`) + all JS external. No DOMPurify. Residual risk accepted for a
  single-user loopback tool.
- **`/open` REST shape (N6):** path-segment form
  `POST /api/work/<slug>/artifacts/<name>/open` (consistent with future write
  endpoints).
- Default port `8765` (overridable with `--port`).
- GUI-opener-only for artifacts (no `$EDITOR`/`$VISUAL` — a TTY editor would hang
  the server thread).

**Resolved with a default during review (override if you disagree):**

- Per-request store construction (fresh each time; node resolved once at
  startup). Ceiling: an `rglob` per request; negligible for local boards.
- Opener-failure / mid-edit exception → `500`.
- Version bump at completion should be **minor** (0.8.0) — `tcw serve` is a new
  public CLI command (subagent N4). Offered at closeout, not now.

## Documentation-sync triggers expected to fire

- `README.md` [Public-API] — new `tcw serve` command + quickstart.
- `docs/release-notes/upcoming.md` [Public-API] — user-facing note.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Added/Changed entries.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — note the `artifacts()` /
  `artifact_locator()` store surface (board output itself is unchanged).
- Capability flip: `web#browse-tcw-content-in-a-local-web-app` → `Supported`.
- Version bump is human-gated via `cut_version.py` (5-file lockstep) — offer a
  **minor** at closeout.
