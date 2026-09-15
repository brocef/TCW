# Refined outcome — tcw:// references + tcw validate + web-view navigation

## Verification decision

**Approved.** The user drove the live web viewer (`tcw serve`) and reported
**success for all test cases**: resolvable `tcw://` links (Capability / Taxonomy
term / Taxonomy Feature / Work self) navigate the SPA in place with working
browser Back; foreign-namespace and dangling links render inert with a tooltip and
swallow the click.

## Refinements after initial implementation

- **Local LLM review round** (`bllm-review-many`, qwen25-coder + gemma4-26b).
  Both flagged a shim XSS as "blocking" — **verified a false positive**: `inl()`
  HTML-escapes the whole line before the link regex runs, so a captured `url` can
  never carry a raw `"`/`<`/`>` and the `href` can't be broken out of. Confirmed
  empirically against four attack vectors (attribute injection with/without space,
  tag injection, single-quote variant — all neutralized). Added a defensive
  ordering-invariant comment to `marked.min.js` so a future edit can't silently
  reintroduce the risk. All other findings dismissed with reasons (broad `except`
  is spec-mandated; `/api/resolve` body size already guarded by
  `_read_json_body`; `axis:null` never emitted on failure; file-path component
  check works per spec).
- **Code-span stripper** upgraded to CommonMark equal-length backtick-run matching
  (caught by dogfooding `tcw validate` on this repo's own scheme-teaching docs).

## Final verification evidence

- Full suite green: **539 passed** (incl. `test_refs.py` 24, `test_validate.py` 12,
  `test_serve_resolve.py` 6).
- `tcw validate` on this node → `validate OK` (exit 0), including after the
  capability reconciliation.
- Serve HTTP smoke + node render check of the shim.
- `tcw capabilities check` → OK after reconciliation.

## Closeout choices (user-selected)

- **Completion route:** merge the work branch into local `main` (no PR).
- **Version:** no new bump — **fold into the unreleased v0.11.0** (never pushed;
  origin/main is at v0.10.3). The five version files already read `0.11.0`; the
  `docs/{release-notes,changelogs}/upcoming.md` entries were moved into
  `v0.11.0.md` and `upcoming.md` reset. The `v0.11.0` tag is moved to the final
  commit.
- **Docs sync:** done — `README.md`, `v0.11.0.md` (both), and the tcw-taxonomy /
  tcw-capabilities / tcw-work skill bodies.
- **Capabilities reconciled:** `cli/reference-a-tcw-object` + `cli/validate-a-node`
  added Supported (with `Planning doc` back-pointers); `web` body updated for the
  in-app `tcw://` navigation.
- **Follow-ups:** none carried forward. Documented limitation (as designed): an
  `extends` alias / node dir literally named `t`/`c`/`w` is swallowed as the axis
  (first-bare-axis-wins); pinned by a test.
