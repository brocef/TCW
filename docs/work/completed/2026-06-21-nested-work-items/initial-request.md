# Nested work items

## Product changes

- A caller can create a **child work item under any existing item** by passing the parent's slug: `tcw work new "<title>" --parent <slug>`. The child's folder is created **inside** the parent item's folder.
- `tcw work list` **nests children under their parents** in the board output.

## Technical changes

- Work item folders are identified by the presence of a **`state.yaml`** file (already the per-item marker) — this is how discovery finds every item regardless of nesting depth.
- Discovery must stop assuming one level deep. Today `_find` resolves `root/{status}/{slug}` and `query` does a single `iterdir()`; both must walk for `state.yaml` (e.g. `rglob`) and reconstruct the parent/child relation from directory nesting.
- Express parent/child as a **node relation** in the abstract vocabulary (litmus test passes — it belongs in the model); the FS adapter *derives* it from nesting, per AGENTS.md "Parent/child as literal directory ancestry … express the relation abstractly."

### Open questions for the spec
- How does a **status transition** (`git mv` of an item folder) behave when the item has children — do children move with the parent, or is nesting orthogonal to status?
- Slug **uniqueness/resolution** across the now-arbitrary tree.
- Relationship to the existing **node / epic / `--initiative`** concepts (cross-node recursion, Spec 2) — nesting is literal folder containment within one node, distinct from cross-node delegation; reconcile the two so they don't collide.

## Meta changes

- Update design doc `docs/plan/phase-5-work.md` in the same change.
- Documentation Sync: README (CLI usage), `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, and `skills/tcw-work/SKILL.md`.

Spec/plan to be written into this folder (`spec.md`, `plan.md`) at planning time.
