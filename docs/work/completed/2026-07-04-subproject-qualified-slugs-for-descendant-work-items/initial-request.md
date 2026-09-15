# Subproject-qualified slugs for descendant work items

## Requested outcome

When a TCW command aggregates work items across descendant nodes, the slugs of
items that live in a descendant node must carry a **subproject qualifier** so the
reader can tell which node they belong to — and that qualified slug must be a
first-class address that resolves correctly when passed back to any command.

Concretely, the user's example:

> If you call `tcw work list --include-descendants` from `SomeFolder/` and it
> shows work items from `SomeFolder/SubprojectA/`, the slugs from SubprojectA
> should include an identifier before them showing they are in SubprojectA.
> Furthermore, you should be able to use all TCW commands like
> `tcw work show {slug}`, and if the slug has a subproject in it, it resolves
> correctly.

The anchor for "relative to" is **the directory the command was invoked in** (the
active node, resolved from the nearest `tcw-config.yaml`), or **the node
`tcw serve` was rooted at**.

## Decisions already made (from planning discussion)

1. **Scope:** CLI **and** `tcw serve`. Serve is currently single-node; it gains
   an opt-in `--include-descendants` mode that aggregates descendant boards and
   resolves qualified slugs across the work API. (Taxonomy/capabilities have no
   descendant aggregation today and stay out of scope.)
2. **Which commands resolve qualified slugs:** **all** work commands that take a
   slug (`show`, `path`, `start`, `edit`, `complete`, `drop`) — not just the
   read-only ones. Rationale: a qualified slug is exactly equivalent to
   `cd SubprojectA && tcw work <cmd> <bare-slug>`, which is already allowed, so it
   grants no new capability — only ergonomics.
3. **Qualifier syntax:** node-relative path + `/` + bare slug, e.g.
   `Project-A/2026-07-04-foo`, `Project-A/Nested/2026-07-04-deep`. Matches the
   existing `# ./Project-A` group header and the taxonomy `alias/slug`
   federation precedent. Bare slugs never contain `/` (`slugify` →
   `[a-z0-9-]`), so the final `/`-segment is unambiguously the slug.

## Constraints & non-goals

- **Prime directive (abstraction litmus test):** must not add a `WorkStore` ABC
  method or `WorkItem` field that only the filesystem adapter could honor. The
  qualifier is a node-relative path *discovered by the FS adapter* and assigned
  *by the anchor at render time* — it is not a stored property of the item.
  Resolution therefore lives in an FS-adapter-local helper + the CLI/serve
  layers, leaving the abstract spine untouched.
- **Backward compatibility:** a bare slug (no `/`) must keep resolving against the
  anchor node **only** — bare-slug lookups must not silently start searching
  descendants (that would be ambiguous and could change existing behavior).
- **Security (serve):** qualified-slug resolution takes untrusted web input; it
  must reject path-traversal qualifiers (`..`, symlink escapes) — resolve only to
  a real node that is genuinely within the anchor.
- Non-goal: cross-node *blocking relations* (blockers remain node-local bare
  slugs, interpreted within the resolved node).
- Non-goal: descendant aggregation for taxonomy/capabilities.

## Open questions for spec

- Should `tcw serve --include-descendants` default on or off? (Leaning **off** for
  parity with `list` and to preserve current serve behavior — confirm in spec.)
- Any frontend polish (node grouping/labels) beyond making qualified slugs
  functional, or defer that to a follow-up? (Leaning: functional now, grouping
  polish optional.)
