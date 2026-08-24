# Render an unhosted tcw:// reference as a visibly distinct non-link naming its project

A `tcw://` reference to a real item that simply is not on the board being served
should not look the same as a broken one. Today it does, and that is how four
request documents in an orchestrator accumulated silently-downgraded references
that nobody noticed.

The viewer currently has one failure appearance for every way a reference can
fail to become a link: struck-through gray text with the raw URI in the tooltip.
That appearance is correct for a typo and wrong for a valid cross-project
reference — the reader is given no way to tell "this link is broken, fix it"
apart from "this item exists, it is just in another project, open that board
instead."

Two things are wanted.

**Tell the reader an off-board reference is off-board, loudly.** An unhosted
reference should stand out in the flow of prose — not merely gray and struck
through, but marked in a warning treatment that is obvious at a glance, with the
project it belongs to named next to the link text and stated in an accessible
label. A document full of downgraded references should be visibly full of them
on sight, without hovering anything. That is the property that failed in the
originating report: the degradation was silent.

**Distinguish valid-but-elsewhere from actually broken.** An unhosted reference
is not a defect — the document is correct and the board is narrow. A malformed
URI or a dangling item is a defect in the document. Those two should read
differently. The reasons the resolver already knows why a reference failed —
malformed URI, no such item, a store error — should reach the reader instead of
being flattened into the same tooltip, so a genuine mistake is diagnosable
without leaving the page.

## Constraints

- The reproduction cases are a descendant reference in plain `serve` mode and an
  ancestor reference from a child node. Both must be recognizable as unhosted.
- Whatever a viewer displays about a failure is displayed to whoever can reach
  the server; a failure detail that names filesystem paths should be weighed
  before it is surfaced.

## Out of scope

- Changing which projects a board hosts. `_hosted_projects()` is deliberately
  not touched; the ask is presentation of what it already decides.
- Making `tcw validate` flag references a viewer would render dead. Settled
  **no** in the superseded item: hostability is a property of the `serve`
  invocation, not of the stored data.
- The self-qualified-link symptom from GitHub issue #12. It no longer reproduces
  on HEAD and its work-store defect was fixed elsewhere.

## Notes

- Asked the requester for reference material beyond the intake; none provided.
- The visibility level (loud inline marker over a quieter badge) and the
  decision to distinguish broken references from unhosted ones were both chosen
  by the requester at this stage, over narrower alternatives.
- The superseded item's spec sketched a response shape (`reason:
  "unhosted-project"`, `project: <id>`) and a presentation. The intake carries it
  as a starting point, explicitly not a settled design; the second ask above goes
  past what that sketch covered.

## References

- `docs/work/backlog/2026-08-19-render-an-unhosted-tcw-reference-as-a-visibly-distinct-non-link-naming-its-project/intake.md`
  — the carve-out history and the reproduction, in full.
- `docs/work/discarded/2026-08-12-resolve-self-qualified-tcw-links-in-tcw-serve/spec.md`
  — the superseded spec this was split out of; says why the other half died.
- `tcw/serve/__init__.py:971` — where every unhosted or failed reference is
  flattened to a bare `{"ok": false}`.
- `tcw/refs.py:100-131` — `resolve_tcw_ref`, which already computes both the
  failure reason and the owning project that the response discards.
- `web/client/src/ui/shared-components.tsx:60-75`, `web/client/src/style.css:261`
  — the single `tcw-inert` appearance every failure currently collapses into.
