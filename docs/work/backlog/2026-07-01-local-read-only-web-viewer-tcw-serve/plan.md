# Plan — Local read-only web viewer (`tcw serve`)

Execute top-to-bottom. Phase 1 and Phase 3 are independent (can run in
parallel); Phase 2's work-detail endpoint depends on Phase 1's `artifacts()`.

## Phase 1 — Consolidated artifact surface (store)

**Touch points:** `tcw/store/base.py`, `tcw/store/fs.py`, `tcw/work/cli.py`,
`tests/`.

1. In `base.py`: add an `Artifact` dataclass (`name`, `present: bool`,
   `locator: str | None`) and two `WorkStore` methods — abstract
   `artifacts(slug) -> list[Artifact]` and `open_artifact(slug, name) -> None`.
   Define the canonical ordered name set as a module constant
   (`WORK_ARTIFACTS = ("initial-request","spec","plan","outcome","refined-outcome")`).
2. In `fs.py` (`FsWorkStore`): implement `artifacts` by mapping each name →
   `<folder>/<name>.md`, `present` = file exists and non-empty (same test
   `stages()` uses), `locator` = the file path (from the resolved item folder +
   fixed name — never joined from client input). Implement `open_artifact`:
   resolve slug→item (unresolved → raise; handler maps to 404), reject a name not
   in `WORK_ARTIFACTS` (→ 400), then launch the **GUI** opener non-blocking:
   `subprocess.Popen([opener, path])`, opener = `open` (macOS) / `xdg-open`
   (Linux) / `os.startfile` (Windows). **Not** `$EDITOR`/`$VISUAL` — a TTY editor
   would hang the server thread. Argv form (no `shell=True`) → no injection.
   Validation lives here (trust boundary).
3. Refactor `tcw/work/cli.py:stages()` (≈line 203) to call `st.artifacts(slug)`
   and derive the R/S/P/O/F letters from `present`. **No output change.**
4. **Board-parity regression test:** capture `tcw work list` output on a seeded
   `tmp_path` repo before/after — assert byte-identical. Unit-test `artifacts`
   (present flags) and `open_artifact` (rejects unknown name → error; does not
   shell out on bad input).

## Phase 2 — `tcw serve` backend

**Touch points:** `tcw/serve.py` (new), `tcw/cli.py`, `tests/`.

1. `tcw/serve.py`: a `ThreadingHTTPServer` + one `BaseHTTPRequestHandler`. Route
   table for the six endpoints in the spec. Per-request store construction
   (reuse the CLI's node-resolution helper). Responses: static files for `/` and
   assets; `application/json` (`dataclasses.asdict`, dumped with
   `json.dumps(..., default=str)` so the opaque `WorkItem.capabilities` blob /
   any `Path` degrades to a string instead of 500-ing) for `/api/*`; 204 for
   `open`. 404/400 for unknown slug/artifact; 500 + message (never a traceback)
   on opener failure. Wrap each request so any unhandled exception (e.g. a
   concurrent CLI `git mv` mid-read) becomes a **500 for that request only** —
   the server keeps running. `serve(host, port, open_browser)` entry fn.
2. `tcw/cli.py`: register a `serve` subparser directly in `build_parser()`
   (`--port` default e.g. 8765, `--host` default `127.0.0.1`, `--no-open`),
   `set_defaults(func=_serve)`; `_serve` calls `tcw.serve.serve(...)` and, unless
   `--no-open`, `webbrowser.open`. Handle `KeyboardInterrupt` cleanly.
3. Ensure static assets ship in the wheel (`[tool.setuptools.package-data]` or
   `MANIFEST`/`include-package-data`) — verify assets resolve from the installed
   package path, not CWD.

## Phase 3 — Frontend (parallel with Phase 1)

**Touch points:** `tcw/serve/static/` (new): `index.html`, `app.js`,
`style.css`, `marked.min.js`.

1. `index.html` + `style.css`: three tabs, list pane + detail pane. No framework.
2. `app.js`: `fetch` the `/api/*` endpoints; render lists and detail. Work
   detail = fields + `marked`-rendered `initial-request` + a link row per
   *present* artifact; a link click POSTs `…/open` and shows a toast on result.
3. Vendor `marked.min.js` (MIT); record source URL + version in a short header
   comment or `static/VENDOR.md` so it's auditable/updatable.

## Phase 4 — Tests (fold into 1–3 as written)

- Backend: boot the handler against a seeded `tmp_path` TCW repo; assert
  `/api/work`, `/api/work/<slug>` (incl. `artifacts[]`), `/api/taxonomy`,
  `/api/capabilities` shapes; `open` rejects unknown artifact (400) and unknown
  slug (404). No browser automation.
- **Traversal/injection:** `open` with `slug` = `../../etc` (and with a bogus
  `artifact`) → 404/400 and **no `Popen` call** (patch/spy the opener to assert
  it never fires on bad input).
- **Serialization:** an item carrying `blocked_by` and a populated
  `capabilities` blob serializes without error (guards the opaque-field risk).
- Reuse existing store test fixtures/helpers.

**Verification commands:**
- `python -m pytest`
- `tcw serve --no-open --port 8765` then `curl -s localhost:8765/api/work | python -m json.tool` (manual smoke)
- `grep -rn "docs/" tcw/serve*` → expect no `docs/` path access in the web layer
- `git grep -n "dependencies" pyproject.toml` → unchanged

## Phase 5 — Documentation sync + capability flip (at completion)

- `README.md`: add `tcw serve` to the command list + a short quickstart.
- `docs/release-notes/upcoming.md`: user-facing note ("browse your board in a
  local web app").
- `docs/changelogs/upcoming.md`: Added (`tcw serve`, `WorkStore.artifacts`),
  Changed (board `stages()` now via `artifacts()`), with commit hash range.
- `skills/tcw-work/SKILL.md`: note the `artifacts()`/`open_artifact` surface and
  `tcw serve` if it references board stages.
- `tcw capabilities set web#browse-tcw-content-in-a-local-web-app --status Supported`.
- Run `skill-cefailures:documentation-sync` before completion; offer a version bump.

## Notes for the implementer

- `tcw work start <slug>` **before** the first code edit; commit that transition
  (with committed `spec.md`/`plan.md`) as the first implementation commit.
- Keep the web layer store-only — the litmus test is an acceptance criterion,
  not a nicety.
