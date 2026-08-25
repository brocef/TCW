# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `/api/resolve` failure objects now carry why a reference did not become a
  link. `reason` is a closed two-value discriminator: `"unhosted-project"`,
  which carries the owning `project`, or `"unresolved"`, which carries `detail`
  — the resolver's own message, the same one `tcw validate` prints. A bare
  `{"ok": false}` no longer occurs.
- `tcw-unhosted` / `tcw-project-badge` rendering in the web client: a reference
  that resolves in the registered graph but is not on the board being served is
  drawn in the amber warning treatment with a project badge after the link text,
  and the sentence `Project <id> is not included in this board` is exposed as
  the anchor's accessible description via a visually-hidden `tcw-sr-only` note
  rather than as a `title` alone.

### Fixed

- `tcw://` link resolution applied nothing at all on a work item's document tab
  — not the new off-board treatment, not `tcw-inert`, and not the `data-nav-key`
  rewrite, so references there were neither navigable nor marked. `Markdown`
  applied `/api/resolve`'s answers to the anchors it captured _before_ the
  request; a render in between replaces that content with identical HTML, which
  detaches those nodes while leaving the effect's deps (`[html, resolveLinks]`)
  unchanged, so it never re-runs and the writes land on nothing.
  `work-document-tabs.tsx` triggers this on every mount — its `[item.slug]`
  effect resets state, and a child's effect runs before its parent's. The
  response handler now re-queries the container instead of trusting the captured
  nodes, which fixes every call site rather than that one parent. Pre-existing;
  reproduced against `5ecdb9a`'s bundle before the fix.
- An unopenable `tcw://` reference kept its `href`. The delegated click handler
  navigates only on `data-nav-key`, so clicking one handed the click to the
  browser's `tcw://` protocol handling while `cursor: not-allowed` claimed
  otherwise. Both failure appearances now drop the `href` and keep the address
  in `data-tcw-ref`. This corrects the pre-existing `tcw-inert` path too.
- `tcw serve` discarded both halves of what `resolve_tcw_ref` had already
  computed — the failure reason and the owning project — flattening four
  distinct situations (off-board, malformed, dangling, store error) into one
  struck-through grey appearance with the raw URI in the tooltip. A valid
  cross-project reference was therefore indistinguishable from a typo, which is
  how documents accumulated silently-downgraded references.

### Internal

- `_hosted_projects()` is computed at most once per `/api/resolve` batch instead
  of once per foreign reference, which had re-walked the descendant nodes up to
  `RESOLVE_MAX_URIS` times. It is taken lazily, on the first foreign reference,
  so a batch that is entirely local, malformed, or dangling neither pays for the
  descendant walk nor can fail on it. It is a snapshot, not an invariant: one
  batch answers from one reading of the graph.
- `tcw/serve/dist` rebuilt from the client source (`pnpm build`); verified with
  `pnpm check:build`.
