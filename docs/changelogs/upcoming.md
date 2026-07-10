# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="d0cc4ce" ending-hash="e9b6f0f">

## Added

- `tcw/refs.py` — the `tcw://` reference protocol. `parse_tcw_uri` (pure, total:
  split-before-percent-decode, first-bare-axis-wins, rejects missing axis / empty
  ref / traversal / control chars in any segment) and `resolve_tcw_ref` (dispatch
  through the existing `FsTaxonomyStore.get` / `FsCapabilitiesStore.get` /
  `resolve_qualified_work_ref`; descendant-node work resolves only when
  `include_descendants`; never propagates a store exception). No new
  store-interface method — litmus-clean.
- `tcw/validate.py` + `tcw validate [path]` in `tcw/cli.py` — aggregate node
  soundness: (a) every `*.yaml` loads via the unique-key loader; (b) every `*.md`
  `](tcw://…)` link-target resolves (fenced + inline code spans stripped with a
  CommonMark equal-length-run matcher, so scheme-teaching docs pass); (c) taxonomy
  + capabilities `check()` (narrowed by `[path]`; skipped and noted on a YAML
  *syntax* error, which would re-raise). Grouped problems, exit 1 on any.
- `POST /api/resolve` in `tcw/serve/__init__.py` — batch `{uris:[…]}` →
  `{uri: {ok, axis, key}|{ok:false}}`, capped at 256, reusing the loopback / JSON /
  `MAX_BODY_BYTES` guards; axis letter → SPA axis word mapped server-side.
- `tests/test_refs.py`, `tests/test_validate.py`, `tests/test_serve_resolve.py`.

## Changed

- `tcw/serve/static/marked.min.js` — the render shim now emits
  `<a href="tcw://…">text</a>` for the inline `[text](tcw://…)` form (that scheme
  only; text still escaped). Recorded in `VENDOR.md`.
- `tcw/serve/static/app.js` + `style.css` — `wireTcwLinks()` scans each
  read-render body for `a[href^="tcw://"]`, batch-POSTs `/api/resolve`, and marks
  anchors `data-nav-*` (resolvable) or `.tcw-inert` (unresolvable / resolve-call
  failure). A delegated click handler on `#detail` navigates the SPA in-place
  (`applyRoute` + `pushRoute`) so History/back works.

</changes>
