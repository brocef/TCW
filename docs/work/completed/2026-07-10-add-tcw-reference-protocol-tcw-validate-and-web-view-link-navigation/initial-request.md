# Add tcw:// reference protocol, tcw validate, and web-view link navigation

## Requested outcome

A first-class way to reference TCW objects (Taxonomy / Capabilities / Work) by an explicit link, validate those links (and the YAML that backs objects), and follow them in the local web viewer. This is spec ③ — deferred from the folder-substrate + capability-federation work ([[2026-07-10-unify-folder-substrate-across-taxonomy-capabilities-work-and-add-capability-federation]]), whose stable capability ids are this feature's designed target.

Three parts:

1. **`tcw://` URI scheme** — `tcw://[<namespace>/]<axis>/<ref>`:
   - `<axis>` is `T` (Taxonomy), `C` (Capabilities), or `W` (Work).
   - `<namespace>` (optional) locates the object in another project: an `extends` alias for T/C, a descendant node path for W. Absent = the local node.
   - `<ref>` is the identifier within that axis (taxonomy slug/path, capability path, work slug).
   - Authored inline in markdown bodies, e.g. `[Auth with GitHub](tcw://shared/C/auth/providers/github)`.

2. **`tcw validate [path]`** — an aggregate node validator: YAML well-formedness, `tcw://` link resolvability, illegal-character checks, plus delegation to each component's existing `check()`. `[path]` optionally narrows the scan.

3. **Web-view navigation** — in `tcw serve`, a rendered `tcw://` link navigates the SPA to the target object using the History API (back button works). Best-effort: objects the viewer hosts (this node + aggregated descendants) navigate in-place; links to a namespace the viewer doesn't host render as styled-but-inert references.

## Decisions already made (brainstorming)

- **`tcw://` is for inline prose links in markdown bodies** (a capability's `description.md`, a work item's `spec.md`, etc.) — additive. It does **not** replace the existing structured pointers (`Subject`, `Feature`, `Planning doc`, `blocked_by`), which keep their bare-slug form.
- **`tcw validate` is an aggregate node validator** (YAML well-formedness + `tcw://` resolution + illegal chars + delegates to `taxonomy`/`capabilities` `check()`), not a standalone link-only checker.
- **Web-nav is best-effort, inert-if-unhosted**: hosted objects (local node + aggregated descendants) navigate the SPA; foreign-namespace links render as non-navigating styled refs (tooltip = the raw ref).
- **Axis token** is uppercase `T`/`C`/`W` (case-insensitively accepted, normalized to upper). The axis is the first path segment equal to a bare axis letter; everything before it is the namespace, everything after is the ref.

## Constraints / non-goals

- **Abstraction litmus test governs** (AGENTS.md): parsing a `tcw://` URI is pure; resolution dispatches through the abstract store `get()`s — no filesystem-only trick. Markdown scanning + web-nav are FS/serve-adapter details.
- No new remote adapters; namespace resolution reuses the existing local-path `extends` federation (T/C) and descendant-node addressing (W).
- Does not rewrite stored markdown; the `tcw://` → internal-route transform happens only on the serve render path, never on the editable content.
- Out of scope: authoring UI for inserting `tcw://` links; a global cross-repo index; remote (git/URL) namespace sources.

## Open questions for spec planning

- Exact grammar edge cases (a `<ref>` whose first segment is a bare `T`/`C`/`W`; percent-encoding of namespaces with spaces).
- Whether `tcw validate` scans only `docs/{taxonomy,capabilities,work}/` markdown or a wider set; how it reports (grouped, exit code).
- Web-nav resolution: client-side parse + optimistic route vs. a serve `resolve` endpoint for the inert-if-unhosted determination.
