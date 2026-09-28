# Spec: collect changelog and release-note entries as one file per item

## Capability changes

- **changed** `skills/documentation-sync` (cap-301436) — add one sentence to its
  story: in a project using the per-version release-notes and changelog layout,
  each finished change adds its entries as its own file in an `upcoming/` folder,
  and the version cut combines those files into the version's document. No other
  capability changes; `work/declare-which-documents-track-which-changes` is
  unaffected because the entry format itself does not change (see Design §2).

## Problem

Every finished change appends to one of two shared files:
`docs/changelogs/upcoming.md` (entry at `tcw-config.yaml:59`, trigger
`Any-Code-Change`, which fires on nearly every change) and
`docs/release-notes/upcoming.md` (`tcw-config.yaml:55`). Two branches that each
finish a change both edit the end of the same file, so merging the second one
conflicts — and the conflict is in prose, which an agent resolves by hand.

The shipped `documentation-sync` skill teaches the same single-file layout to
every TCW project: `skills/documentation-sync/references/release-notes-and-changelogs.md:9-21`
(directory layout), `:46-55` (recommended entries), `:57-70` (cross-check and
rotation); `references/cut-version.md:52-66` (rotation step) and `:125-134`
(folding into an unpushed version); `skills/configure/references/docs-sync.md:18`
and `:43` (setup creates `upcoming.md`). So every TCW project running agents in
parallel branches has the same conflict.

This repo's cut, `scripts/cut_version.py:102-124` (`rotate_upcoming`),
`git mv`s each `upcoming.md` to `v{version}.md`, retitles it `# v{version}`,
drops the working-file preamble, and recreates a fresh `upcoming.md`.

## Goals

1. Recording a changelog or release-note entry for a change never edits a file
   that another change's entry also edits.
2. At version cut, all recorded entries become one `v{version}.md` per kind that
   reads as a single document: one `# v{version}` title, and each section
   heading appearing once.
3. The shipped skills teach this layout to every project that uses the
   per-version structure, and tell an agent what to do in a project still on a
   single `upcoming.md`.
4. This repo is switched over, with the entries currently in its two
   `upcoming.md` files preserved.

## Non-goals

- A `tcw` CLI command for combining entries (the requester declined it). Other
  projects' agents follow written steps; this repo's script does the work here.
- Changing the `work.documentation` entry format or its validation.
- Rewriting already-released `v{version}.md` files or the historical migration
  guides (`docs/migration-guide-*.md`), which describe past versions.
- Automatically migrating another project's `upcoming.md`. Migration stays an
  offer, as the skill already requires (`release-notes-and-changelogs.md:77`).
- Detecting two branches that write the same slug's file (same item on two
  branches is already one piece of work; see Risks).

## Design

### 1. Layout

```
docs/changelogs/
  upcoming/
    README.md                     # drafting guidance; never combined
    <work-item-slug>.md           # one file per change
  v1.2.3.md
docs/release-notes/
  upcoming/
    README.md
    <work-item-slug>.md
  v1.2.3.md
```

- **File name:** the work item's slug, `<slug>.md`. Work done outside any item
  uses `<YYYY-MM-DD>-<short-description>.md`, the same shape as a slug. Because
  slugs begin with a date, file-name order is roughly chronological.
- **A change that already has a file** (for example, rework on the same item)
  edits its own file; it never touches another item's file.
- **`README.md`** carries what today's `upcoming.md` preamble carries (who the
  document is for, and how to write it). It exists also so the folder survives
  in git when it holds no entries. It is excluded from combining.
- **Inside a file:** entries go under `## <Heading>` sections — for the
  changelog, `## Added`, `## Changed`, `## Fixed`, `## Removed`, `## Internal`;
  for release notes, whatever headings the project uses. No `#` title. A `###`
  or deeper heading belongs to the `##` section above it.

### 2. Documentation entries name a placeholder path

The entries become `docs/changelogs/upcoming/<slug>.md` and
`docs/release-notes/upcoming/<slug>.md`. This needs no code change: entry paths
are shape-checked only and need not exist, and a placeholder such as
`skills/<component>/SKILL.md` is already legal and in use
(`tcw/store/base.py:2742-2748`; `tcw-config.yaml:62`). The descriptions say to
write one file per item.

Abstraction check: this is documentation in the code repository, not a store
operation, so nothing moves into the model. It passes trivially.

Harness check: the behavior lives entirely in skill text and this repo's
script. Both Claude and Codex read the same skill files; nothing depends on a
hook or injected context.

### 3. Combining (the cut)

Applied to each `upcoming/` folder, taking every `*.md` except `README.md`,
in file-name order:

1. Split each file into a leading block (text before its first `## ` line) and
   `##` sections (each heading line plus everything up to the next `## ` line).
2. Merge sections whose heading text is identical, after trimming whitespace:
   their bodies are joined in file-name order, separated by one blank line.
3. Order the merged sections: for the changelog, `Added`, `Changed`, `Fixed`,
   `Removed`, `Internal` first in that order, when present; then every other
   heading in the order it first appears. Release notes have no fixed order;
   first appearance decides.
4. Leading blocks, if any, go right after the title, in file-name order.
5. Write `v{version}.md` as `# v{version}`, a blank line, then the result.
6. Delete the combined files; `README.md` stays.

An `upcoming/` folder with no entry files produces a `v{version}.md` holding
only the title, the same as rotating an empty `upcoming.md` does today.

**In this repo**, `scripts/cut_version.py` replaces `rotate_upcoming` with this
combining, and stages the new `v{version}.md` files and the deletions in the
same release commit. Its other guarantees are unchanged: abort on version
drift, commit, tag, never push.

**In other projects**, `references/cut-version.md` Step 2 describes the same
combining as written steps, and still defers to the project's own cut script
when one exists (`cut-version.md:13-22`).

**Folding into an unpushed version** (`cut-version.md:125-134`): the files in
`upcoming/` are merged into the existing `v{version}.md` by the same heading
rules (a section whose heading already exists is extended, not repeated), then
deleted.

### 4. Projects still on a single `upcoming.md`

The documentation entries are authoritative (`release-notes-and-changelogs.md:5`).
When a project's entries name `upcoming.md`, the agent keeps writing there as
before, and offers once — never performs unasked — the migration: create the
`upcoming/` folders, move the existing content into one file
(`<YYYY-MM-DD>-carried-over.md`), and change the entries' paths. The migration
table in `release-notes-and-changelogs.md` gains this row. The version cross-check
(`:57-70`) is rewritten for folders: "the `upcoming/` folder holds entries" takes
the place of "`upcoming.md` has content".

### 5. Files that change

- `scripts/cut_version.py`, `tests/test_cut_version.py`
- `tcw-config.yaml` (two entries), `CLAUDE.md` and `AGENTS.md` Versioning
  sections
- `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` → replaced by
  `upcoming/README.md` plus one carried-over entry file each
- `skills/documentation-sync/SKILL.md` (example entry, line 41),
  `references/release-notes-and-changelogs.md`, `references/cut-version.md`
- `skills/configure/references/docs-sync.md`
- `tcw/work/procedures/documentation-sync.md:84-90`,
  `tcw/work/procedures/unattended-work.md:37`
- `tests/test_repo_lifecycle.py:101-109`, `tests/test_documentation_prompt.py`
  and `tests/test_documentation_config.py` fixtures (only if their wording is
  asserted against shipped text; they parse arbitrary paths otherwise)
- `README.md:887-891` (Releasing paragraph) and `docs/guide/configuration.md:212`
  (example entry)
- `evals/seed_fixture.py:425-431` — **only its comment changes.** The fixture
  deliberately stays on a single `upcoming.md`: eval case B10
  (`evals/evals.json:796-803`) asserts the exact list of changed paths,
  `README.md` and `docs/changelogs/upcoming.md`, and a file named by the agent
  could not be listed in advance. Keeping it also makes the fixture exercise
  the older layout that Design §4 still supports.
- `tests/cli/scenarios/13-release-integrity.md` row 8
- the capability `skills/documentation-sync`

**Sibling sweep:** `git grep -ln upcoming`, excluding `docs/work/`, released
`v*.md` and the migration guides, found the files above plus four that stay as
they are: `docs/plan/phase-5-work.md` and two `docs/superpowers/` documents
(historical plans), and `docs/guide/web-viewer.md:30` ("upcoming notes", which
stays true of the folders). `.prettierignore:27-28` ignores only `v*.md`, so the
new entry files are formatted like `upcoming.md` was.

## Acceptance criteria

1. `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` no longer
   exist; `docs/changelogs/upcoming/README.md` and
   `docs/release-notes/upcoming/README.md` do.
2. The entries that were in the two `upcoming.md` files at the start of this
   item (the `commands-pause-work` resume-line change) are present, word for
   word, in a file under the matching `upcoming/` folder.
3. `tcw work docs` lists `docs/changelogs/upcoming/<slug>.md` and
   `docs/release-notes/upcoming/<slug>.md`, and `tcw validate` reports no
   problem with them.
4. A test runs `cut_version.main` against a temporary repo whose
   `docs/changelogs/upcoming/` holds two entry files, `a.md` with `## Fixed`
   and `## Added` sections and `b.md` with `## Added` and `## Security`
   sections, plus `README.md`, and asserts that `docs/changelogs/v{new}.md`:
   starts with `# v{new}`; contains exactly one `## Added`, whose body holds
   `a.md`'s entries before `b.md`'s; orders sections `Added`, `Fixed`,
   `Security`; contains nothing from `README.md`. After the run `a.md` and
   `b.md` are gone, `README.md` is unchanged, and the commit is tagged `v{new}`.
5. The same test with an `upcoming/` folder holding only `README.md` produces a
   `v{new}.md` whose only content is the `# v{new}` title line.
6. A `###` heading inside a `##` section stays under that section in the
   combined output (covered by a test).
7. `grep -rn 'upcoming\.md'` over `skills/`, `tcw/`, `scripts/`, `CLAUDE.md`,
   `AGENTS.md`, `README.md`, `docs/guide/` and `tcw-config.yaml` finds only the text that tells an agent
   what to do in a project still on a single `upcoming.md`
   (§4 of Design) — no instruction to write to or rotate one.
8. `references/cut-version.md` describes combining folders, including the fold
   into an unpushed version, and `references/release-notes-and-changelogs.md`
   contains the migration row and the folder cross-check.
9. `README.md`'s Releasing paragraph and `docs/guide/configuration.md`'s example
   entry describe the folders. The eval fixture still declares and creates
   `docs/changelogs/upcoming.md`, and its comment says why.
10. The full test suite passes with `pytest` run bare, as CI runs it.
11. The capability `skills/documentation-sync` says entries are one file per
    change in an `upcoming/` folder, combined at cut.

## Risks

- **Two branches writing for the same item** would still conflict on
  `<slug>.md`. Accepted: that is one piece of work in two places, which the
  work system already treats as a problem.
- **A mistyped heading** (`## Fixes` next to `## Fixed`) produces two sections
  instead of one. The fixed changelog order makes the stray one visible at the
  bottom of the document; the cut does not try to guess.
- **An entry file with no `##` heading** lands in the leading block right after
  the title, which can look out of place. Visible in review of the release
  commit; acceptable.
- **Agents in other projects follow written combining steps** rather than a
  script, so a hand-combined release can drift from these rules. Accepted by
  the requester in declining a CLI command.
- **Existing TCW projects on `upcoming.md`** see no change until they accept the
  offered migration, so the conflict problem remains for them until then.

## Notes

- The release-note headings in this repo are mostly feature titles rather than
  fixed categories (`grep -h '^##' docs/release-notes/v2.*.md` shows many
  distinct `##` headings), which is why release notes get no fixed order.
- The changelog has used both `##` and `###` for its categories
  (`docs/changelogs/v2.*.md`); the new convention settles on `##`.
