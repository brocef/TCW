# Plan — Graph-wide `<project-id>/<slug>` resolution

Phases 1 and 2 are sequential (2 builds on 1's failure paths). Phase 3 depends on
both. Phase 4 is independent and can run in parallel with 3. No stage documents —
the change is small enough to hold in one read.

## Phase 1 — the resolution guard (`tcw/store/fs.py`)

In `resolve_qualified_work_ref` (~L172):

1. Replace the descendants-only table (~L217-220):

   ```python
   registry = FsProjectRegistry.open(anchor).require_valid()
   descendants = {project.id: project for project in registry.descendants()}
   target_project = descendants.get(qualifier)
   ```

   with a graph-wide lookup via the registry's existing
   `get(project_id)`. Everything below it (the `docs/work` check, the
   `FsWorkStore.open(target)` return) is unchanged.

2. Rewrite the docstring's stale containment prose. It currently claims the
   qualifier must be "a real node genuinely inside `anchor`" and talks about
   traversal / `.git` / `.worktrees` escapes; the implementation already keys on
   canonical registry IDs, and those escapes are excluded because they are not
   registered IDs — not because of a path check. State the real rule: the
   qualifier must be a project ID in the anchor's registered (reciprocal,
   cycle-checked) graph, in any direction; a bare slug and a `<status>/…/<slug>`
   locator stay local.

3. Confirm `registry.get` includes the anchor's own project so `<own-id>/<slug>`
   resolves locally. If it does not, that is acceptable — it is not an acceptance
   criterion — but record which way it went in `outcome.md`.

Do **not** touch `include_descendants` anywhere: `tcw work list -i` and the serve
aggregation stay descendant-only.

## Phase 2 — cause-naming errors

Both printing callers consult the registry **only on the failure path**.

1. `tcw/work/cli.py:65` (`_resolve`) — when `resolve_qualified_work_ref` returns
   `None` and the ref carries a non-status qualifier, open the registry and pick:
   - qualifier not in the graph → `no such project in this graph: <qualifier>`;
   - qualifier in the graph but no `docs/work` → `<qualifier> has no work component`;
   - otherwise → the existing `no such work item: <slug>`.
2. `tcw/refs.py` W branch (~L113-115) — same three-way message into
   `ResolveResult.reason`, so `tcw validate` and the serve `/api/resolve` route
   both report the cause.

Factor the three-way message into one helper rather than duplicating it. The
natural home is `tcw/store/fs.py` beside `resolve_qualified_work_ref` (it is the
same FS-adapter concern and both callers already import from there); the helper
takes `(anchor, ref)` and returns the message string. Wrap its registry open in a
`try` so a broken graph degrades to the generic message instead of raising into
`resolve_tcw_ref`, which is contractually non-raising.

## Phase 3 — tests

`tests/test_qualified_ref.py` — the existing four tests must pass **unchanged**
(they are the guard regression: unregistered ID, path qualifier, `..`, absolute).
Add:

1. Upward: child node resolves `<parent-id>/<slug>` to the parent's store.
2. Sibling: two children of one root resolve each other's `<id>/<slug>`.
3. Deep upward: grandchild resolves the root's `<root-id>/<slug>`.

`tests/test_refs.py` — add a child-node case asserting
`resolve_tcw_ref(child, "tcw://W/<parent-id>/<slug>").ok`. Keep
`test_resolve_descendant_work_needs_include` unchanged.

New or existing validate test — a child item whose `initial-request.md` links
`tcw://W/<parent-id>/<epic-slug>` validates clean; a bogus qualifier produces the
cause-naming message. (Check `tests/` for the existing validate-link test file and
add there rather than creating a new one.)

CLI-level: `tcw work show <parent-id>/<slug>` from the child node prints the
parent's item.

## Phase 4 — documentation sync

- `README.md` ~L588-595 — the qualified-slug paragraph and the "bare slug stays
  local" note: `<project-id>/<slug>` addresses any node in the registered graph,
  in any direction; unregistered projects and path qualifiers still fail.
- `skills/tcw-work/SKILL.md` — the "address a descendant item" and "reference
  another object in prose" quick-reference rows currently say *descendant*; widen
  to *registered graph node* while keeping the registered-only requirement.
- `skills/tcw-work/references/cross-node-epic.md` — at the point the workflow
  tells the child to adopt a slice, add the explicit epic back-link line
  (`Epic: [<title>](tcw://W/<parent-id>/<epic-slug>)`).
- `docs/changelogs/upcoming.md` — Fixed (upward/sibling resolution) and Changed
  (error messages name the cause).
- `docs/release-notes/upcoming.md` — plain language; include the two caveats:
  a qualified ref can now mutate an item in an ancestor node, and an upward link
  validates but cannot be opened in the child's web viewer.

Run the `skill-cefailures:documentation-sync` skill before reporting complete.

## Phase 5 — closeout follow-up

Record in `outcome.md`, and at closeout ask the user whether to file it as a
backlog item: `resolve_tcw_ref` returns a **bare** SPA key for the
`tcw://W/<proj>/<slug>` spelling and bypasses the `include_descendants` hosting
gate (`tcw/refs.py:109,117`), so cross-node links dead-end in the web viewer.
Pre-existing (verified against a descendant link before this change) and
explicitly out of scope here.

## Verification

```
python -m pytest tests/test_qualified_ref.py tests/test_refs.py -q
python -m pytest -q
```

Plus the manual two-node reproduction from the spec: build parent/child nodes,
add the upward epic link, confirm `tcw validate` is clean from the child and
`tcw work show <parent-id>/<slug>` works from the child.

## Lifecycle

`tcw work start` before phase 1's first edit, committed on its own after this
plan is checkpointed.
