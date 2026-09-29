# Refined outcome — Tidy three tracker messages left by the binding hardening review

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–5 met, each by its test and by printing
  the real messages; for criterion 1 it compared the hint under the old and new
  path readers in four layouts (the old one missed three).
- Full suite after the review fixes (started after `63ba5843`), from the item
  worktree with its private virtual environment: **4810 passed, 2 failed, 3
  skipped**. Both failures are
  `test_check_versions.py::test_a_hanging_cli_is_abandoned_silently`, a timing
  test run under a load average above 50 from parallel suites; it passed rerun
  alone, by me and by the verifier. Criterion 6 accepted on that basis.
- After the suite, one verify fold-in (`8ee57b11`): `FsTaxonomyStore.remove`'s
  `ls-files -z` decodes like the other four readers — a one-argument change;
  `tests/test_taxonomy_rm_gaps.py` and the item's own tests pass (25).
- Hands-on (mine): limited to the tests — every tracker path here needs a
  tracker, and the fake transport the tests use is the only one available in
  this run.

## Accepted deviations from the spec

- The review widened criterion 1's fix: `_tracked_source` and (at verify)
  `remove` read git paths the same way; all decode with `surrogateescape`.
- `ever_bound` is removed rather than kept as a wrapper.
- A `tracker.yaml` that is valid UTF-8 but fails to parse now refuses a strict
  drop as "cannot be read" rather than "is, or was, bound".
- The bound-item wording now leads with the slug in both CLI and web.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `docs/guide/jira.md`, changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed. Recorded, not filed: a `create_issue` answer that is
  not JSON still says "not JSON" rather than "may exist"; `apply_transition` and
  `add_comment` raise "unexpected shape" after a POST that may have taken effect.
