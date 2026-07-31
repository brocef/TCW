# Plan

1. Add focused taxonomy-store tests for a three-project inheritance chain and a
   diamond. Cover list, search, canonical qualified lookup, bare lookup,
   ambiguity, deduplication, detail reads, validation resources, local shadowing,
   and cycle regression. Verify with the focused taxonomy test module.
2. Add a flattened inherited-owner projection to `FsTaxonomyStore` and route all
   inherited read and owner-resolution paths through it while retaining direct
   `extends` declarations for writes and cycle checks. Verify with the focused
   tests, then the full Python suite.
3. Reconcile the standing product model: narrow the
   `taxonomy/federate-shared-vocabulary` gap without changing its `Partial`
   status, and update the Phase 2 roadmap note. Verify with
   `tcw taxonomy check`, `tcw capabilities check`, and `tcw validate`.
4. Complete Documentation Sync in one final pass:
   - Update `README.md` for the public transitive-inheritance behavior
     (`Public-API`).
   - Update `docs/release-notes/upcoming.md` in user-facing language
     (`Public-API`).
   - Update `docs/changelogs/upcoming.md` with the technical change
     (`Any-Code-Change`).
   - Update `skills/tcw-taxonomy/SKILL.md` so the driving skill teaches the new
     inheritance semantics (`Skill-Driven-Component`).
   Verify documentation claims against the final implementation and run
   `git diff --check`.
5. Run the full verification gate: Python tests, taxonomy and capability checks,
   node-wide validation, and whitespace validation. Write `outcome.md`, submit
   the item for review, and stop for user verification before closeout.

## Verification

The automated suite will cover graph shapes and read paths. Manual verification
will inspect CLI `list`, `show`, and `search` output in a temporary A → B → C
fixture to confirm that the namespace shown to users is the source project ID,
not an inheritance route. Closeout will also confirm that remote sources and
version pinning remain accurately documented as unsupported.
