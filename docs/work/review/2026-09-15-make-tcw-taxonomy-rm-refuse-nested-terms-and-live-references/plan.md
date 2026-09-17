# Plan: Make tcw taxonomy rm refuse nested terms and live references

Sequential, on `main`. Code edits only while no suite run is in progress.

## Task 1 — failing tests

Modify `tests/test_taxonomy.py`, `# ── rm ──` section, using its `node` and
`write_term` helpers:

- `test_rm_refuses_nested_terms` (criterion 1, store and CLI exit code/stderr);
- `test_rm_refuses_a_relatesto_referrer` (2);
- `test_rm_refuses_a_vocabulary_referrer` (3);
- `test_rm_is_not_refused_by_a_same_leaf_ref_elsewhere` (4);
- `test_rm_ignores_a_self_reference` (5);
- `test_rm_refuses_a_case_variant_spelling` (6), `pytest.skip` when the tmp
  filesystem is case-sensitive.

Run: criteria 1-3 and 6 fail today; 4, 5, 7 pass today and are kept as guards
(mutation-checked in Task 2).

## Task 2 — the refusal

- Modify `tcw/store/fs.py` `FsTaxonomyStore.remove` per the spec's design, with a
  private `_referrers(self, target: Path) -> list[str]` beside it modelled on
  `FsCapabilitiesStore._referrers`; delete `relators`.
- Modify `tcw/store/base.py` `TaxonomyStore.remove` docstring.
- Modify `tcw/taxonomy/cli.py` `_rm`: drop the `relators` lookup and warning.
- Proof: `pytest tests/test_taxonomy.py tests/test_non_git_writes.py`; mutation
  checks — remove each refusal and the identity comparison in turn and watch the
  matching test go red.

## Task 3 — full suite (`pytest -q`).

## Documentation Sync

- `README.md` [Public-API] — `:300` row "removes a local entry" → add "refused
  while terms are nested under it or reference it".
- `docs/release-notes/upcoming.md` [Public-API] — fires: behaviour change to a
  shipped command, stated as such.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — fires: `Changed`.
- `skills/taxonomy/SKILL.md` [Skill-Driven-Component] — fires: the `rm` row
  (`:117`) says what refuses.
- `docs/guide/taxonomy-and-capabilities.md` — not a configured entry; check for an
  `rm` description and match.
- `tests/cli/scenarios/08-taxonomy-and-capabilities.md` assertion 7 — describes rm;
  add the nested refusal.
- Capability `taxonomy/remove-a-local-term` — rewrite its last sentence; declare
  under `changed:` in this item's `capabilities.yaml`.
- Follow-up item: refuse (or report) capability `Subject`/`Feature` references on
  `taxonomy rm`.

## Verification

Hands-on in a scratch project: the three refusals and a clean removal through the
installed CLI, then `tcw taxonomy check`.
