# Plan: Drop commit hash ranges from changelog entries

Seven prose/string sites, one commit each. Nothing here is sequencing-sensitive
in the usual sense — no task leaves the tree broken, and `pytest` is green at
every boundary because no shipped code path reads these strings. The order below
is chosen for *review* legibility instead: the skill's own mandate dies first
(T1-T3), then everything that only referred to it (T4-T6), then TCW's own
adoption of it (T7). Reviewing T4-T6 before T1 would mean reading references to
a rule still on the books.

The riskiest edits are T3 and T5 — the two sentences that also carry the
end-of-`implement` documentation gate's justification. They are isolated in their
own commits, with the surviving wording pinned by AC5, so a bad trim is visible
in a two-line diff rather than buried in a sweep.

## Tasks

### T1 — Delete the `## Changelog Entry Format` section

**Changes:** `skills/documentation-sync/references/release-notes-and-changelogs.md`
— remove lines 46-67 in their entirety: the wrapper mandate, the
`<changes starting-hash=… ending-hash=…>` example, the `git rev-parse --short
HEAD` / `git log --oneline` recipe, and the "**Skip hash wrappers**" escape
hatch. The escape hatch goes with the mandate; with nothing to escape from it is
an instruction about a rule the reader has never been given.

Leave the preceding section (lines 39-44 — "include everything", "reference file
paths", "group by category", "be specific enough…") untouched. That is entry
*content* guidance and survives the change.

**Verify:** `grep -n "Changelog Entry Format\|starting-hash\|ending-hash\|Skip hash wrappers" skills/documentation-sync/references/release-notes-and-changelogs.md`
is empty — the heading included, so a section emptied but left standing is
caught. The file's remaining headings read as a continuous document — no
orphaned intro sentence left pointing at the deleted section.

### T2 — Fix the recommended Documentation Sync entry in both templates

**Changes:** the sample entry line, in two places, to the identical text:

```markdown
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog; technical, grouped by category
```

- `skills/documentation-sync/references/release-notes-and-changelogs.md:75`
- `skills/documentation-sync/SKILL.md:30`

These are duplicated by design (router keeps the sample section inline, the
reference repeats it for readers who arrived there directly). Editing one and
not the other is the specific failure mode AC7 guards, so they change in one
commit rather than two.

**Verify:** AC7 — the two lines are byte-identical:

```bash
hits=$(grep -h "docs/changelogs/upcoming.md.*Any-Code-Change" \
  skills/documentation-sync/SKILL.md \
  skills/documentation-sync/references/release-notes-and-changelogs.md)
[ "$(echo "$hits" | wc -l)" -eq 2 ] &&
[ "$(echo "$hits" | sort -u | wc -l)" -eq 1 ] && echo "AC7 ok"
```

Both counts matter: `sort -u` alone reports `1` when one file lost its line
entirely, so the total is checked at 2 before the lines are compared.

### T3 — Repair the one-pass rationale in `documentation-sync/SKILL.md`

**Changes:** `skills/documentation-sync/SKILL.md:18` — drop only the clause "and
a changelog entry can't state its commit range until the range exists". The
sentence keeps its first reason (docs written mid-implementation describe a
shape the change no longer has by the time it lands) and its conclusion (`verify`
reviews code and docs together instead of accepting a diff whose docs are still
pending).

Do **not** delete the sentence or move the gate — the gate's placement is a
stated non-goal of the spec.

**Verify:** AC5, second half. The line still contains both the shape-drift reason
and the `verify` conclusion, and `git diff` for this commit shows a single line
changed.

### T4 — Delete fold step 5 and its Common Mistakes row in `cut-version.md`

**Changes:** `skills/documentation-sync/references/cut-version.md`

- Delete step 5 of "Folding into an unpushed version" (lines 133-135,
  "**Extend the commit-hash ranges.**").
- Renumber the remainder: `6. **Commit**` → `5.`, `7. **Re-tag at HEAD.**` → `6.`
- Delete the Common Mistakes row at line 163 ("Folding and leaving the old commit
  ranges in `v{version}.md`"). Its fix column instructs the step just deleted.

Nothing outside this list refers to the fold steps by number — the file's only
numbered cross-reference is to `Step 0` (line 157), a different list. Confirmed
by `grep -n "[Ss]tep [0-9]"` at spec time; re-run it as part of verification
rather than trusting the note.

**Verify:** AC6 — the fold list numbers `1.` through `6.` with no gap
(`grep -n "^[0-9]\." skills/documentation-sync/references/cut-version.md`), the
mistakes table has no commit-range row, and `grep -n "[Ss]tep [0-9]"` across
`skills/` surfaces no reference to a fold step number.

### T5 — Repair the step 6 rationale in `stage-implement.md`

**Changes:** `skills/tcw-work/references/stage-implement.md` step 6 (lines 45-51)
— drop "and a changelog entry cannot state its commit range until there is one".
The step's three imperatives stay verbatim: run only once every plan task is done
and the suite is green; evaluate every trigger in `AGENTS.md` against the finished
diff rather than the task just committed; commit doc updates separately from the
code. The paragraph below it naming step 6 as the lifecycle's documentation gate
is untouched.

**Verify:** AC5, first half — all three imperatives still present; `git diff` for
this commit is confined to step 6's prose.

### T6 — Drop the hash clause from the `cut_version.py` header template

**Changes:** `scripts/cut_version.py:33-36` —
`UPCOMING["docs/changelogs/upcoming.md"]` becomes:

```python
"# Upcoming\n\n"
"Developer changelog for the next version. Technical and precise; grouped by\n"
"category.\n"
```

This is the only shipped-code site. `tests/test_cut_version.py:79-80` asserts
`"# Upcoming" in fresh` and nothing about the body, so no test changes.

**Verify:** `pytest tests/test_cut_version.py` green (AC8's first half). Paired
with T7 by AC4, which is checked in the Verification section below once both have
landed.

### T7 — TCW's own adoption: `AGENTS.md` and the live `upcoming.md` header

**Changes:**

- `AGENTS.md:65` — drop the trailing clause, leaving
  `` - `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog for the next version; technical, grouped (Added/Changed/Fixed/Removed/Internal). ``
  `CLAUDE.md` is a symlink to `AGENTS.md`; one edit covers both.
- `docs/changelogs/upcoming.md` lines 3-4 — the header paragraph only, matched to
  T6's new template so a rotation does not silently rewrite it.

**Do not touch a single changelog entry.** Every existing `` (`hash`) `` suffix
in `upcoming.md` stays, and no `docs/changelogs/v*.md` file is opened. This is the
spec's hardest boundary (Non-goals, AC2, AC3) and this task is the only one with
an opportunity to cross it.

**Verify:** AC3 — the diff for `docs/changelogs/upcoming.md` touches only lines
above the first `##` heading:

```bash
git diff docs/changelogs/upcoming.md   # expect the header paragraph and nothing else
```

AC2 — `git diff --stat` for the whole item lists no `docs/changelogs/v*.md`.

## Documentation Sync

Evaluated against the four entries in `AGENTS.md`. Scheduled as one block at the
end, per `stage-implement.md` step 6 — implementation answers these in a single
pass over the finished diff, not task-by-task.

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | `Public-API` | **No.** The `tcw` CLI surface is unchanged and `README.md` has no hit for hashes or changelog format (grepped at spec time). |
| `docs/release-notes/upcoming.md` | `Public-API` | **Yes.** The shipped skill's instructions change for every project that adopts it — a user-visible rule they were following and now are not. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **Yes.** `scripts/cut_version.py` emits a different header (T6) — behavior-affecting, not cosmetic. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **Yes, and already answered by T1-T5** — the skills *are* what this item changes. D3 re-checks for a driving skill the code tasks missed. |

- **D1 — `docs/release-notes/upcoming.md`.** Plain language, no internal module
  names: changelog entries no longer need to carry the git commits they came
  from; existing entries keep the hashes they already have.
- **D2 — `docs/changelogs/upcoming.md`.** Under `Changed` / `Removed`: the
  `<changes>` wrapper mandate and its recipe removed from the
  `documentation-sync` skill; the fold procedure's range-extension step and its
  Common Mistakes row removed; `scripts/cut_version.py`'s header template and
  TCW's own Documentation Sync entry updated. **Write it without a commit hash
  range** — this item is the first entry under the new rule, and an entry that
  cites its own range would be the most conspicuous possible miss.
- **D3 — re-check `Skill-Driven-Component`.** Re-run the AC1 grep across
  `skills/` over the finished diff to confirm no driving skill still teaches the
  requirement, and that `skills/tcw-post-mortem/SKILL.md:36` is the only
  surviving hit.

## Verification

Beyond `pytest` (AC8), which cannot see any of this:

1. **AC1 — the requirement is gone.**
   ```bash
   grep -rniE "commit[- ]hash range|commit range|starting-hash|ending-hash" \
     skills/ scripts/ AGENTS.md docs/changelogs/upcoming.md
   ```
   Expect exactly one hit: `skills/tcw-post-mortem/SKILL.md:36`, which is about
   reading `git log` during a post-mortem and is an explicit non-goal.

2. **AC4 — template and live header agree.** Compare the string
   `scripts/cut_version.py` writes against the header now in
   `docs/changelogs/upcoming.md` (everything above the first `##`). They must be
   byte-identical, or the next `cut_version.py` run rewrites the header as a
   surprise diff. Import the value rather than parsing the source — the module is
   already imported this way by `tests/test_cut_version.py`, so the check is
   indifferent to how the string literal happens to be formatted:
   ```bash
   python - <<'PY'
   import pathlib, sys
   sys.path.insert(0, "scripts")
   import cut_version
   tpl = cut_version.UPCOMING["docs/changelogs/upcoming.md"]
   live = pathlib.Path("docs/changelogs/upcoming.md").read_text().split("\n##")[0]
   assert tpl.strip() == live.strip(), f"drift:\n{tpl!r}\n{live!r}"
   print("AC4 ok")
   PY
   ```

3. **AC2/AC3 — history untouched.** `git diff --stat` over the item's full range
   lists no `docs/changelogs/v*.md`, and the only `docs/changelogs/upcoming.md`
   lines changed are in the header paragraph. Every existing `` (`hash`) ``
   suffix survives.

4. **AC5 — the documentation gate survived the trim.** Read
   `skills/documentation-sync/SKILL.md:18` and `stage-implement.md` step 6 back
   in full. The gate must still be stated as: after every plan task and a green
   suite, one pass over the finished diff, doc commits separate from code. This
   is a human read, not a grep — the failure mode is a sentence that is
   *technically* still there but no longer argues for anything.

5. **AC6/AC7 — structural.** Fold list contiguously numbered `1.`-`6.`; the two
   recommended-entry lines identical (the `sort -u | wc -l` check in T2).

## Notes

- No blockers. Nothing in the backlog depends on this item and it depends on
  nothing, so no `tcw work edit --blocked-by` is needed.
- Every task is a self-contained commit; the suite is green at each boundary
  because no test reads any of the edited strings. T6 is the only task that
  touches Python, and the one assertion near it checks a substring this change
  preserves.
- Effort/complexity were set to `low`/`low` at creation and planning did not
  change that assessment — the volume is seven small edits, and the only judgment
  in the item is how much of two sentences to keep.
