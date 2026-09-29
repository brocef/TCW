# Outcome — Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `c9d7fb01` | Tests, then `WorkStore._local_forms` (status path) and `FsWorkStore._local_forms` (own project id through `resolve_qualified_work_ref`, same store only), tried by `_entry_for`. |
| docs | `3675211f` | `docs/guide/work.md`, `skills/work/references/commands.md`, changelog and release-note entry files. |
| review | see log | `_without` matches the same forms; `_same_item` replaces an old text copy on re-add; own-id form limited to exactly two segments; spec and plan amended. |
| 4 | `65807662` (on `bug-run`) | Follow-up filed: `2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes`. |

## Tests

- `tests/test_local_qualified_blockers.py`, 16 tests: criteria 1–5, a stale
  status path, another qualifier naming a local slug; at review, removal by
  each form that adds, re-add replacing an old text entry, a folder path staying
  text, and a registered sibling's item with the same slug staying external.
- Mutation-checked: each review fix, reverted, turns its tests red (removal
  forms: 3; `_same_item`: 2; two-segment limit: 1; the same-store check: 1).
  Earlier, mutations stayed green until the stale-status and `vendor/<slug>`
  tests were added.
- Full suite: see `refined-outcome.md`.

## What the plan or spec got wrong

- **The design moved.** The spec stripped `<status>/` in `_normalize_ref` and
  added `_local_slug`; the code adds `_local_forms`, tried only by `_entry_for`.
  That left removal (`_without`, which uses `_normalize_ref`) unable to remove
  what the new forms added — found by review, fixed, spec amended.
- **Old text entries were not considered.** Re-adding kept both; the web app's
  full-list save rewrites them. Both are now stated in the spec's Design and
  Risks.

## Autonomous decisions

- No advisor consult: no open question at spec or plan.
- Review (adversarial-code-reviewer, "merge after fixes"): accepted 1–4 and the
  spec/plan divergence. Accepted the web app's rewrite of old entries as
  documented behavior rather than special-casing it: the entry it refuses is
  the self-reference this item exists to remove.
- Rejected for this change (separate, not filed as items): `--blocks` accepting
  the new forms (it refuses them cleanly, nothing is written); a note when the
  project registry fails to open and an own-id reference silently stays text
  (the pre-change behavior).
