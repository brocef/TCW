# Outcome: Drop commit hash ranges from changelog entries

All seven planned tasks shipped in plan order, one commit each, plus the
documentation pass and one spec correction. Prose and one Python string; no
`tcw` behavior changed.

**A second pass followed** (`rework.md`). Verification accepted the seven tasks
and every acceptance criterion, then overrode two of the spec's Non-goals — the
pending changelog's hashes come out, and a migration guide ships. Nothing from
the first pass was reverted; see *Rework* below.

## What shipped (first pass)

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

## Rework (second pass)

Driven by `rework.md`, after the user overrode two Non-goals at the `verify`
gate. Both were scope expansions, not defects.

| Task | Commit | What landed |
| --- | --- | --- |
| — | `105ddbd` | `rework.md` — records the two overrides and what implementation still owed. |
| R3 | `026022e` | `spec.md` amended: Goals 4-6, the Non-goal split (released history stays hard, pending file moves into scope), AC1, AC3 inverted, AC9 added, Design sites 8-9, and the downstream-wrapper risk reclassified from accepted to mitigated. |
| R1 | `7393740` | Every commit hash stripped from `docs/changelogs/upcoming.md` — 12 per-entry `` (`hash`) `` suffixes and the `Commit range:` footer. Entry prose untouched; no `docs/changelogs/v*.md` opened. |
| R2 | `3acc6d6` | `docs/migration-guide-0.15.X-to-0.16.0.md`. |
| — | `3b01f03` | Doc pass for the rework scope: the guide under `## Added`, the hash strip under `## Changed`, release notes pointing at the guide. |
| R3b | `65bcf38` | AC3 made shape-specific — see below. |

**Why the migration guide needed no packaging work.** The plugin cache at
`~/.claude/plugins/cache/tcw/tcw/<version>/` contains the repository verbatim,
`docs/` included — verified by listing it. So a file in `docs/` is readable by
every plugin user with no manifest change.

**How the guide differs from its three predecessors.** They describe required
migrations (move files, run `tcw validate`, assign project IDs). This one
describes a *relaxation*: nothing breaks on upgrade and no action is required.
It leads with that and puts the cleanup under an explicit "Optional" heading,
per AC9. Writing it in the shape of its predecessors would have invented a
ritual for a non-event.

## Tests

`python -m pytest -q` → **1062 passed**, run at the end of each pass (151.96s,
then 152.59s), including `tests/test_cut_version.py` and
`tests/test_plugin_manifests.py`. `tcw validate` → `validate OK`. AC8 met.

## What the spec got wrong

**The acceptance criteria were self-referential, and it took two corrections to
see it.** A changelog entry that removes a requirement has to *name* the
requirement. Both AC1 and AC3 greped for the requirement's keywords over files
that include that entry, so each criterion matched its own description of the
work satisfying it. The defect was in the criteria, never in the change.

The sequence, recorded because the shape of the mistake is the useful part:

1. **AC1, written**, expected one hit over roots including
   `docs/changelogs/upcoming.md`.
2. **AC1, first correction** (`4b6d70a`) — it returned **two**. The spec's
   site-inventory grep (its Notes) used the case-sensitive pattern
   `commit range` and had missed `` Commit range: `24f4bc6..0886943`. `` at
   `docs/changelogs/upcoming.md:71`, the footer of an entry written under the old
   rule in commit `3633c30`. AC1's own grep is `-i` and caught it. Under the
   Non-goals then in force that line was untouchable, so the criterion widened to
   accommodate it, and implementation left the line alone.
3. **The `verify` gate deleted that footer** anyway (R1), which should have
   returned AC1 to one hit. It returned **three** — the two new hits being the
   `## Removed` entry naming `starting-hash` and `ending-hash` to say what was
   removed.
4. **AC1, second correction** (`7393740`): drop `docs/changelogs/upcoming.md`
   from the grep roots. The criterion is about *instruction surfaces* —
   `skills/`, `scripts/`, `AGENTS.md`. It now returns the single predicted hit,
   `skills/tcw-post-mortem/SKILL.md:36`.
5. **AC3, same defect** (`65bcf38`): its keyword grep for `Commit range:` matched
   the changelog entry describing the footer's deletion. Rewritten to be
   shape-specific — an attribution is a parenthesised 7-hex hash, or a footer at
   the *start* of a line. Prose about one is neither.

The general lesson, worth carrying to the next item of this kind: **an
acceptance criterion that greps for a keyword cannot be run over the document
that announces the keyword's removal.** Either exclude that document or match on
shape rather than vocabulary.

## Acceptance criteria

Final state, after both passes. Criteria marked *(rev.)* were amended mid-item;
each amendment is recorded in `spec.md` in place.

| AC | Result |
| --- | --- |
| 1 *(rev.)* | **Met.** `grep -rniE "commit[- ]hash range\|commit range\|starting-hash\|ending-hash" skills/ scripts/ AGENTS.md` → one hit, `skills/tcw-post-mortem/SKILL.md:36`, an explicit Non-goal. No shipped instruction teaches the requirement. |
| 2 | **Met.** `git diff --stat` over the item's full range lists no `docs/changelogs/v*.md`. Released history untouched. |
| 3 *(rev.)* | **Met.** Both shape-specific greps return nothing: no `` (`7hex`) `` attribution and no line-initial `Commit range:` footer. 12 suffixes plus 1 footer removed; entry prose unchanged. |
| 4 | **Met.** `cut_version.UPCOMING["docs/changelogs/upcoming.md"]` imported and compared to the live header — byte-identical after stripping. Re-checked after every subsequent edit to the file. |
| 5 | **Met.** Read back in full: step 6 still states all three imperatives, and `SKILL.md:18` keeps the shape-drift reason and the `verify` conclusion. |
| 6 | **Met.** `grep -n "^[0-9]\."` on `cut-version.md` gives `1.`–`6.` with no gap; no commit-range row in Common Mistakes. `grep -rn "[Ss]tep [0-9]" skills/` surfaces only `## Step 0-4` headings and `stage-implement.md` step 6 — no reference to a fold step number. |
| 7 | **Met.** Both template lines present and byte-identical (count checked at 2 before `sort -u`). |
| 8 | **Met.** 1062 passed, both passes. |
| 9 *(new)* | **Met.** `docs/migration-guide-0.15.X-to-0.16.0.md` follows the predecessors' naming and structure, and its third paragraph is "**There is nothing you have to do.**" The cleanup section is explicitly headed *Optional*. |

## Documentation Sync

Evaluated once over the finished diff, per `stage-implement.md` step 6.

| Entry | Trigger | Fired |
| --- | --- | --- |
| `README.md` | `Public-API` | **No.** CLI surface unchanged; README's only related line (`842`) is a generic mention of the skill, not the requirement. |
| `docs/release-notes/upcoming.md` | `Public-API` | **Yes** — D1 written. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **Yes** — D2 written under `## Removed` and `## Changed`. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **Yes, answered by T1–T5.** D3 re-check: the AC1 grep over the finished diff finds no driving skill still teaching the requirement. |

Re-run after the rework, since R1 and R2 changed documentation: `README.md` still
does not fire; the guide went into the changelog under `## Added` and the hash
strip under `## Changed`; the release notes now point at the guide and repeat
that it requires nothing. No skill changed in the second pass.

The changelog entry for this item carries **no commit range** — the first entry
written under the new rule, in a file that now carries none at all.

## Review

Two rounds of `bllm-review-many` (`qwen25`, `gemma4`), one per pass, each with a
context document.

**First pass** (`5e997d4..HEAD`). `gemma4` concluded "the diff looks solid, no
blocking issues found" (then degenerated into a repetition loop, truncating its
output). `qwen25` raised two "blocking" items that misread the diff direction —
it quoted the *pre-change* sentences as current and proposed exactly the
replacement text already applied — plus one non-blocking claim that a Common
Mistakes row still referenced a renumbered step, in a row this change deletes.
All three were review artifacts. Its remaining notes (changelog/release-note
overlap, add a guard test, write a downstream migration note) were by-design
audience separation or, at the time, spec Non-goals. **The migration-note
suggestion was independently raised to the user at the `verify` gate and became
R2.**

**Second pass** (`105ddbd..HEAD`). `qwen25` again flagged as blocking a change
the diff already contains ("AC3 needs updating to reflect this") while quoting
the updated AC3. `gemma4` flagged the `docs/work/review/` → `docs/work/active/`
rename as broken internal links — that rename *is* the status transition
(status is the folder), performed by `tcw work rework`. Checked anyway: no file
in the repository hardcodes a status-folder path to this item, and
`tcw validate` returns `validate OK`.

Dismissed from both rounds, with reasons: **add a guard test** that greps
`upcoming.md` for hashes — the item's own finding is that this requirement is
instruction-only and no code emits, validates, or reads these hashes; adding a
validator would contradict the design it just simplified. Noted as a candidate
follow-up rather than applied. **Rephrase the changelog to avoid naming
`starting-hash`/`ending-hash`** — an entry has to name what it removed; the
criteria were fixed instead. **Document the optional cleanup more clearly** — it
already carries an `rg` command and two stated positions.

## Notes

- No capability delta, per the spec — `tcw capabilities list` has no
  documentation-sync entry, so no contradiction detection was run.
- The plugin cache still ships the pre-change `documentation-sync` skill
  (`~/.claude/plugins/cache/tcw/tcw/0.15.3/`); the repo is the source of truth
  and the cache refreshes on the next plugin update. The same cache is what makes
  R2's placement work — it carries `docs/` verbatim.
- No blockers were declared or encountered.
- `docs/migration-guide-0.15.X-to-0.16.0.md` presupposes a **minor** bump at
  closeout, which is the user's stated choice. A different bump means renaming
  the file.
- Candidate follow-up, not filed: a guard test asserting `docs/changelogs/upcoming.md`
  carries no commit-hash attribution. Deliberately not added here — see *Review*.
