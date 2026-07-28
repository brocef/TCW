# Outcome: Drop commit hash ranges from changelog entries

All seven planned tasks shipped in plan order, one commit each, plus the
documentation pass and one spec correction. Prose and one Python string; no
`tcw` behavior changed.

## What shipped

| Task | Commit | What landed |
| --- | --- | --- |
| T1 | `d17ee2c` | `## Changelog Entry Format` deleted in full from `skills/documentation-sync/references/release-notes-and-changelogs.md` — the `<changes starting-hash= ending-hash=>` wrapper, the `git rev-parse` / `git log --oneline` recipe, and the "Skip hash wrappers" escape hatch. Entry *content* guidance in the preceding section untouched. |
| T2 | `be5b2c5` | The recommended Documentation Sync entry set to `` - `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog; technical, grouped by category `` in both copies (`SKILL.md:30`, `release-notes-and-changelogs.md`). |
| T3 | `9e5f7c3` | `skills/documentation-sync/SKILL.md:18` — the commit-range clause dropped; the shape-drift reason and the `verify` conclusion kept. |
| T4 | `6475fb4` | `references/cut-version.md` — fold step 5 ("Extend the commit-hash ranges") and its Common Mistakes row deleted; steps renumbered to a contiguous `1.`–`6.` |
| T5 | `d3a63c7` | `skills/tcw-work/references/stage-implement.md` step 6 — same clause dropped; all three imperatives verbatim. |
| T6 | `0164646` | `scripts/cut_version.py` — `UPCOMING["docs/changelogs/upcoming.md"]` header template loses its hash clause. Only shipped-code site. |
| T7 | `fd84f54` | `AGENTS.md:65` (and `CLAUDE.md`, its symlink) drops the trailing clause; `docs/changelogs/upcoming.md`'s header paragraph matched to T6's template. No changelog entry touched. |
| Docs | `99a40a7` | `docs/changelogs/upcoming.md` (`## Removed` + `## Changed`) and `docs/release-notes/upcoming.md`. |
| Spec fix | `4b6d70a` | AC1 corrected — see below. |

## Tests

`python -m pytest -q` → **1062 passed** in 151.96s, including
`tests/test_cut_version.py` (5 passed, run separately at T6) and
`tests/test_plugin_manifests.py`. AC8 met.

## What the spec got wrong

**AC1's expected hit count.** The spec asserted the acceptance grep would return
exactly one hit (`skills/tcw-post-mortem/SKILL.md:36`). It returns two. The
second is `docs/changelogs/upcoming.md:71` — `` Commit range: `24f4bc6..0886943`. ``,
the trailing footer of a pending changelog entry written under the old rule in
commit `3633c30`, before this item's spec.

Root cause: the site-inventory grep recorded in the spec's Notes searched the
case-sensitive pattern `commit range`, which does not match `Commit range:`.
AC1's own grep is `-i` and catches it.

Resolution: **the line stays.** It is entry content below the first `##` heading,
which the spec's Non-goals ("the pending entries in `docs/changelogs/upcoming.md`
keep the hashes they already carry") and AC3 both protect. AC1 was corrected in
`spec.md` (`4b6d70a`) to name both hits as out of scope. No instruction prose is
involved, so nothing about the work changed — only the criterion's wording.

## Acceptance criteria

| AC | Result |
| --- | --- |
| 1 | **Met as corrected.** Two hits, both out-of-scope non-goals (above). No skill teaches the requirement. |
| 2 | **Met.** `git diff --stat` over the item lists 7 files; no `docs/changelogs/v*.md`. |
| 3 | **Met.** `` (`hash`) `` suffix count in `upcoming.md` is 12 before and after; the only changed line is line 4, in the header paragraph. |
| 4 | **Met.** Verified by importing `cut_version.UPCOMING` and comparing against the live header — byte-identical after stripping. Re-run after the doc pass. |
| 5 | **Met.** Read back in full: step 6 still states all three imperatives, and `SKILL.md:18` keeps the shape-drift reason and the `verify` conclusion. |
| 6 | **Met.** `grep -n "^[0-9]\."` on `cut-version.md` gives `1.`–`6.` with no gap; no commit-range row in Common Mistakes. `grep -rn "[Ss]tep [0-9]" skills/` surfaces only `## Step 0-4` headings and `stage-implement.md` step 6 — no reference to a fold step number. |
| 7 | **Met.** Both template lines present and byte-identical (count checked at 2 before `sort -u`). |
| 8 | **Met.** 1062 passed. |

## Documentation Sync

Evaluated once over the finished diff, per `stage-implement.md` step 6.

| Entry | Trigger | Fired |
| --- | --- | --- |
| `README.md` | `Public-API` | **No.** CLI surface unchanged; README's only related line (`842`) is a generic mention of the skill, not the requirement. |
| `docs/release-notes/upcoming.md` | `Public-API` | **Yes** — D1 written. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **Yes** — D2 written under `## Removed` and `## Changed`. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **Yes, answered by T1–T5.** D3 re-check: the AC1 grep over the finished diff finds no driving skill still teaching the requirement. |

The changelog entry for this item carries **no commit range** — the first entry
written under the new rule.

## Review

One round of `bllm-review-many` (`qwen25`, `gemma4`) over `5e997d4..HEAD` with a
context document. `gemma4` concluded "the diff looks solid, no blocking issues
found" (then degenerated into a repetition loop, so its output is truncated).
`qwen25` raised two "blocking" items that misread the diff direction — it quoted
the *pre-change* sentences as current and proposed exactly the replacement text
already applied — and one non-blocking claim that a Common Mistakes row still
referenced a renumbered step, in a row this change deletes. All three are
artifacts of the review, not defects. Its remaining notes (changelog/release-note
overlap; add a guard test; write a downstream migration note) are either
by-design separation of audiences or explicit spec non-goals.

## Notes

- No capability delta, per the spec — `tcw capabilities list` has no
  documentation-sync entry, so no contradiction detection was run.
- The plugin cache still ships the pre-change `documentation-sync` skill
  (`~/.claude/plugins/cache/tcw/tcw/0.15.3/`); the repo is the source of truth
  and the cache refreshes on the next plugin update.
- No blockers were declared or encountered.
