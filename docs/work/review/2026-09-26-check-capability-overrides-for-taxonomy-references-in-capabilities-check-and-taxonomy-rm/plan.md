# Plan — Check capability overrides for taxonomy references

Worked in a `--worktree` branch from `bug-run`, tested with a private virtual
environment pointed at that worktree.

## Tasks

1. **Failing tests** — new `tests/test_override_references.py`, built on the
   helpers of `tests/test_capabilities_federation.py` (`child_of`, `write_cap`)
   with a local taxonomy added to the child (`init(["taxonomy"], child, …)` plus a
   `term()` helper as in `tests/test_taxonomy_rm_gaps.py`). One test per
   acceptance criterion 1–5. Proof: 1, 2 and 4 red today (check returns `[]`;
   remove succeeds); 3 and 5 pass today and are mutation-checked after task 2.
2. **Code** — `tcw/store/fs.py`: `FsCapabilitiesStore._override_fields`; the
   override branch of `check`; `FsTaxonomyStore._capability_referrers`.
   Proof: task 1 green; `tests/test_capabilities_federation.py`,
   `tests/test_taxonomy_rm_gaps.py`, `tests/test_capabilit*.py` green.
3. **Full suite** — `pytest -q -n 8`.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` — fires.
- `docs/release-notes/upcoming/<slug>.md` — fires (a `check` that newly fails
  on existing overrides is user-visible).
- `docs/guide/<topic>.md` — evaluate the taxonomy-and-capabilities guide's
  description of `check` and `rm`; fires only if it says what they cover in a
  way that excludes overrides.
- `skills/capabilities/SKILL.md`, `skills/taxonomy/SKILL.md` — evaluate the
  same way.
- `README.md`, `skills/configure/references/*` — do not fire.

## Verification

Re-run `repro3.py` against the worktree: `check()` names `ov`, and `remove`
refuses. Run `tcw capabilities check` and `tcw taxonomy rm zed` in that scratch
node with the worktree's CLI and read the messages.
