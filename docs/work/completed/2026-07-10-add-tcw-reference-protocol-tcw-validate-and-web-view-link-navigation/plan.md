# Plan — tcw:// references + tcw validate + web-view navigation

Spec: [`spec.md`](spec.md). TDD throughout (pytest over `tmp_path` git repos). No new store-interface methods — everything dispatches through existing `get()` / `resolve_qualified_work_ref`, so the litmus test is satisfied by construction.

**Order:** T1 (parse+resolve) is the shared spine and lands first; T2 (validate), T3 (serve resolve API), and T3a (render-shim anchors) run in parallel on top of it (T3a is independent of T1); T4 (SPA nav) needs both T3 and T3a; T5 (docs) last.

## T1 — `tcw/refs.py`: parse + resolve
- `TcwRef(namespace, axis, ref)` + `ResolveResult(ok, axis, key, reason)` dataclasses.
- `parse_tcw_uri(uri) -> TcwRef | None`: require `tcw://`; **split on `/` first, then `decodeURIComponent`-equivalent each segment** (match `app.js:2752`); axis = first segment whose `.upper()` ∈ {T,C,W}; namespace = before, ref = after; reject missing axis / empty ref / any segment (namespace **or** ref) with `..` / control / NUL (reuse the guard style of `_safe_store_id`, `fs.py:381`). Total function (never raises).
- `resolve_tcw_ref(node_root, uri, include_descendants=False) -> ResolveResult`: dispatch T→`FsTaxonomyStore`, C→`FsCapabilitiesStore` (`get(<ns/ref or ref>)`, `key = obj.qualified`), W→`resolve_qualified_work_ref` (`key = ns-qualified slug`; a namespaced/descendant ref → `ok=False` unless `include_descendants`). Wrap store calls in a **broad `except Exception` → `ok=False, reason=str(e)`** (also catches `AmbiguousRef`/`RefError`); absent node/store → `ok=False`.
- **Touch:** new `tcw/refs.py`. **Tests:** `tests/test_refs.py` — grammar round-trips + rejects (missing axis, empty ref, ref traversal, **namespace traversal/control char**, multiple slashes, `tcw://T/C/ref` collision → first-wins, split-before-decode via `%2F`); resolve of local / alias-federated (T,C) / descendant-node (W, with+without `include_descendants`) / dangling / ambiguous / foreign-namespace.

## T2 — `tcw validate [path]`
- Add `tcw/validate.py` (`validate(node_root, path=None) -> list[str]`): scan roots = `[path]` or the three `docs/<component>` trees; (a) every `*.yaml` → `load_yaml(unique=True)`, parse error → problem (track whether any was a **syntax** error); (b) every `*.md` → **strip fenced ```` ``` ```` and inline `` ` `` code spans, then regex-match only `](tcw://…)` link targets** → `resolve_tcw_ref`, unresolved/malformed → problem; (c) run component `check()`s — both with no `path`, else the one whose tree the path falls under (`docs/taxonomy`/`docs/capabilities`; else none) — **skipped (and noted) if (a) hit a YAML syntax error**, since `check()` re-`load_yaml`s and would raise.
- `tcw/cli.py`: register `validate` (`sub.add_parser("validate", …)` with optional `path`, `set_defaults(func=_cmd_validate)`); print grouped problems, exit 1 if any else `validate OK`.
- **Touch:** `tcw/validate.py`, `tcw/cli.py`. **Tests:** `tests/test_validate.py` — clean node OK; bad YAML doesn't crash + skips component checks; dangling/malformed `](tcw://…)` link; **a `tcw://` in a fenced code block is ignored**; a delegated component-check failure; `docs/capabilities` narrowing runs its check; exit codes.

## T3 — serve `POST /api/resolve`
- `tcw/serve/__init__.py`: POST route `"/api/resolve"` → validate via `_validate_mutating_request` + `_read_json_body` (loopback + JSON + `MAX_BODY_BYTES`), parse `{"uris":[…]}`, **cap the list at 256**, map each via `resolve_tcw_ref(self.server.node_root, uri, include_descendants=self.server.include_descendants)` → `{uri: {ok, axis, key}}`.
- **Touch:** `tcw/serve/__init__.py` (POST route table). **Tests:** `tests/test_serve_resolve.py` — resolvable local + federated (T/C) + descendant W with/without `include_descendants` + foreign (`ok:false`); malformed uri; batch; **oversize/over-256 payload rejected/capped without hanging**.

## T3a — render shim emits `tcw://` anchors (prerequisite for T4)
- `tcw/serve/static/marked.min.js` is a minimal shim that escapes every line and emits no `<a>`. Extend it to render the **inline link form `[text](tcw://…)` for the `tcw://` scheme only** as `<a href="tcw://…">escaped-text</a>` (leave all other text escaped; no other scheme, no reference-style links). Update `VENDOR.md` to record the addition.
- **Touch:** `tcw/serve/static/marked.min.js`, `tcw/serve/static/VENDOR.md`. **Verify:** a body with `[x](tcw://C/a)` renders an anchor (serve smoke).

## T4 — SPA `tcw://` navigation (`app.js`)
- After each **read-render** body renders (`renderCapability`/`renderTaxonomy`/`renderWork` — **not** the editor preview, avoiding the dirty-guard), scan the rendered `<article>` for `a[href^="tcw://"]`, batch-`POST /api/resolve`; per anchor: resolvable → `data-nav = pathFor(axisWord, key)` (map T/C/W→taxonomy/capabilities/work) + a delegated click handler that `preventDefault`s and navigates in-app (`state.view`/`state.selected` + `render()` + `pushRoute()`); unresolvable **or resolve-call failure** → `class="tcw-inert"` + `title` = raw uri + `preventDefault`. Minimal CSS for `.tcw-inert`.
- **Touch:** `tcw/serve/static/app.js` (+ `styles.css` if separate). **Verify:** driven via the `verify`/serve smoke (JS isn't in pytest) — a link navigates + back works; a foreign link is inert.

## T5 — docs sync
- `README.md` [Public-API] — `tcw validate` + `tcw://` linking.
- `docs/release-notes/upcoming.md` [Public-API]; `docs/changelogs/upcoming.md` [Any-Code-Change] (commit range).
- `skills/tcw-capabilities/SKILL.md` + `skills/tcw-taxonomy/SKILL.md` (+ tcw-work) [Skill-Driven-Component] — a line on authoring `tcw://` links in bodies and running `tcw validate`.

## Verification
- Full `pytest` green incl. `test_refs.py`, `test_validate.py`, serve resolve tests.
- `tcw validate` exercised on this repo's own node (dogfood) — expect `validate OK` or real findings.
- Serve web-nav driven via the `verify` skill: click a `tcw://` link → SPA navigates + browser back returns; a foreign link renders inert.

## Closeout
- Reconcile capabilities (flip the three new/changed entries), evaluate doc-sync, offer a version bump (likely **minor** — additive command + linking).
