# Resolve self-qualified tcw:// links in tcw serve — Specification

## Capability changes

No capability-ledger delta is required. This repairs qualified-link navigation within the existing local web viewer.

## Problem

The viewer resolves `tcw://` work references through `/api/resolve`, then additionally requires a qualified reference's project to be in `_hosted_projects()` (`tcw/serve/__init__.py:919-934`). That set is empty without descendant aggregation and contains descendants only with it; the served anchor is omitted in both cases (`tcw/serve/__init__.py:399-413`). Consequently, a valid reference qualified with the current node's own project ID is rendered inert even though the board serves that item.

The SPA already marks rejected TCW anchors with `tcw-inert` and copies the URI into `title`, but that treatment does not explain that the named project is outside the current board (`web/client/src/ui/shared-components.tsx`, styled by `web/client/src/style.css` and generated into `tcw/serve/dist`).

## Goals

- Treat the anchor node's registered project ID as hosted in both normal and `--include-descendants` modes.
- Preserve descendant hosting only when aggregation is enabled.
- Make valid-but-unhosted references visibly distinct and identify their project without turning them into navigable links.
- Keep validation concerned with reference validity, not a particular serve invocation.

## Non-goals

- Serving ancestors or arbitrary registered peers.
- Changing qualified-reference storage or validation semantics.
- Adding network navigation to another TCW server.
- Making `tcw serve` run lifecycle hooks.
- Altering bare-reference behavior.

## Design

### Hosted project set

Build `_hosted_projects()` from the anchor first, using `registered_project_id(anchor, anchor)`. When `include_descendants` is true, union the registered IDs of `descendant_nodes(anchor)`. This mirrors `_board()`, whose served roots are exactly `[anchor]` or `[anchor, *descendants]` (`tcw/serve/__init__.py:415-427`).

Project registration errors should follow the same behavior already used by qualified resolution; do not invent an unregistered fallback ID. Bare references still bypass project membership.

### Resolution response

Keep the existing `ok` contract: a syntactically valid and resolvable reference is `ok: true` only when its destination is hosted. Extend unsuccessful resolved responses with enough structured context for presentation: `reason: "unhosted-project"` and `project: <id>`. Invalid or missing references retain their existing failure shape and do not masquerade as remote destinations.

### Viewer presentation

When the resolver reports `unhosted-project`, replace link behavior with the existing inert style plus an accessible label/title such as `Project <id> is not included in this board`. Add a small visible project badge adjacent to the original link text. Other unresolved references retain today's inert rendering and URI tooltip.

The React source is authoritative; rebuild and commit `tcw/serve/dist` because the Python package serves the vendored bundle.

## Acceptance criteria

- In ordinary serve mode, `tcw://W/<anchor-id>/<slug>` resolves to the same work key as `tcw://W/<slug>`.
- With `--include-descendants`, qualified links to both the anchor and every included descendant resolve and navigate.
- Without `--include-descendants`, a valid descendant reference remains unhosted.
- Ancestor and peer references remain unhosted even if valid in the registry.
- An unhosted response names the project and is rendered as a non-navigable, visually distinct element with accessible explanatory text.
- Missing/malformed references retain their existing unresolved presentation.
- Server resolver tests, client tests, and the production web build pass.

## Risks

- Conflating validity with hostability would make validation invocation-dependent. The design keeps that distinction in `serve` only.
- Changing the resolver payload can drift from the bundled client. Server tests plus a client production build guard the contract.
- Anchor IDs depend on registry configuration. Tests must cover both serve modes using registered nodes rather than hard-coded assumptions.
