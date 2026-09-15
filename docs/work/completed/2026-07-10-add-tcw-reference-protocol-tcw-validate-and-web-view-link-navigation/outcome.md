# Outcome — tcw:// references + tcw validate + web-view navigation

Implementation complete through T4 (the code feature); **T5 (docs sync) and live
browser click-through verification remain** — paused here for user verification
before closeout (no `tcw work complete` yet).

## What changed

- **T1 — `tcw/refs.py` (new).** `TcwRef` + `ResolveResult` dataclasses;
  `parse_tcw_uri` (pure, total — split-before-decode, first-bare-axis-wins,
  rejects missing axis / empty ref / traversal / control chars in any segment);
  `resolve_tcw_ref` (adapter glue over existing `FsTaxonomyStore.get` /
  `FsCapabilitiesStore.get` / `resolve_qualified_work_ref`; descendant work gated
  on `include_descendants`; never propagates a store exception). No new
  store-interface method → litmus-clean.
- **T2 — `tcw/validate.py` (new) + `tcw/cli.py`.** `tcw validate [path]`:
  (a) YAML well-formedness via the unique-key loader; (b) `](tcw://…)` link
  resolution after stripping fenced + inline code spans; (c) taxonomy +
  capabilities `check()` (narrowed by `[path]`; skipped + noted on a YAML *syntax*
  error). Grouped problems, exit 1 on any else `validate OK`.
- **T3 — `tcw/serve/__init__.py`.** `POST /api/resolve` — batch `{uris:[…]}` →
  `{uri: {ok, axis, key}|{ok:false}}`, capped at 256, reusing the loopback/JSON/
  size guards. Axis letter → SPA word mapped server-side.
- **T3a — `marked.min.js` shim + `VENDOR.md`.** The shim now emits
  `<a href="tcw://…">text</a>` for the inline `[text](tcw://…)` form only (text
  still escaped; no other scheme).
- **T4 — `app.js` + `style.css`.** `wireTcwLinks()` scans each read-render body's
  `<article>` for `a[href^="tcw://"]`, batch-POSTs `/api/resolve`, and sets
  `data-nav-*` + an in-app href on resolvable anchors / `.tcw-inert` on the rest
  (also inert on a resolve-call failure — fail safe). A delegated click handler on
  the persistent `#detail` `preventDefault`s and navigates the SPA (`applyRoute` +
  `pushRoute`, so browser-back works).

## Verification performed

- **Full pytest suite green: 539 passed** (incl. new `tests/test_refs.py` (24),
  `tests/test_validate.py` (12), `tests/test_serve_resolve.py` (6)).
- **Dogfood:** `tcw validate` on this repo → `validate OK` (exit 0). It initially
  flagged a false positive on `plan.md`'s scheme-teaching examples with adjacent
  backtick runs (```` ``` ````); fixed by upgrading the code-span stripper to a
  CommonMark-style equal-length-run matcher, and pinned it with a regression test.
- **Serve HTTP smoke:** server boots, serves updated `app.js`/`marked.min.js`/
  `style.css`, and `/api/resolve` returns correct `ok`/axis/key for a real
  capability + `ok:false` for dangling/malformed.
- **Shim render (node):** `[the login cap](tcw://C/web)` → a real `tcw://` anchor;
  `http://` link left as escaped literal text; body text still escaped.

## Deviations from plan.md

- None structural. The only mid-flight change: the T2 code-span stripper needed to
  be CommonMark-equal-length-run aware (not the naive `` `…` ``/```` ```…``` ````
  regexes first written) to keep the scheme-teaching docs under `docs/work` from
  failing their own validator — caught by dogfooding, as the plan intended.

## Remaining (not yet done)

- **T5 — docs sync** (`README.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `skills/tcw-{capabilities,taxonomy,work}` bodies).
- **Live browser click-through** of the SPA nav (JS isn't exercised by pytest):
  click a `tcw://` link → in-app navigate + browser-back; a foreign/unhosted link
  renders inert with a tooltip.
- **Closeout:** capabilities reconciliation (flip the 2 new + 1 changed entries),
  version bump (likely minor), `tcw work complete`.

## Follow-up notes

- Documented limitation (as designed): an `extends` alias / node dir literally
  named `t`/`c`/`w` is swallowed as the axis (first-bare-axis-wins). Pinned by a
  test; not code-enforced (pathological).
