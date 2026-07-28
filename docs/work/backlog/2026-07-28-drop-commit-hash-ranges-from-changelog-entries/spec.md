# Spec: Drop commit hash ranges from changelog entries

## Capability changes

None. No capability in the ledger covers changelog authoring or the
`documentation-sync` skill's entry format — `tcw capabilities list` has no
documentation-sync entry, and the closest neighbours (`cli/scaffold-the-doc-trees`,
`cli/check-the-installed-version`) describe CLI behavior this item does not touch.
The requirement lives entirely in instruction prose, so there is no ledger delta
to plan and no taxonomy term to add.

## Problem

Every project that adopts the `documentation-sync` skill is told to wrap its
developer-changelog entries in a commit hash range so entries trace back to
source. The mandate is stated in
`skills/documentation-sync/references/release-notes-and-changelogs.md:46-67` — a
`## Changelog Entry Format` section whose entire content is the
`<changes starting-hash="…" ending-hash="…">` wrapper, the `git rev-parse
--short HEAD` recipe for obtaining it, and a narrow escape hatch
(`release-notes-and-changelogs.md:67`) that only applies when git is unavailable,
the directory is not a repo, or the user objects.

Two things are wrong with it.

**The recorded range decays.** Nothing pins a changelog entry's hashes to the
commits they named. Rebase, amend, and squash all rewrite them, and the skill's
own fold procedure institutionalises the decay: `cut-version.md:133-135` has to
carry a dedicated step telling the agent to extend the ranges after a fold, and
`cut-version.md:163` lists forgetting it as a common mistake whose consequence is
that "a stale range outlives the fold". The skill already knows the ranges lie;
its answer is a manual repair step rather than dropping the field.

**It costs more than it returns.** Producing the range means extra `git` calls
and threading hashes into prose during the documentation gate, on every code
change, for a lookup that `git log --grep` or `git blame` answers directly from
the entry's text.

The requirement is instruction-only. No code emits, validates, or reads the
hashes: the sole mention in shipped code is
`scripts/cut_version.py:33-36`, a literal header string recreated in a fresh
`docs/changelogs/upcoming.md` after rotation, and the only test touching that
file (`tests/test_cut_version.py:79-80`) asserts `"# Upcoming" in fresh`, never
the body of the header. So this change is prose plus one string constant.

The requirement also supplies half the stated reason the documentation pass runs
once at the *end* of `implement` rather than task-by-task — see
`skills/documentation-sync/SKILL.md:18` and
`skills/tcw-work/references/stage-implement.md:44-50`, both of which argue "a
changelog entry can't state its commit range until the range exists". Removing
the requirement without repairing those sentences would leave the lifecycle's
documentation gate justified by a rule that no longer exists.

## Goals

1. No instruction anywhere in TCW's shipped skills asks an agent to record,
   compute, or extend a commit hash range for a changelog entry.
2. TCW's own `AGENTS.md` Documentation Sync entry stops asking for it, and the
   `upcoming.md` header text agrees with what `scripts/cut_version.py` writes.
3. The end-of-`implement` documentation gate keeps its position and its force,
   restated on the half of its rationale that survives.
4. No changelog file's *entries* are edited — released or pending.

## Non-goals

- **Reconsidering when documentation is written during `implement`.** The gate's
  placement is out of scope; only the sentence explaining it changes.
- **Stripping hashes from changelog entries.** Released `docs/changelogs/v*.md`
  and the pending entries in `docs/changelogs/upcoming.md` keep the hashes they
  already carry. Rewriting history was explicitly declined.
- **Any behavioral change to the `tcw` CLI.** No command emits or reads these
  hashes; none needs to change.
- **`skills/tcw-post-mortem/SKILL.md:36`** ("The commit range. `git log` over the
  item's commits shows what order things actually happened in"). That is about
  reading git during a post-mortem, not about writing hashes into a changelog.
  It stays.
- **The separate `skill-cefailures:documentation-sync` skill**, which lives in
  another repository.

## Design

Seven sites, all prose except one Python string. Each is a deletion or a
sentence-level rewrite; there is no new mechanism.

### 1. `skills/documentation-sync/references/release-notes-and-changelogs.md`

- **Delete `## Changelog Entry Format` entirely (lines 46-67).** The section has
  no content besides the wrapper mandate, the `git rev-parse` / `git log
  --oneline` recipe, and the "Skip hash wrappers" escape hatch. With the mandate
  gone, the escape hatch has nothing to escape from, so it goes with it. Entry
  *content* guidance — "include everything", "reference file paths", "group by
  category" — lives in the preceding section (lines 39-44) and is untouched.
- **Line 75**, the recommended Documentation Sync entry, becomes:
  `` - `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog; technical, grouped by category ``

### 2. `skills/documentation-sync/SKILL.md`

- **Line 18** drops the clause "and a changelog entry can't state its commit
  range until the range exists". The remaining reason — docs written
  mid-implementation describe a shape the change no longer has by the time it
  lands — stands on its own and keeps the sentence's conclusion (`verify` reviews
  code and docs together) intact.
- **Line 30**, the sample Documentation Sync section, takes the same replacement
  text as site 1's line 75, so the two templates stay identical.

### 3. `skills/documentation-sync/references/cut-version.md`

- **Delete fold step 5** (lines 133-135, "Extend the commit-hash ranges") and
  renumber the two steps below it: `6. Commit` → `5.`, `7. Re-tag at HEAD` → `6.`
  Nothing outside this list refers to the fold steps by number — the only
  numbered cross-reference in the file is to `Step 0` (line 157), a different
  list.
- **Delete the Common Mistakes row at line 163** ("Folding and leaving the old
  commit ranges in `v{version}.md`"). Its fix instruction is the step being
  deleted.

### 4. `AGENTS.md` line 65

Drop the trailing clause, leaving:

`` - `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog for the next version; technical, grouped (Added/Changed/Fixed/Removed/Internal). ``

`CLAUDE.md` is a symlink to `AGENTS.md`, so this is one edit, not two.

### 5. `scripts/cut_version.py` lines 33-36

The `UPCOMING["docs/changelogs/upcoming.md"]` header template loses its hash
clause:

```
"# Upcoming\n\n"
"Developer changelog for the next version. Technical and precise; grouped by\n"
"category.\n"
```

### 6. `skills/tcw-work/references/stage-implement.md` step 6 (lines 45-51)

Drop "and a changelog entry cannot state its commit range until there is one".
The step's imperative — run the doc pass only once every plan task is done and
the suite is green, evaluate every trigger against the finished diff, commit doc
updates separately — is unchanged, as is the paragraph below it naming step 6 as
the lifecycle's documentation gate.

### 7. `docs/changelogs/upcoming.md` line 3-4

The file's own header prose is brought in line with site 5's new template, so a
rotation does not silently change the header text. **Only the header changes** —
every existing entry keeps its `` (`hash`) `` suffix. This is the one place the
change touches a changelog file, and it touches instruction prose in it, not an
entry.

## Acceptance criteria

1. `grep -rniE "commit[- ]hash range|commit range|starting-hash|ending-hash" skills/ scripts/ AGENTS.md docs/changelogs/upcoming.md` returns exactly one hit:
   `skills/tcw-post-mortem/SKILL.md:36` (out of scope per Non-goals).
2. `git diff --stat` for the whole change lists no file matching
   `docs/changelogs/v*.md`.
3. `docs/changelogs/upcoming.md` still contains every `` (`hash`) `` suffix it
   carries at the start of this work — the only lines changed in that file are
   in the header paragraph above the first `##` heading.
4. The header string `scripts/cut_version.py` writes for
   `docs/changelogs/upcoming.md` is byte-identical to the header currently in
   `docs/changelogs/upcoming.md` (everything above the first `##` heading).
5. `skills/tcw-work/references/stage-implement.md` step 6 still states all three
   of: run it only after every plan task is done and the suite is green;
   evaluate every trigger against the finished diff; commit doc updates
   separately from code. `skills/documentation-sync/SKILL.md:18` still gives the
   shape-drift reason for the one-pass-at-the-end rule and still concludes that
   `verify` reviews code and docs together.
6. The fold procedure in `skills/documentation-sync/references/cut-version.md`
   is numbered `1.` through `6.` with no gap, and its Common Mistakes table has
   no row about commit ranges.
7. The recommended Documentation Sync entry for `docs/changelogs/upcoming.md` is
   textually identical in `skills/documentation-sync/SKILL.md` and
   `skills/documentation-sync/references/release-notes-and-changelogs.md`.
8. `pytest` passes, including `tests/test_cut_version.py` and
   `tests/test_plugin_manifests.py`.

## Risks

- **Over-trimming the gate's rationale.** Both surviving sentences (sites 2 and
  6) are the only written justification for the end-of-`implement` documentation
  gate. Cutting the clause is a scalpel edit; deleting the sentence would leave
  the gate looking arbitrary and invite a later reader to move it. AC5 pins the
  surviving content. *Mitigation: sentence-level edits only, verified against
  AC5.*
- **Downstream projects still holding `<changes>` wrappers.** Any project that
  adopted the skill earlier has changelog entries in a syntax the skill will no
  longer explain. Accepted: the wrappers are inert Markdown, the entries stay
  readable, and this item explicitly does not rewrite history. No migration note
  is written, since the requirement's removal is announced in TCW's own release
  notes.
- **`documentation-sync` regressing on its own change.** This item edits the very
  skill that governs the documentation gate; the gate must still be run on this
  work, against the *new* text. *Mitigation: the plan schedules the doc pass as
  its own block, as usual.*
- **Prose drift between the two recommended-entry templates.** They are duplicated
  by design (router + reference); an edit to one and not the other reintroduces
  the requirement in half the skill. AC7 checks them against each other.

## Notes

- Site inventory came from
  `grep -rn "hash\|<changes\|commit range\|commit hash" skills/ scripts/ AGENTS.md README.md docs/{changelogs,release-notes}/upcoming.md tests/`
  at spec time, with `docs/work/` and released `v*.md` excluded. `README.md` has
  no hit; neither does `docs/release-notes/upcoming.md`.
- `tests/test_cut_version.py:79-80` asserts only `"# Upcoming" in fresh`, so
  site 5's template change breaks no test. Confirmed by reading the assertion,
  not inferred.
- Expected documentation triggers, for the plan to schedule: `Any-Code-Change`
  (`scripts/cut_version.py` changes) → `docs/changelogs/upcoming.md`;
  `Public-API` (the shipped skill's instructions change for every adopting
  project) → `docs/release-notes/upcoming.md`; `Skill-Driven-Component` →
  `skills/documentation-sync/SKILL.md` and `skills/tcw-work/…`, which sites 1-3
  and 6 already are.
