# Refined outcome — Honor the configured work.path at every work-store call site

**Decision: accepted.** Approved by the user on 2026-08-13 after review of the
per-criterion assessment.

## Evidence at acceptance

All ten acceptance criteria in `spec.md` were met, each pinned by a test rather
than by inspection. Criteria 1-4 by the discovery and inbox-routing tests,
criterion 5 by the external reconcile test (which reproduced the original
`CalledProcessError` before the fix), criterion 6 by the parameterized drift test
(which reproduced the predicted no-decoy/decoy split), criteria 7 and 7b by the
split-repository and default-layout worktree tests, criterion 8 by the two
monkeypatched failure boundaries, criterion 9 by the full suite, and criterion 10
by the classification table in `outcome.md`.

Verified on merged `main`, not only on the branch:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 1250 passed |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate` | `validate OK` |
| `git status --short` | clean |

The two-repository smoke fixture behaved exactly as specified: both repositories
clean, `.gitignore` committed only in the code repository, item state only in the
store repository, no phantom `<node>/docs/work`, and neither commit carrying an
unrelated file.

## Capability reconciliation

`capabilities.yaml` declares `changed:` only — no `new:` entry to flip, so no
status transitions were required. All five declared paths resolve and their
descriptions were rewritten for the configuration-aware behavior in `36b7218`.
`tcw capabilities check` and `tcw capabilities drift` both pass on merged `main`.

## Closeout

- **Route: merge.** The shared branch
  `work/2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`
  was merged into `main` by hand with `-c merge.directoryRenames=true`, then
  completed with `--already-integrated`. The manual merge was necessary because
  the defect that would have blocked TCW's own merge-back is fixed *on that same
  branch*, and the `tcw` on PATH still resolved to the pre-merge primary checkout.
- Documentation was already current at acceptance: implementation's documentation
  gate ran over the finished diff, updating `README.md`, both `upcoming.md` working
  files, three skill documents, and all five capability descriptions.

## Follow-ups

- `2026-08-13-confirm-directory-renames-during-the-worktree-merge-back` — filed,
  planned, and implemented during this item's review, on this item's own branch.
  It is the reason this closeout needed a manual merge.
- **Unfiled:** `reconcile --commit` raises an uncaught
  `subprocess.CalledProcessError` because `git_commit` is absent from
  `tcw/work/cli.py`'s `_ERRORS`. Found while assessing criterion 8; deliberately
  out of scope. Still needs an item.

## Notes

The single most useful thing this item produced beyond the fix is the settled
answer in `spec.md` on `_has_work_store` strictness — an open question the spec
explicitly refused to let fall out of the implementation, decided as **strict**
with `tcw work init` named as the repair.
