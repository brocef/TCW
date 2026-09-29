# Outcome — Check capability overrides for taxonomy references in capabilities check and taxonomy rm

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `3c653549` | Tests, then `FsCapabilitiesStore._override_fields` / `_set_fields`, the override branch of `check`, and `FsTaxonomyStore._capability_referrers` walking overrides. |
| docs | `40ce862d` | `skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md`, changelog and release-note entry files. |

## Tests

- `tests/test_override_references.py`, 8 tests: a dangling `Feature` and
  `Subject` in an override reported; a dangling `Blocked by` reported; `null`
  clears reporting nothing; a real term reporting nothing; `rm` refused for a
  term an override names in `Subject` and in `Feature` (store and CLI); another
  term not blocking; a malformed override refusing the removal readably.
- Mutation-checked: keeping `null` values in `_set_fields` turns the clearing
  test red. Moving the override walk outside the `try` does **not** turn the
  malformed-override test red: `list_all(local_only=True)` already parses every
  meta folder, overrides included, inside the same `try`, so the malformed file
  is caught before the walk. The walk sits inside the `try` as a safeguard.
- Full suite (`pytest -q -n 6`): 4768 passed, 3 skipped, exit 0.
- Hands-on: see `refined-outcome.md`.

## What the plan or spec got wrong

- **The spec's scope grew by its own sweep, as it said it would:** an override's
  `Blocked by`, `Superseded by`, `Roles` and `When` were equally unchecked, and
  the same `_ref_problems` call covers them.
- **The first draft of the code duplicated the field filter** in `check` and put
  the override walk outside the refusal's `try`; both corrected before commit
  (`_set_fields` is the one definition).

## Autonomous decisions

- No advisor consult: no open question; the scope choice (all references, not
  only `Subject`/`Feature`) followed from the sweep the spec stage requires.
- Review: see `refined-outcome.md`.
