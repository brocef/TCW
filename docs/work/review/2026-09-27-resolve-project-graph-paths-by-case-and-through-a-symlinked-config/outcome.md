# Outcome — Resolve project-graph paths regardless of letter case and through a symlinked config

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `6e0a684b` | Tests, then in `tcw/store/project.py`: `_config_file` (folder resolved, config file not followed), `FsProjectRegistry._canonical` (one key per folder identity, first spelling kept) at every config-path site, and `_probe_worktree` reading a submodule repository's `core.worktree` and falling back to the superproject's anchors. |
| docs | `5ddb395e` | `docs/guide/multi-repo.md` (worktree section, override sentence, one-folder rule), changelog and release-note entry files. |
| review | `0ff05c56` | `_reconcile_overrides` compares through `_canonical`; no inode numbers → text keys; the submodule layout is one shared test helper and its test asserts a clean validate. |

Follow-up filed on `bug-run` (`e61d4cb6`):
`2026-09-29-warn-when-a-project-override-names-the-primary-checkout-s-copy-from-a-linked-worktree`.

## Tests

- `tests/test_project_graph_paths.py`, 5 tests: a locator in other letter case
  and an override in other letter case (both skipped on a case-sensitive disk);
  a symlinked config with a child; a submodule node inside a linked worktree; a
  linked worktree of a submodule repository.
- All four original tests failed on the code before the fix, for the intended
  reasons. Mutation-checked: dropping the spelling map, following the config
  symlink, dropping the superproject fallback, dropping the `core.worktree`
  read, and the review's override comparison each turn their test red.
- **A test proved nothing at first**: the submodule-in-worktree test stayed
  green with the superproject fallback removed, because (a) `git worktree list`
  reports a submodule's git directory as its main worktree, giving wrong but
  harmless anchors, and (b) the layout declared an invalid `lib-too`, so the
  test could only assert "no duplicate". The probe was rewritten on
  `core.worktree` and the layout made valid; it now fails without the fallback.
- Full suite before review: 4835 passed, 3 skipped. After: see
  `refined-outcome.md`.

## What the plan or spec got wrong

- **The spec's probe design (`git worktree list`) was wrong for submodules**;
  amended at implement.
- **`_reconcile_overrides` was missed by the sweep** (it builds a path from the
  override's text); found by review.
- **The case rule holds per folder**: a descendant keeps the spelling of the
  locator that reached it. Unchanged from before and outside this item.

## Autonomous decisions

- **Question 3 — redirect a `TCW_PROJECT_<ID>` override to the linked
  worktree's copy?** Codex: keep it as stated; rule 0 is documented as the
  most specific answer and stops the lower rungs, and redirecting changes the
  branch read. Opus: redirect; my brief's claimed cost was wrong — for a
  sibling the override applies to every reference, so nothing loads twice and
  the graph silently mixes two branches. Chose to keep the documented contract
  (an explicit statement should not be second-guessed, and redirecting is the
  larger behavior change), state it in the guide, and file a follow-up to warn
  in exactly Opus's case. This is a split I would have asked the user about.
- Review (adversarial-code-reviewer, "merge after the fix"): accepted the
  override comparison, the test layout, the spec text and the shared helper;
  took the cheap inode-0 guard it listed as separate. Left, not filed: a
  descendant keeping an off-case spelling; linked worktrees of a
  `--separate-git-dir` repository (unchanged from before).
