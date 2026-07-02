# Plan — Local read-only web viewer (`tcw serve`)

Execute top-to-bottom. Phase 1 and Phase 3 are independent (can run in
parallel); Phase 2's work-detail + `/open` endpoints depend on Phase 1.

## Phase 1 — Consolidated artifact surface (store)

**Touch points:** `tcw/store/base.py`, `tcw/store/fs.py`, `tcw/work/cli.py`,
`tests/`.

1. In `base.py`: add `WORK_ARTIFACTS = ("initial-request","spec","plan",
   "outcome","refined-outcome")`, an `Artifact` dataclass (`name`,
   `present: bool` — **no `locator` field**, fix S1), and two `WorkStore` ABC
   methods: `artifacts(slug) -> list[Artifact]` and
   `artifact_locator(slug, name) -> str | None`. `artifact_locator` returns an
   abstract openable handle (fix B1); it does **not** launch anything.
2. In `fs.py` (`FsWorkStore`): `artifacts` maps each name → `<folder>/<name>.md`,
   `present` = `p.is_file() and p.read_text(encoding="utf-8").strip()` truthy
   (identical to `stages()`, fix N1). `artifact_locator` resolves slug→item
   (unresolved → `None`), rejects a name not in `WORK_ARTIFACTS`, returns the
   file path (or `file://`) — path derived from the resolved item folder + fixed
   name, never joined from client input. **No `Popen` here** — the launch is
   serve-layer (Phase 2).
3. Refactor `tcw/work/cli.py:stages()` (≈line 203) to call `st.artifacts(slug)`
   and map `present` → R/S/P/O/F letters (mapping + order stay in the CLI).
   **No output change.**
4. **Board-parity regression test:** seed a `tmp_path` repo with items covering
   (a) a whitespace-only artifact, (b) a missing one, (c) all-present; assert
   `tcw work list` output is byte-identical before/after. Unit-test `artifacts`
   (present flags across those cases) and `artifact_locator` (unknown name →
   `None`/reject; unknown slug → `None`).

## Phase 2 — `tcw serve` backend

**Touch points:** `tcw/serve/__init__.py` (or `server.py`) — a **package**, not a
bare module (fix S2); `tcw/cli.py`; `pyproject.toml`; `tests/`.

1. `tcw/serve/`: a `ThreadingHTTPServer` + one `BaseHTTPRequestHandler`. Route
   table for the six endpoints in the spec. **Startup:** resolve the node once
   via `find_node_root()` (fail-fast + non-zero exit + standard message if
   absent, fix S3) — do **not** reuse the print-y per-request `_store()`. **Per
   request:** construct fresh `FsWorkStore`/`FsTaxonomyStore`/
   `FsCapabilitiesStore` from the node root; a missing component dir → empty/404,
   not a crash. Responses: static assets for `/` (resolved via
   `importlib.resources.files("tcw.serve") / "static"`, never CWD);
   `application/json` (`dataclasses.asdict`, `json.dumps(…, default=str)`) for
   `/api/*`; 204 for `open`. Send `Content-Security-Policy: default-src 'self'`
   (fix S5). Wrap each request → unhandled exception becomes a **500 for that
   request only**. `/open`: `artifact_locator(slug,name)` → 404 if `None` or the
   artifact isn't present (fix N2); local path → `subprocess.Popen([opener,path])`
   (`open`/`xdg-open`/`os.startfile`, argv form) with `Popen`/`FileNotFoundError`
   (opener missing) caught → 500; `http(s)` handle → JSON `{url}` for the browser.
   `serve(port, open_browser)` entry fn.
2. `tcw/cli.py`: register a `serve` subparser directly in `build_parser()`
   (`--port` default `8765`, `--no-open`; **no `--host`**, fix S4),
   `set_defaults(func=_serve)`. `_serve` binds the socket, opens the browser
   **after bind, before `serve_forever`** (pass `open_browser` into `serve()`),
   handles `KeyboardInterrupt` and `OSError` (address in use) with clean messages
   (fix N3).
3. `pyproject.toml`: add
   ```toml
   [tool.setuptools.package-data]
   "tcw.serve" = ["static/*"]
   ```
   Verify assets resolve from the **installed** package path, not CWD.

## Phase 3 — Frontend (parallel with Phase 1)

**Touch points:** `tcw/serve/static/`: `index.html`, `app.js`, `style.css`,
`marked.min.js`, `VENDOR.md`.

1. `index.html` + `style.css`: three tabs, list pane + detail pane, no framework,
   **no inline JS** (CSP-compatible).
2. `app.js`: `fetch` the `/api/*` endpoints; render lists + detail. Work detail =
   fields + `marked`-rendered `initial-request` + a link row per *present*
   artifact; a link click POSTs the `/open` endpoint, toasts on result, and (for
   a returned `{url}`) `window.open`s it.
3. Vendor `marked.min.js` (MIT); `VENDOR.md` records source URL + version.

## Phase 4 — Tests (fold into 1–3 as written)

- Backend: boot the handler against a seeded `tmp_path` TCW repo; assert
  `/api/work`, `/api/work/<slug>` (incl. `artifacts[]` with **no path field**),
  `/api/taxonomy`, `/api/capabilities` shapes.
- `/open`: unknown `name` → 400; unknown/`../../etc` slug → 404; **absent** but
  valid artifact → 404; each with **no `Popen` call** (spy the opener). A present
  artifact → 204 and one `Popen` with an argv (no shell).
- Opener-binary-missing → `FileNotFoundError` handled → 500, server stays up.
- Serialization: an item with `blocked_by` + a populated `capabilities` blob
  serializes without error.
- Partial node (only `docs/work/`, no `docs/taxonomy/`) → `/api/taxonomy` empty,
  no crash.
- Packaging: an installed-path asset read via `importlib.resources` succeeds.
- No browser automation (v1).

**Verification commands:**
- `python -m pytest`
- `tcw serve --no-open --port 8765` then `curl -s localhost:8765/api/work | python -m json.tool`
- `grep -rn "docs/" tcw/serve/` → no `docs/` path access in the web layer
- `git grep -n "dependencies" pyproject.toml` → unchanged
- `pip install .` in a temp venv → `tcw serve` finds its static assets

## Phase 5 — Documentation sync + capability flip (at completion)

- `README.md`: add `tcw serve` + a short quickstart.
- `docs/release-notes/upcoming.md`: user-facing note.
- `docs/changelogs/upcoming.md`: Added (`tcw serve`, `WorkStore.artifacts` /
  `artifact_locator`), Changed (board `stages()` via `artifacts()`), commit range.
- `skills/tcw-work/SKILL.md`: note the `artifacts()`/`artifact_locator()` surface.
- `tcw capabilities set web#browse-tcw-content-in-a-local-web-app --status Supported`.
- Run `skill-cefailures:documentation-sync`; offer a **minor** version bump
  (0.8.0 — new public CLI command) via `cut_version.py` (5-file lockstep).

## Notes for the implementer

- `tcw work start <slug>` **before** the first code edit; commit that transition
  (with committed `spec.md`/`plan.md`) as the first implementation commit.
- The litmus test is an acceptance criterion: the web layer talks only to the
  store interface; the abstract surface returns data/handles, never local
  side-effects.
