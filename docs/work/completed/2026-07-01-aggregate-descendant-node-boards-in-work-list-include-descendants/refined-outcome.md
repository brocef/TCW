# Refined outcome — `tcw work list --include-descendants`

## Verification decision

Approved. User verified the multi-node smoke output (root + `Project-A` + `Project-B`
grouped under `# .` / `# ./Project-A` / `# ./Project-B`, non-node `plain-subdir` excluded)
and the 228-passing suite, and elected to complete the item.

## Refinements after initial implementation

None. The implementation was accepted as-is at verification. (The one substantive
mid-flight change — the `descendant_work_nodes` → `descendant_nodes` rename and the
decision to leave `child_nodes` alone / not add `ancestor_nodes()` — happened during
planning, not after implementation; see `outcome.md`.)

## Closeout choices (user-selected)

- **Version:** patch bump → **v0.7.2** cut and tagged via `scripts/cut_version.py patch`
  (5 version files bumped in lockstep; `docs/{changelogs,release-notes}/upcoming.md`
  rotated to `v0.7.2.md`; committed `9d317ae`; **not pushed** — publishing stays manual).
- **Follow-ups → backlog:** none created. The `child_nodes` clarity-rename idea
  (`child_repo_nodes()`) stays a note here, not a TCW item.
- **Capabilities:** `work#view-the-board` body reconciled to describe `--include-descendants`
  (status stays `Supported`); ledger `tcw capabilities check` clean.
- **Completion:** `tcw work complete --resolution done --confirm` — DoD acknowledged
  (tests pass, docs synced, capabilities reconciled, reviewed, version offered).

## Final verification evidence

- `python -m pytest -q` → 228 passed.
- `tests/test_plugin_manifests.py` → 4 passed (version agreement across all 5 files at v0.7.2).
- `git tag --points-at HEAD` → `v0.7.2`.

## Deferred (documented, not scheduled)

- `child_nodes` → `child_repo_nodes()` clarity rename (touches `recursion.py` + `cli.py`).
- `PermissionError` / discovery→render TOCTOU hardening in `descendant_nodes` (parity with
  `child_nodes`; non-states for a single-user repo — see `spec.md` Risks).
- Sibling backlog item `2026-07-01-accept-l-m-h-vh-shorthand-aliases-for-effort-complexity`
  remains in backlog, awaiting its own planning pass.

## Commits

`ee092d7` start · `a284df8` impl+tests · `6c95e00` docs-sync · `f574754` outcome ·
`e4867d2` complete+capability · `9d317ae` release v0.7.2.
