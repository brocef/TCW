# Outcome

## What shipped

| Plan task | Commit | What |
| --- | --- | --- |
| 1 | `7b1ca8cc` | `scripts/cut_version.py` combines `upcoming/` folders (`combine`, `combine_upcoming`; aborts on a missing folder before any change). Eight tests in `tests/test_cut_version.py`, written first and seen failing against the old script (`git mv` of a missing `upcoming.md`). Mutation check: replacing the heading order with first-appearance order turned `test_combine_merges_sections_by_heading` red on its heading-order assertion. |
| 2 | `5a051964` | This repo's two `upcoming.md` files moved to `upcoming/2026-09-27-carried-over.md` (title and preamble dropped, changelog `###` → `##`, entry lines unchanged per `git diff -M`); `upcoming/README.md` in each folder; `tcw-config.yaml` entries now `upcoming/<slug>.md`; `tests/test_repo_lifecycle.py` path list. |
| 3 | `32a61f82` | Shipped skill text: `release-notes-and-changelogs.md` (layout, one-file-per-change rules, folder cross-check, "A project still on a single `upcoming.md`" section, migration row, two Common Mistakes rows), `cut-version.md` (Step 2 combining rules, legacy rotation, fold steps 2 and 4), `SKILL.md` example entry, `documentation-sync` and `unattended-work` procedures, `configure/references/docs-sync.md`. |
| 4 | `c656b921` | `AGENTS.md` Versioning (and so `CLAUDE.md`, a link to it), release scenario 13 row 8, eval fixture comment, capability `skills/documentation-sync` story sentence, item `capabilities.yaml` (`changed:`). |
| 5 | `918e8a4f` | Documentation pass: `README.md` Releasing paragraph, `docs/guide/configuration.md` example entry plus one sentence that a path may be a `<slug>` pattern, and this item's own entries in `docs/{changelogs,release-notes}/upcoming/<slug>.md`. |

## Test result

- `pytest` run bare, after Task 4: **4756 passed, 3 skipped** (20m43s). Task 5
  changed only Markdown; the tests that read `README.md` and skill paths
  (`test_repo_lifecycle.py`, `test_skill_path_pointers.py`) were rerun after it:
  10 passed.
- `tcw validate` OK; `tcw capabilities check` OK; `tcw work docs` lists the two
  `upcoming/<slug>.md` entries.
- Verification from the plan: cloned the repo to a scratch folder and ran
  `python scripts/cut_version.py patch` there. It produced `v2.6.4.md` files
  titled `# v2.6.4` with the carried-over entries intact, left only `README.md`
  in each `upcoming/`, recorded the moves as renames in one release commit, tagged
  it, and left a clean tree. (That clone predates Task 5's entry files, so it
  exercised a single entry per folder; merging across files is covered by the
  unit tests.)

## Acceptance criteria

1 ✔ (Task 2) · 2 ✔ (`git diff -M` shows only title/preamble/heading level) ·
3 ✔ · 4, 5, 6 ✔ (unit tests) · 7 ✔ (every remaining hit is legacy-layout
guidance) · 8 ✔ · 9 ✔ · 10 ✔ · 11 ✔.

## What the plan or spec got wrong

- **The spec's first sibling sweep was incomplete.** It missed `README.md:889`,
  `docs/guide/configuration.md:212` and eval case B10 in `evals/evals.json`;
  found at `plan` and corrected in the spec (`a7ed9012`) before any code.
- **The plan listed `CLAUDE.md` and `AGENTS.md` as two files.** `CLAUDE.md` is a
  symbolic link to `AGENTS.md`, so one edit covers both.
- **"Suite green at every commit boundary" was run as targeted tests per commit
  and the full suite once**, after Task 4, because the full suite takes over 20
  minutes. The per-commit runs covered every test that reads a changed file.
- **Formatting:** of the edited Markdown files, only
  `release-notes-and-changelogs.md` and `docs/guide/configuration.md` were
  Prettier-clean beforehand; those two are clean now. The others (`SKILL.md`,
  both procedures, `configure/references/docs-sync.md`, `README.md`) were
  already failing Prettier and were left as they were — the backlog item
  `2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout` covers them.
- The Task 5 guide sentence about `<slug>` patterns was not in the plan; the
  guide's own paragraph on what `path` may be would otherwise have gone stale.

## Notes

- Nothing in `tcw/` Python changed; the entry format and its validation are
  untouched, as the spec intended.
- The next version cut in this repo will ship three entries per folder: the
  carried-over one and this item's, merged under shared headings.
