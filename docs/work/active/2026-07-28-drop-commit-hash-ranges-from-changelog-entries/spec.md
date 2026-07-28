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
4. No **released** changelog file is edited. `docs/changelogs/v*.md` are history.
   *(Amended at `verify` — originally "no changelog file's entries are edited,
   released or pending". The pending file is now in scope; see Goal 5.)*
5. The pending `docs/changelogs/upcoming.md` carries no commit hashes, so the
   next release ships a changelog consistent with the rule this item introduces.
   *(Added at `verify`.)*
6. Projects already holding `<changes>` wrappers get a migration guide in
   `docs/`, which the plugin cache carries verbatim. *(Added at `verify`.)*

## Non-goals

- **Reconsidering when documentation is written during `implement`.** The gate's
  placement is out of scope; only the sentence explaining it changes.
- **Rewriting released changelog history.** `docs/changelogs/v*.md` keep every
  hash they carry; they describe versions that already shipped.

  *Amended at `verify`.* This Non-goal originally also covered the pending
  entries in `docs/changelogs/upcoming.md`. The user overrode that half at the
  verification gate: the pending file is unreleased, so bringing it in line with
  the new rule is not rewriting history. The released-file boundary is unchanged
  and remains the hard one.
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
rotation does not silently change the header text.

*Amended at `verify`.* This site originally read "**only the header changes** —
every existing entry keeps its `` (`hash`) `` suffix". Sites 8 and 9 below were
added when the verification gate widened the scope.

### 8. `docs/changelogs/upcoming.md` entries *(added at `verify`)*

Strip every commit hash from the pending changelog: all 12 per-entry
`` (`hash`) `` suffixes and the `` Commit range: `24f4bc6..0886943`. `` footer.
Entry prose is otherwise untouched — this removes attributions, not content.

The file is unreleased, so this is not a history rewrite; `docs/changelogs/v*.md`
remain closed (AC2). The result is that the next release ships a changelog whose
form matches the rule the release itself announces.

### 9. `docs/migration-guide-0.15.X-to-0.16.0.md` *(added at `verify`)*

A new file, following `migration-guide-0.14.X-to-0.15.0.md` and its two
predecessors. The whole repository *is* the plugin payload — the cache at
`~/.claude/plugins/cache/tcw/tcw/<version>/` contains `docs/` verbatim — so no
packaging change is needed for users to read it.

It differs from every predecessor in kind: they describe required migrations
(move files, run `tcw validate`), this one describes a **relaxation**. Nothing
breaks on upgrade and nothing must be done. The guide has to lead with that and
then offer the optional cleanup, rather than dressing a non-event as a
procedure (AC9).

The name presupposes a minor bump at closeout, which is the user's stated
choice.

## Acceptance criteria

1. `grep -rniE "commit[- ]hash range|commit range|starting-hash|ending-hash" skills/ scripts/ AGENTS.md` returns exactly one hit:
   `skills/tcw-post-mortem/SKILL.md:36` (out of scope per Non-goals).

   The grep roots are the **instruction surfaces** — the skills that teach the
   rule, the one script that emits it, and TCW's own adoption of it. That is what
   the criterion is actually about: no shipped instruction asks for a hash range.

   *History of this criterion — it was wrong twice, in opposite directions.*

   - **Written** expecting one hit over roots that also included
     `docs/changelogs/upcoming.md`.
   - **Corrected during `implement`** to expect **two**: the spec's
     site-inventory grep (see Notes) was case-sensitive on `commit range` and had
     missed `` Commit range: `24f4bc6..0886943`. `` at
     `docs/changelogs/upcoming.md:71`, the footer of a pending entry written under
     the old rule in commit `3633c30`. The original Non-goals made that line
     untouchable, so the criterion had to widen to accommodate it.
   - **Corrected again after the `verify` gate**, when AC3 deleted that footer.
     The count did not return to one: it went to **three**, because the changelog
     entry announcing this very change has to name `starting-hash`,
     `ending-hash`, and "commit-hash ranges" in order to say what was removed.

   A changelog is not an instruction, so the third state exposed a defect in the
   criterion rather than in the work — the grep root was wrong from the start.
   `docs/changelogs/upcoming.md` is dropped from the roots; AC3 (no hashes in it)
   and AC4 (its header matches the template) cover that file, and they cover it
   better, because they do not break when an entry legitimately names the thing
   it removed.
2. `git diff --stat` for the whole change lists no file matching
   `docs/changelogs/v*.md`.
3. `docs/changelogs/upcoming.md` contains **no** commit hash: no
   `` (`hash`) `` suffix on any entry and no `Commit range:` footer. Entry prose
   is otherwise unchanged — the diff removes hash attributions and nothing else.
   *(Inverted at `verify`. It previously required every suffix to survive. AC2
   still guards the released files, which is the boundary that held.)*
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
9. `docs/migration-guide-0.15.X-to-0.16.0.md` exists, follows the naming
   convention of its three predecessors, and states plainly that **no user
   action is required** before describing the optional cleanup. It must not
   invent a required ritual for a change that only relaxes a rule.
   *(Added at `verify`.)*

## Risks

- **Over-trimming the gate's rationale.** Both surviving sentences (sites 2 and
  6) are the only written justification for the end-of-`implement` documentation
  gate. Cutting the clause is a scalpel edit; deleting the sentence would leave
  the gate looking arbitrary and invite a later reader to move it. AC5 pins the
  surviving content. *Mitigation: sentence-level edits only, verified against
  AC5.*
- **Downstream projects still holding `<changes>` wrappers.** Any project that
  adopted the skill earlier has changelog entries in a syntax the skill will no
  longer explain. *Mitigated at `verify` by site 9.* The spec originally accepted
  this unmitigated — the wrappers are inert Markdown and the removal is announced
  in the release notes — but the user called for a migration guide, which now
  carries the explanation and the optional cleanup. The wrappers still need no
  action.
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
