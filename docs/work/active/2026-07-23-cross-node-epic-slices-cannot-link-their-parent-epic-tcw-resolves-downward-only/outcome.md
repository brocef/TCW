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

## Follow-up notes

**Recommend filing as a backlog item** (the plan's phase 5): `resolve_tcw_ref`
returns a **bare** SPA key for the `tcw://W/<proj>/<slug>` spelling
(`tcw/refs.py:117` — `parsed.namespace` is empty for that form) and never reaches
the `include_descendants` hosting gate at `tcw/refs.py:109`, which only guards the
`tcw://<ns>/W/<slug>` spelling. So a cross-node work link resolves `ok` but
dead-ends in the web viewer, which looks the slug up locally.

Verified **pre-existing**: it reproduces for a *descendant* link on the code
before this change, so this item did not introduce it. `tcw validate` only
inspects `.ok`, which is why it stayed hidden. A real fix means deciding whether
`resolve_tcw_ref`'s `ok` means "resolves in the graph" (validate's question) or
"the viewer can open it" (serve's question) — they are different questions
currently sharing one flag, and separating them is a design change, not a bug fix.

Also worth noting for whoever picks that up: `parse_tcw_uri`'s first-bare-axis-wins
rule is what makes the two spellings behave differently. Documenting one canonical
spelling would prevent the next instance of this confusion.
