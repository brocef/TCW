# Resolve self-qualified tcw:// links in tcw serve — Specification

> **BLOCKED — the premise below does not reproduce on HEAD (2026-08-13 review).**
> Do not implement the hosted-project half of this spec until the reporter's
> environment is nailed down. See "Reproduction status". The presentation half
> ("Viewer presentation") is independent and still valid.

## Capability changes

No capability-ledger delta is required. This repairs qualified-link navigation within the existing local web viewer.

## Reproduction status

Resolved against 0.21.0, a two-node registered graph, both serve modes:

| ref | plain `serve` | `--include-descendants` |
| --- | --- | --- |
| `tcw://W/<anchor-id>/<slug>` | `ok: true` | `ok: true` |
| `tcw://<anchor-id>/W/<slug>` | `ok: true` | `ok: true` |
| `tcw://W/<descendant-id>/<slug>` | `ok: false` | `ok: true` |
| `tcw://W/<ancestor-id>/<slug>` (from the child) | `ok: false` | — |

Every one of those is the documented intent. The reported failure is absent
because `resolve_tcw_ref` short-circuits a reference that lands on the anchor
node and returns **no** `project` (`tcw/refs.py:125-126`), so
`ok = r.ok and (not r.project or …)` never consults `_hosted_projects()` for the
anchor's own ID. That short-circuit is `ff2741f`, shipped in v0.14.0 — before the
0.18.2 the issue was filed against — so the report is not a version skew either.

**Leading hypothesis for the real trigger: a path-aliased anchor.** When `serve`
runs from a `.worktrees/<slug>` checkout (a `start --worktree` checkout copies the
sentinel), `store.node_root != node_root.resolve()`, the anchor's own reference is
classified foreign, and it fails the membership test exactly as reported. The
reporter is a heavy `--worktree` user. Any other path aliasing of the registered
locator — a symlinked project root, a relocated locator — produces the same shape.

**That hypothesis changes the fix.** `registered_project_id(anchor, anchor)`
*raises* `ValueError` when the anchor path is not a registered locator
(`tcw/store/fs.py:190`), which is precisely the aliased case; adopting the
reported remediation unchanged would turn an inert link into a 500 from
`/api/resolve`. A fix has to canonicalize the anchor, not just add it to a set.

### Hypothesis tested and disproven (2026-08-13, implementation attempt)

The path-aliasing hypothesis above was tested directly, in both shapes it names.
Neither reproduces on HEAD:

| Anchor reached via | `registered_project_id(anchor, anchor)` | self-qualified `tcw://W/<own-id>/<slug>` |
| --- | --- | --- |
| the real project path | `myproj` | `ok=True`, `project=''` |
| a **symlinked** project root | `myproj` | `ok=True`, `project=''` |
| a **`start --worktree` checkout** (copied sentinel, distinct real path) | `myproj` | `ok=True`, `project=''` |

`find_node_root` and `registered_project_id` both `.resolve()`, so a symlinked
anchor collapses onto the same real path; and a worktree checkout still resolves
its own registered ID rather than raising. In every case the anchor short-circuit
at `tcw/refs.py:125-126` fires and returns no `project`, so `_hosted_projects()`
is never consulted — exactly as the original review found.

So the hosted-project half has **no known reproduction and no surviving
hypothesis**. Implementing it would be writing code against a defect nobody can
demonstrate, and the spec's own Design section already records that it "fixes
nothing observable as written".

### Reporter's environment checked directly (2026-08-13)

The reporter confirmed `tcw serve` ran in `/Users/brian/Projects/proposit-orchestration/`
(project id `proposit-app`, default `docs/work`, four registered children). Tested
against that live node, read-only:

- `registered_project_id(anchor, anchor)` → `proposit-app`. No raise, no aliasing.
- **All eight** real `tcw://W/proposit-app/<slug>` references in that node's own
  `docs/work` resolve `ok=True, project=''`.

So the symptom does not reproduce against the reporter's real data, from the
reporter's real directory, on HEAD.

### The gate is not `_hosted_projects()`

`_hosted_projects()` cannot be the cause and never could: a self-qualified
reference short-circuits with no `project`, so `ok = r.ok and (not r.project or …)`
never consults it. The gate that *can* make a self-qualified reference inert is in
the resolver, one layer earlier:

```python
target = Path(target_project.locator)
if not _has_work_store(target):        # tcw/store/fs.py:249
    return None                        # -> ok=False -> inert link
```

Demonstrated: with the anchor's own work store unresolvable, a self-qualified
reference goes inert, and it recovers the moment the store resolves again.

That places the defect squarely in the **work-store resolution** class — the same
class as GitHub issues #15-#18, filed by the same reporter on the same day, during
the same migration of this very orchestrator to child nodes with external
`work.path`. Those four were fixed by
`2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`
(completed 2026-08-13), which made `_has_work_store` authoritative and routed
store resolution through the configured path.

**Conclusion: the hosted-project half is almost certainly already fixed, by a
different item, and its Design here targets the wrong function.** It should be
discarded as superseded rather than implemented. The presentation half is
independent and unaffected by any of this.

**The presentation half is independent and remains implementable**, because
genuinely unhosted references already occur and are reproducible today: the table
above shows `tcw://W/<descendant-id>/<slug>` resolving `ok: false` in plain serve
mode. That is precisely the case the viewer renders as an indistinguishable inert
link, which is what let four request documents accumulate silently-downgraded
references. It needs the `reason`/`project` payload extension but **not** the
`_hosted_projects()` change.

## Problem

The SPA marks rejected TCW anchors with `tcw-inert` and copies the URI into `title`, but that treatment does not explain that the named project is outside the current board (`web/client/src/ui/shared-components.tsx`, styled by `web/client/src/style.css` and generated into `tcw/serve/dist`). That is what let four request documents accumulate references the viewer silently downgraded to prose.

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

### Hosted project set — **pending re-specification**

Build `_hosted_projects()` from the anchor first, using `registered_project_id(anchor, anchor)`. When `include_descendants` is true, union the registered IDs of `descendant_nodes(anchor)`. This mirrors `_board()`, whose served roots are exactly `[anchor]` or `[anchor, *descendants]` (`tcw/serve/__init__.py:415-427`).

Three things this design does not yet answer, all of which the reproduction work
must settle first:

- **It fixes nothing observable as written.** A reference landing on the anchor
  already carries no `project`, so adding the anchor's ID to the set changes no
  answer for any case reachable today.
- **It raises where the real defect probably lives.** For an aliased anchor,
  `registered_project_id(anchor, anchor)` raises rather than returning an ID.
  Canonicalizing the anchor to its registered locator — and deciding what a
  genuinely unregistered anchor should serve — is the actual design question.
- **It must not be computed per reference.** `_hosted_projects()` is called
  inside the `/api/resolve` URI loop (`tcw/serve/__init__.py:931`). Today the
  non-aggregating path returns an empty set immediately; any version that opens
  and validates the registry has to be hoisted out of the loop, or a batch of
  `RESOLVE_MAX_URIS` references pays for that many registry reads.

Bare references still bypass project membership.

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
