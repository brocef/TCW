# Refined outcome

Accepted 2026-10-16 under the TCW 3.0 epic's rule: a bounded adversarial
review stands in for the owner's verify (one round, one fix round, one
confirming round, then the owner decides). Landed on `epic/tcw-3.0` at
`a54f7086` (fast-forward from `e301bef5`).

## Review rounds

- **Review of Tasks 1-8** (three reviewers split by area): NOT DONE. Accepted
  and fixed in the fix round (`a0db5a98`..`aa6f94c5`): a note lost after a
  dropped connection when an older identical note exists (J1); the ssh-command
  read in the wrong repository (C4); `!!omap`/`!!pairs` lost by `config show`
  (P5); the viewer's item listing following links outside the item; the
  "never asks" wording; a test that could not fail; a skill rule that depended
  on the default procedure. The owner chose to add: T5 for single items, the
  Jira token on a redirect (also shipped as 2.8.3), `tcw provision` on an
  unparseable config, and `work new --project --stage`.
- **Confirming round**: viewer and docs half DONE; Jira, configuration and
  CLI half NOT DONE on one regression (an ssh command given on the git command
  line was no longer seen). The owner chose to have it and the four smaller
  points fixed without another review round (`1d4e2032`..`1c34dfe9`), each
  with a test that fails without its fix; checked by all of `tests/work` and
  `tests/serve` plus the standing guards: 2896 passed, 18 skipped.
- **Task 9 (J2)**: its own review, DONE; two of its test notes folded in
  (`a54f7086`).

## Left open

- The 101 probe tickets TCWTEST-86 to TCWTEST-186 are the owner's to delete
  (`project = TCWTEST AND summary ~ "\"J2 paging probe\""`); deleting
  tickets is permanent, so the agent did not.
- Not fixed, low priority (Task 9 review): a create whose answer is lost
  could make a 102nd probe on a quick rerun; the live test's clean-up stops
  on an error other than a permission refusal; recorded `created` stamps
  carry the account's `-0400` offset.
- `tests/test_prompt_fallback.py::test_an_unconfigured_project_sees_the_recorded_bytes[review]`
  still fails on the epic; its fixture predates TCW-74's "Who reviews"
  paragraph.
- For TCW-76: the guide's "Behavior that changed" section still needs the
  `work new --project --stage` refusal, the 401-after-a-redirect message and
  the non-UTF-8 `tcw-config.yaml` message; and the T5/T7 wording for
  `docs/capabilities/cli/validate-a-project/description.md` (in this item's
  report, carried into TCW-76).
- No GitHub issue: the item did not come from one.
