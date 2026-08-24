# Render an unhosted tcw:// reference as a visibly distinct non-link naming its project

## Origin

Carved out of `2026-08-12-resolve-self-qualified-tcw-links-in-tcw-serve`, which
was **discarded as superseded** on 2026-08-13. That item came from GitHub issue
[#12](https://github.com/brocef/TCW/issues/12), filed 2026-08-11 by @brocef.

That spec held two independent halves:

- **The hosted-project half** — the reported symptom, self-qualified
  `tcw://W/<own-id>/<slug>` links rendering inert. Absorbed: it no longer
  reproduces on HEAD, because `resolve_tcw_ref` short-circuits an anchor-local
  reference and returns no `project` (`tcw/refs.py:125-126`), so the
  `_hosted_projects()` membership test is never consulted. The underlying
  work-store resolution defect was fixed by
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`.
- **The presentation half** — this item. Independent of the above, still
  reproducible, and **nothing tracked it** between that discard and this sweep.

The follow-on the report also raised — a note beside the recommended link form
in `cross-node-deltas.md` — landed: "Note the viewer caveat: a child's
`tcw serve` aggregates descendants, so it cannot open an ancestor's item."
The other follow-on, whether `tcw validate` should flag a locator the viewer
will render dead, was settled **no** in the superseded item's Meta changes:
hostability is a property of the `serve` invocation, not of the stored data, so
`validate` has no invocation to check against.

## Inbox body

`/api/resolve` answers a valid-but-unhosted reference with a bare
`{"ok": false}` (`tcw/serve/__init__.py:971-973`), indistinguishable from a
malformed or missing one. The SPA then renders it with the `tcw-inert` style and
the URI in `title`, which does not tell the reader that the named project is
outside the board being served. That is what let four request documents in the
reporter's orchestrator accumulate silently-downgraded references unnoticed.

Reproducible today: in plain `serve` mode, `tcw://W/<descendant-id>/<slug>`
resolves `ok: false`, as does an ancestor reference from a child node. Both are
valid references to real items — they are simply not on this board.

From the superseded item's spec, as the starting point rather than a settled
design:

> ### Resolution response
>
> Keep the existing `ok` contract: a syntactically valid and resolvable
> reference is `ok: true` only when its destination is hosted. Extend
> unsuccessful resolved responses with enough structured context for
> presentation: `reason: "unhosted-project"` and `project: <id>`. Invalid or
> missing references retain their existing failure shape and do not masquerade
> as remote destinations.
>
> ### Viewer presentation
>
> When the resolver reports `unhosted-project`, replace link behavior with the
> existing inert style plus an accessible label/title such as `Project <id> is
> not included in this board`. Add a small visible project badge adjacent to the
> original link text. Other unresolved references retain today's inert rendering
> and URI tooltip.
>
> The React source is authoritative; rebuild and commit `tcw/serve/dist` because
> the Python package serves the vendored bundle.

Explicitly **not** carried over: the `_hosted_projects()` change. This item does
not need it.

## References

- `docs/work/discarded/2026-08-12-resolve-self-qualified-tcw-links-in-tcw-serve/spec.md`
  — the full reproduction history and why the other half was discarded.
- `tcw/serve/__init__.py:971` — where an unhosted reference is flattened to a
  bare `{"ok": false}`.
- `web/client/src/ui/shared-components.tsx`, `web/client/src/style.css` — the
  `tcw-inert` rendering to replace.
