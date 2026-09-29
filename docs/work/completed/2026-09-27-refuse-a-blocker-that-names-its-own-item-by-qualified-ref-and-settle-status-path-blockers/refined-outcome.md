# Refined outcome — Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–5 met by tests and hands-on runs in a
  scratch node `pa` — own-id and status-path self-references refused, both
  forms recorded as `slug:`, including after the item was completed and only
  its tombstone was left; cycles refused; other qualifiers stay text; removal
  works by every form that adds.
- Full suite after the review fixes (started after `e87de26e`), from the item
  worktree with its private virtual environment: **4783 passed, 2 failed, 3
  skipped**. The two failures —
  `test_check_versions.py::test_a_hanging_cli_is_abandoned_silently[hangs and
  ignores TERM]` and `test_capabilities_federation.py::test_federation_stays_linear_in_chain_depth`
  — are timing tests run under a load average above 50 from parallel suites;
  both passed rerun alone on the same code (3 passed). Neither touches
  blockers. Criterion 6 is accepted on that basis.
- Hands-on (mine): `--blocked-by pa/<self>` exits 1 ("an item cannot block
  itself"); `--blocked-by backlog/<a>` records `slug: <a>`;
  `--unblocked-by pa/<a>` removes it.

## Accepted deviations from the spec

- The design was amended at review to the names built (`_local_forms`), and
  widened: removal accepts the same forms; re-adding an item held as old text
  replaces the text; a stale status path still names the local item; the web
  app's full-list save rewrites old text entries (documented in Risks).

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `docs/guide/work.md`, `skills/work/references/commands.md`,
  changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: `2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes`.
