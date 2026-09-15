# Outcome — Graph-wide `<project-id>/<slug>` resolution

Work completed successfully. Route 1 + route 3 as decided. The whole defect
reduced to a single narrowing at `tcw/store/fs.py:217`, so one guard fixed CLI
addressing, `tcw validate`, and `tcw serve` together.

## What changed

### `tcw/store/fs.py`

- `resolve_qualified_work_ref` looks the qualifier up with
  `FsProjectRegistry.get(qualifier)` over the whole registered graph instead of a
  `descendants()`-only table. Nothing else in the function moved: the bare-slug
  path, the status-path locator, the `docs/work` existence check and the
  slug-never-contains-`/` split are untouched.
- Rewrote the docstring's stale path-containment prose. It claimed the qualifier
  had to be "genuinely inside `anchor`" and described traversal / `.git` /
  `.worktrees` escapes as path checks; the implementation already keyed on
  canonical registry IDs, and those qualifiers fail because they are not IDs in
  the graph. The docstring now states the real rule and why the direction
  restriction was wrong.
- New `qualified_work_ref_problem(anchor, ref)` — the route-3 message. Returns
  `no such project in this graph: <id>`, `<id> has no work component`, or the
  generic `no such work item: <ref>`. Cold path only (callers use it after a
  `None`), and its registry open is wrapped in `try` so `resolve_tcw_ref` keeps
  its contractual never-raises guarantee.

### `tcw/work/cli.py`, `tcw/refs.py`

Both printing callers now route their failure message through
`qualified_work_ref_problem` — one helper, no duplicated three-way branch.
`_resolve`'s docstring updated from "descendant node" to "any node in the
registered graph".

`include_descendants` was deliberately **not** touched anywhere:
`tcw work list -i` and `tcw serve` aggregation stay descendant-only.

### Tests

`tests/test_qualified_ref.py` — added upward (child → parent), sibling, and deep
upward (grandchild → root) resolution, plus a `qualified_work_ref_problem`
message test. The four pre-existing guard tests (unregistered ID, path
qualifier, `..`, absolute) pass **unchanged**, which is the regression that
matters.

`tests/test_refs.py` — `test_resolve_parent_work_from_child` uses the exact
`tcw://W/<project-id>/<slug>` spelling from issue #7, and
`test_resolve_unregistered_project_names_the_cause` pins the new message.
`test_resolve_descendant_work_needs_include` is unchanged.

`tests/test_validate.py` — `test_upward_epic_link_validates` builds a reciprocal
parent/child pair and asserts the child validates clean with the epic back-link;
`test_link_to_unregistered_project_names_the_cause` pins the message. The local
`node()` helper gained an optional `project_id` parameter (the two nodes need
distinct IDs).

`tests/test_work.py` — added
`test_parent_qualified_slug_addressable_from_child`.
`test_unresolvable_qualifier_errors_with_qualified_slug` asserted the old
misleading message and was renamed/retargeted to
`test_unresolvable_qualifier_names_the_unregistered_project`.

### Documentation

`README.md` (a new paragraph after the qualified-slug section: graph-wide in any
direction, still registered-only, and the explicit note that `list -i` / `serve`
stay descendant-only), `skills/tcw-work/SKILL.md` (the addressing and prose-
reference quick-reference rows), `skills/tcw-work/references/cross-node-epic.md`
(step 2 now shows the epic back-link line and its viewer caveat),
`docs/changelogs/upcoming.md` (Fixed + Changed, `c999f70..HEAD`),
`docs/release-notes/upcoming.md` (plain-language section with both caveats).

## Verification

- `python -m pytest -q` → **698 passed** (full suite).
- `tcw validate` on this repo → OK.
- The exact issue #7 reproduction, in a throwaway reciprocal two-node graph:
  - child's `initial-request.md` links `tcw://W/parent-proj/<epic-slug>` →
    `tcw validate` **OK** from the child (was:
    `no work item: parent-proj/<epic-slug>`);
  - parent → child link still validates;
  - `tcw work show parent-proj/<epic-slug>` from the child prints the parent's
    epic;
  - `tcw work show ghost/whatever` → `no such project in this graph: ghost`,
    exit 1.

All seven spec acceptance criteria met.

## Deviations from plan

None material. Plan step 1.3 asked which way `<own-id>/<slug>` went: the registry
caches the anchor's own config first, so `registry.get` returns it and a
self-qualified ref resolves to the local store.

## Follow-up: the SPA dead-end (now fixed in-scope)

The plan's phase 5 flagged a pre-existing defect: `resolve_tcw_ref` returned a
**bare** SPA key for the `tcw://W/<proj>/<slug>` spelling and bypassed the hosting
gate, so a cross-node link resolved `ok` and then dead-ended in the web viewer.
At the user's direction (2026-07-23) this was fixed here rather than deferred.

The fix separates the two questions that were sharing `ResolveResult.ok`:

- **Does the ref resolve in the registered graph?** — validate's question, and all
  `ok` now answers. `resolve_tcw_ref` returns the same qualified key for both
  spellings and reports the owning project in a new `ResolveResult.project` field
  (empty when local). It lost its `include_descendants` parameter — resolution is
  no longer viewer-aware.
- **Can *this* viewer open it?** — serve's question, so the gate moved to
  `tcw serve`'s `/api/resolve`, which consults a new `_hosted_projects()` (the
  descendants it aggregates) and returns `ok:false` for an unhostable
  ancestor/foreign ref. The SPA already renders a non-`ok` link inert, so an
  upward link now shows as plain text instead of a dead link. No client change
  was needed — the `/api/resolve` JSON shape (`{ok, axis?, key?}`) is unchanged;
  `project` is server-internal.

Verified end-to-end against the throwaway graph: both spellings resolve upward
and report `project`; the child's aggregating server reports the upward link
`ok:false`; the parent's server still hosts the downward link. New tests:
`test_resolve_foreign_work_resolves_and_reports_project`,
`test_resolve_local_work_reports_no_project` (test_refs), and
`test_resolve_ancestor_work_is_unhosted` (test_serve_resolve).
`test_resolve_descendant_work_gated` was rewritten to the new contract
(resolution succeeds; the *server* gates).

Web client TS tests were **not run** — this checkout has no web build tooling
(`package.json`/`node_modules` absent). The client contract is unchanged, so no
client test is affected, but this was not executed here.

Remaining note for a future cleanup (not a bug): `parse_tcw_uri`'s
first-bare-axis-wins rule is why the two spellings parse differently in the first
place. Documenting one canonical spelling would prevent the confusion recurring.
