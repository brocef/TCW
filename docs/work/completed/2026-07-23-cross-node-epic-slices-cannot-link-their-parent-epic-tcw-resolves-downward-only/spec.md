# Spec — Cross-node epic slices cannot link their parent epic

## Capability changes

No new capability. This restores an already-documented ability — addressing and
linking a work item by `<project-id>/<slug>` across a registered graph — that
silently worked in one direction only. The capabilities ledger is unchanged; the
README/skill wording that describes the locator is corrected (see Documentation
sync).

## Route decision

Route **1** — let `<project-id>/<slug>` resolve to any node in the registered
graph — plus route **3**'s clearer error. User decision, 2026-07-23. Route 2
(document the restriction) is moot once the restriction is gone, but the
`cross-node-epic.md` walkthrough still gains an explicit "link your epic like
this" line.

## Current-state findings

Reproduced end-to-end in a throwaway two-node graph (`parent-proj` with child
`child-proj`, reciprocally registered, `tcw validate` clean):

```
# in child-proj
Epic: [Parent epic](tcw://W/parent-proj/2026-07-23-parent-epic)
→ tcw validate: no work item: parent-proj/2026-07-23-parent-epic

# in parent-proj
Slice: [Child slice](tcw://W/child-proj/2026-07-23-child-slice)
→ validate OK
```

### The single root cause

`resolve_qualified_work_ref` (`tcw/store/fs.py:172`) builds its lookup table from
`registry.descendants()` only (`tcw/store/fs.py:217`) and returns `None` for any
other qualifier. Every cross-node path funnels through it:

- `tcw work <cmd> <proj>/<slug>` addressing — `tcw/work/cli.py:65`;
- `tcw://` link resolution — `tcw/refs.py:113`, used by `tcw validate`
  (`tcw/validate.py:153`) and `tcw serve` (`tcw/serve/__init__.py:897`).

So one guard fixes all of them. The function's docstring still describes a
path-containment model ("genuinely inside `anchor`", traversal/`.git` escapes),
but the implementation already keys on canonical project IDs from the registry —
the containment prose is stale and the ID lookup is what actually enforces
safety. Registered connections are required to be reciprocal
(`FsProjectRegistry._validate_reciprocity`) and IDs are canonical and
cycle-checked, so admitting the whole graph adds no ambiguity and no new trust.

`FsProjectRegistry` already exposes `get(project_id)` over the full loaded graph
alongside `descendants()` / `ancestors()` — the wider lookup needs no new
registry method, and no new store-interface method. Litmus: resolving a
reference through canonical IDs in a registered graph is the abstract
"reference" vocabulary; nothing filesystem-specific is implied.

### Which `tcw://` spelling is affected

`parse_tcw_uri` treats the **first** T/C/W segment as the axis, so the two
spellings take different paths:

- `tcw://<ns>/W/<slug>` — namespace parsed; gated on `include_descendants`.
- `tcw://W/<qualifier>/<slug>` — namespace empty; the whole
  `<qualifier>/<slug>` becomes the ref and goes to
  `resolve_qualified_work_ref`.

The issue (and the README/skill wording) uses the second spelling. Both funnel
into the same lookup, so both are fixed.

### Adjacent defect found, deliberately out of scope

For the `tcw://W/<proj>/<slug>` spelling, `resolve_tcw_ref` returns a **bare**
key (`tcw/refs.py:117` — `parsed.namespace` is empty), so the SPA looks the slug
up in the local node and dead-ends. It also bypasses the `include_descendants`
hosting gate at `tcw/refs.py:109`. Verified today against a *descendant* link, so
this is pre-existing and not introduced here — `tcw validate` only inspects
`.ok`, which is why it never surfaced. Fixing it means reworking
`resolve_tcw_ref`'s hosting contract (a viewer concern that arguably does not
belong in a validity check at all) and is a separate change. Filed as a
follow-up at closeout; not fixed by this item.

Consequence to state plainly in the release notes: after this fix an upward epic
link **validates**, and the web viewer cannot open it (a child's viewer
aggregates descendants, never ancestors).

## Goals

1. `<project-id>/<slug>` resolves against any node in the registered graph, in
   any direction, for both CLI addressing and `tcw://` links.
2. A failed qualified ref names the cause rather than the symptom.
3. Docs describe the locator as graph-wide, and `cross-node-epic.md` shows the
   epic link explicitly.

## Non-goals

- The SPA hosting/key defect above.
- Any change to `tcw work list --include-descendants`, which is a board-aggregation
  feature and stays descendant-only.
- Loosening the "registered and reciprocal" requirement. An unregistered or
  non-reciprocal project stays unresolvable.
- The `T` / `C` axes. They namespace through `extends` aliases, a separate
  mechanism that is not direction-restricted; unchanged.

## Proposed behavior

### Graph-wide qualifier resolution

`resolve_qualified_work_ref` looks the qualifier up with `registry.get(qualifier)`
over the full validated graph instead of a `descendants()`-only table. Everything
else — the bare-slug path, the status-path locator, the `docs/work` existence
check, the "slug never contains `/`" split — is unchanged. The stale containment
prose in the docstring is rewritten to describe the ID-based graph rule.

Self-qualification (`<own-id>/<slug>`) resolves to the local store, which is
consistent and costs nothing.

### Cause-naming errors

When a qualified ref fails, distinguish:

- qualifier is not a project in the registered graph →
  `no such project in this graph: <qualifier>` (plus the existing
  `no such work item` when the project resolves but the slug does not);
- qualifier is a registered project with no work component →
  `<qualifier> has no work component`.

`resolve_qualified_work_ref` returns `tuple | None` with no reason channel. Rather
than reshape its return type (three call sites, one of which is in the pure-ish
`refs` glue), the callers that print — `_resolve` (`tcw/work/cli.py:65`) and the
W branch of `resolve_tcw_ref` — consult the registry on the failure path only and
pick the specific message. Failure paths are cold; the extra registry open costs
nothing that matters.

## Acceptance criteria

1. In a reciprocally registered parent/child graph, a child item whose
   `initial-request.md` links `tcw://W/<parent-id>/<epic-slug>` passes
   `tcw validate`.
2. The reverse (parent → child) still passes.
3. `tcw work show <parent-id>/<epic-slug>` from the child node prints the parent's
   item; the same qualified form works for `edit` and other work commands.
4. A sibling/cousin node in the same registered graph resolves too.
5. An unregistered project ID, a path qualifier (`nested/<slug>`), a traversal
   (`../nested/<slug>`) and an absolute qualifier all still fail — the existing
   guards in `tests/test_qualified_ref.py` keep passing unchanged.
6. `tcw validate` on a bad qualifier names the cause, not `no such work item`.
7. Bare slugs and `<status>/<slug>` locators are unaffected.

## Risks

- A qualified ref can now mutate an item in an *ancestor* node
  (`tcw work start <parent-id>/<slug>` from a child). This is the intended
  consequence of graph-wide addressing and matches how descendant addressing
  already behaves in the other direction; it is called out in the release notes.
- `registry.get` spans the whole graph, so resolution may open a node further away
  than before. Registry loading already walks the full graph for validation, so
  there is no new traversal cost.

## Documentation sync

- `README.md` — the `tcw://` locator section (~L593) and the qualified-slug
  paragraph (~L588): graph-wide, both directions, still registered-only.
- `skills/tcw-work/SKILL.md` — the "reference another object in prose" and
  "address a descendant item" quick-reference rows.
- `skills/tcw-work/references/cross-node-epic.md` — add the explicit epic
  back-link line at the point the workflow tells you to adopt a slice.
- `docs/release-notes/upcoming.md` — upward links now work; viewer caveat.
- `docs/changelogs/upcoming.md` — Fixed / Changed entries.

## Related work

Independent of
`2026-07-23-blocker-refs-comma-split-mangles-external-text-and-unblocked-by-silently-no-ops`.
Upstream: GitHub issue #7.
