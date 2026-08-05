# Add a rich Markdown editor to the local web app

> **Slug note:** the slug still says "vendored". That word is historical — it
> described the pre-rewrite constraint (single-file UMD assets shipped as Python
> package data). The web client is now a built React app, so the editor is a
> normal npm dependency bundled at build time. The title was corrected on
> 2026-07-28; the slug is the item's stable ID and is kept as-is.

## Context

Split out of `2026-07-02-interactive-local-web-editor-for-tcw-objects` (now
completed), which made `tcw serve` write-capable and shipped Markdown editing as
a raw textarea with live preview.

## Capability changes

This refines the existing `web/editing` capability; it does not create a new
capability by default. During specification, confirm the selected editor stays
inside that boundary. Record any genuinely distinct user outcome separately
rather than treating toolbar controls or syntax highlighting as capabilities.

`2026-07-22-modularize-and-standardize-the-tcw-web-client` (completed) then
replaced the hand-vendored client with a Vite + TypeScript + React app under
`web/`, built into `tcw/serve/dist/client/`. That rewrite invalidated every
packaging constraint this item was originally written against — a build pipeline
now exists, `marked` is a normal npm dependency rather than a hand-vendored
`marked.min.js`, and there is no `VENDOR.md` pattern to follow.

Editing is still a plain textarea + split preview
(`MarkdownEditor`, `web/client/src/ui/shared-components.tsx`), so the underlying
ask is unchanged: upgrade the widget.

## Product changes

Provide a richer Markdown editing experience (toolbar, formatting affordances,
optionally WYSIWYG) for the Markdown lifecycle artifacts and body surfaces in the
local web app, without regressing packaging or security.

## Technical changes

- Add the editor as a normal dependency of the `web/` client and let the existing
  Vite build bundle it into `tcw/serve/dist/client/`. `tcw serve` must still work
  fully offline — no runtime CDN or npm fetch.
- **MDX Editor is back on the table.** Its React/build cost was the sole reason
  this was deferred, and that cost is now already paid by the client rewrite.
  Evaluate it against alternatives on bundle size, CSP fit, and Radix/theme
  integration rather than on "does it need a build".
- Vendor selection must document license compatibility, production bundle-size
  impact, keyboard and screen-reader behavior, and offline/CSP compatibility.
- Swap the widget, not the plumbing: reuse the existing write API, revision
  tokens, dirty-state guard, and validation surfaces. `MarkdownEditor` already
  has a `value`/`onChange` contract every call site goes through — replace its
  body, keep its signature.
- Markdown files stay stored as `.md` text; the editor is a presentation layer.
- Extend the Playwright suite (`web/e2e/parity.spec.ts`) rather than adding a new
  harness — the Markdown-editing, dirty-nav, and stale-write scenarios there are
  the regression net for this change.

## Meta changes

- Keep the strict `default-src 'self'` CSP; document and narrowly scope any
  unavoidable relaxation (e.g. `style-src 'unsafe-inline'`).
- No new capability is expected — this refines the editing surface of the
  existing `web/editing` capability ("Edit TCW content in a local web app").

## Open questions for spec

- MDX Editor vs. a lighter React Markdown editor: which wins on bundle size and
  CSP fit now that the build pipeline is a non-issue?
- Is any CSP relaxation required, and can it be kept narrow?
- Does the richer editor apply to every Markdown surface (artifacts, bodies,
  descriptions) or only the long-form lifecycle artifacts?
