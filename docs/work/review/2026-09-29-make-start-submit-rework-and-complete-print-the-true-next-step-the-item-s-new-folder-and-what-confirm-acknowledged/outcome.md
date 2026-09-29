# Outcome

Covers GitHub #68, #67 and point 1 of #58. Everything shipped on
`work/<slug>`, one commit per plan task, plus two fixes found along the way.

## What shipped

| Task | Commit     | What |
| ---- | ---------- | ---- |
| 1    | `a96f7b01` | `TRANSITION_NEXT_STEPS`, `TRANSITION_LANDS_IN` and `start_next_stage` in `tcw/store/base.py`, beside `STAGE_NEXT_STEPS`. Guard tests in `tests/test_stage_verb.py`: every command named exists, no placeholder survives, every stage named is legal in the status the item lands in, and every transition that prints a hint has one. |
| 2    | `2a69692d` | `new` (epics included, which printed nothing before) and `inbox accept` point at the `request` gate. |
| 3    | `70a7d03e` | `start` points at the first stage the item still needs (`spec`, `plan`, `implement`, or `verify`), read once through `_present_artifacts` and shared with the unplanned-item warning. |
| 4    | `e80f7c8e` | `submit` and `rework` print the item's new folder (from `locate`, falling back to the status) and the `verify` / `implement` gate. The line telling the reader to delete a not-yet-written `refined-outcome.md` is gone. |
| 3 (fix) | `b7b420a2` | The qualified-slug start test in `tests/test_work.py`, missed in Task 3. |
| 5    | `adbd7f5f` | With `--confirm`, the Definition of Done prints ticked, under `Definition of Done — acknowledged with --confirm:`, only after the item has closed. A refusal on the way prints no checklist. Without `--confirm` nothing changes. |
| 6    | `a183bc07` | Guide, skills, and eight capability descriptions. |
| 6    | `85581005` | Changelog and release-note entries; the item's `capabilities.yaml`. |
| review fix | `24f870dd` | `_present_artifacts` returns `None` for an empty listing. `FsWorkStore.artifacts` answers `[]` when the folder vanishes mid-read, and a present item always lists every artifact, so `[]` means unreadable. Before, `start` would have pointed at `spec` and warned that spec and plan were missing; now it falls back to `implement` and warns about nothing, as the spec's Design says. Test first, watched fail (`set() is not None`). |

## Test result

Full suite, bare `pytest`, at `080c8e0b`, in a Claude Code cloud container:
**4905 passed, 9 skipped, 4 failed.** The four failures are the container's, not
this item's — the same four fail on untouched `origin/main` in the same container,
and none touches code this item changed:

- `tests/test_check_versions.py::test_a_hanging_cli_is_abandoned_silently`
  (both cases) and `::test_a_child_left_holding_the_output_does_not_delay_the_warning`
  — the abandoned `tcw` process is still alive when the test checks.
- `tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel` —
  `pip wheel --no-build-isolation` fails with the container's system build tools.

`tests/test_stage_verb.py`, which holds this item's guard tests and the new
unreadable-listing test, passes in full (61).

(At `85581005`, before the review fix: 4914 passed, 3 skipped.)

Other evidence gathered during implementation:

- Spec criterion 11's search finds nothing; `tcw validate` is OK.
- Every new test was mutation-checked by breaking what it covers and watching it
  fail for the right reason: an unfilled `{stage}` entry; `submit` naming
  `implement`, a stage not legal in `review`; the inbox hint removed; `start`
  hard-coded to `implement`; `submit` printing the bare status; the checklist
  printed up front again; `_present_artifacts` returning an empty set.
- One item walked by hand through new → start → submit → rework → submit →
  complete --confirm in a scratch project. Every printed gate command passed when
  run as printed, and every printed folder existed. A confirmed completion
  refused late (an unreconciled capability) printed no checklist.
- An adversarial spec review (three blocking findings, all accepted; see the
  spec's Notes) and an adversarial code review (verdict: merge, with the notes
  below).

## What the plan or spec got wrong

- **The spec's list of tests to update was incomplete.** It missed three in
  `tests/test_work.py`: the `new`/`start` hint test, the epic test, and the
  qualified-slug start test. All three were updated; the last only after the
  Task 3 commit (`b7b420a2`).
- **The Task 1 command-check test, as planned, checked the wrong text.** It ran
  the command pattern against hints with the slug already filled in, which the
  existing pattern cannot read, so it passed by matching nothing. It now runs
  against the unfilled text, where an unfilled `{stage}` makes it fail.
- **The spec's fallback to `implement` was implemented for errors only.** An
  empty artifact listing, which the filesystem store returns when the folder
  disappears mid-read, was read as "nothing written". Fixed in `24f870dd`.

## Notes

Two code-review findings, recorded here and deliberately not changed by this
item:

- **A qualified reference prints a folder relative to the child project.** For
  `kid/<slug>`, the folder printed by `start`, `submit`, `rework` and `complete`
  is relative to the child project, not to where the command ran. `start` and
  `complete` already behaved this way before this change; `submit` and `rework`
  now match them. It belongs with the backlog item
  `2026-09-29-make-a-stale-item-path-fail-loudly-complete-checks-for-the-verify-artifact-validate-finds-a-slug-under-two-statuses-and`,
  which is about paths that mislead; filed there as a triage note with the
  user's agreement.
- **`start_next_stage` says `verify` for an active item that already holds
  `refined-outcome.md`** (verified from `active`, then released and taken over).
  The work skill's "Finding your place" would say that item is ready to
  complete. Harmless — `verify` is legal there and its footer names
  `tcw work complete` — so it stays as a known difference.
