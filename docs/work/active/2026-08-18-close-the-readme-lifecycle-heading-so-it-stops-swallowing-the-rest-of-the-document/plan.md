# Plan — Close the headings that swallow the rest of the document

Twenty-three heading insertions across five documents, no prose change. The
spec's Design table grew from thirteen rows to twenty-three during
implementation and review; see its *When a long section is a defect and when it
is not* section for the rule that drove the additions. The spec's
Design table is the authority on what goes where; this plan is the order and the
proof.

**One rule governs every task.** Insert the heading, a blank line after it, and
a blank line before it if one is not already there. Change nothing else on any
line. Within a file, work **bottom-up** — the highest line number first — so
earlier insertions never shift a later target.

## Tasks

### Task 1 — `docs/guide/work.md`, seven headings

Modifies `docs/guide/work.md` only. Insert in this order, highest line first:

1. before `:552` — `## Running an item in an isolated checkout`
2. before `:411` — `## Descendants and addressing work across projects`
3. before `:388` — `## The board and the JSON projection`
4. before `:379` — `## Splitting a plan into stage documents`
5. before `:372` — `## Promoting an intake into a request`
6. before `:337` — `## Inbox entries and an item's body`
7. before `:325` — `## What the commands print`

`:331/:332` and `:336/:337` have no blank line between the paragraphs, so
insertions 6 and 7 add one above the heading as well as below it.

**Proves it:** `grep -n '^## ' docs/guide/work.md` shows nineteen `##` headings
where there were twelve, and each new one immediately precedes the paragraph
the spec names. `git diff -U0 -- docs/guide/work.md | grep '^-[^-]' | grep -v '^-$'`
prints nothing.

### Task 2 — `docs/guide/configuration.md`, two headings

Modifies `docs/guide/configuration.md` only. Highest line first:

1. before `:163` — `## How bindings run`
2. before `:94` — `## Checking a stage, reading its instructions, and starting its document`

`:161/:162` runs together, so insertion 1 adds a blank line above the heading.

**Proves it:** `sed -n '1,93p'` of the result is byte-identical to
`git show 3a063f6f:docs/guide/configuration.md | sed -n '1,93p'` — the span the
request protects. `git diff -U0 -- docs/guide/configuration.md | grep '^-[^-]' | grep -v '^-$'`
prints nothing.

### Task 3 — `docs/guide/multi-repo.md`, two headings

Modifies `docs/guide/multi-repo.md` only. Highest line first:

1. before `:325` — `## Which repository owns what`
2. before `:316` — `## What is checked when a store is declared`

**Proves it:** `grep -n '^## ' docs/guide/multi-repo.md` shows six `##` headings
where there were four. Diff check as above.

### Task 4 — `docs/guide/taxonomy-and-capabilities.md`, one heading

Modifies `docs/guide/taxonomy-and-capabilities.md` only.

1. before `:56` — `## Bootstrapping a taxonomy or a capabilities ledger`

**Proves it:** the new heading sits between `:54` ("…above).") and the
"To **bootstrap**" paragraph, and `## tcw capabilities — the user stories`
follows it three paragraphs later.

### Task 5 — `README.md`, one heading

Modifies `README.md` only.

1. before `:386` — `### Review agents and slash commands`

A `###`, not a `##`, because the enclosing `## Skills — the judgment layer` is
accurate and only its subdivision is incomplete. This is the only `###` in the
change; the spec says why.

**Proves it:** `grep -n '^### ' README.md` shows five `###` headings where there
were four, the new one between the `tcw-work-stage-*` paragraph and "Three
read-only review agents".

### Task 6 — whole-change checks

Changes no file. Runs, against the whole change at once:

1. `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^-[^-]' | grep -v '^-$'`
   — must print nothing (spec criterion 2).
2. `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^+[^+]' | grep -vE '^\+(#{2,3} |$)'`
   — must print nothing (spec criterion 3).
3. `diff <(git show 3a063f6f:docs/guide/configuration.md | sed -n '1,93p') <(sed -n '1,93p' docs/guide/configuration.md)`
   — must be empty (spec criterion 4).
4. `pnpm prettier --check README.md 'docs/guide/**/*.md'` — must pass (criterion 5).
5. `python -m pytest -q` — must report 2594 passed, the `3a063f6f` baseline
   (criterion 6). The suite takes about sixteen minutes; run it once here, not
   per task.
6. `git status --short` — nothing outside `README.md`, `docs/guide/` and
   `docs/work/` (criterion 7), and `docs/guide/web-viewer.md` absent from it
   (criterion 8).

### Task 7 — file the follow-up item

Creates one document under `docs/work/inbox/` naming all five defects from the
spec's *Found but not fixed here*: the duplicated sentence and misplaced
`tcw serve` note at `docs/guide/configuration.md:223-226`; the "above" that
points below at `docs/guide/taxonomy-and-capabilities.md:53-54`; the broken
same-page anchor at `docs/guide/web-viewer.md:47`; the contributor-formatting
block and repeated sentence at `docs/guide/web-viewer.md:3,5,20-31`; and
`pnpm prettify:check` failing on 168 files at `3a063f6f`.

Filed to `docs/work/inbox/` rather than created with `tcw work new`, because
this repository's guide says to record work as plain Markdown in the inbox
while TCW's own code is in flux — and more simply, the triage decision about
what those five defects are worth belongs to the `inbox` stage, not to this
item.

**Proves it:** the file exists, and spec criterion 8 reads it.

## Documentation Sync

Evaluated against every entry `tcw work docs` reports. One fires.

- **`README.md` — [Public-API].** Trigger does **not** fire: no CLI surface and
  no user-facing behaviour changes. `README.md` is edited anyway, by Task 5, as
  a subject of the change rather than as documentation of one. No extra task.
- **`docs/release-notes/upcoming.md` — [Public-API].** Trigger does **not** fire.
  Release notes describe what a user can now do; nobody can do anything new. A
  reader who finds the guide easier to navigate does not need telling in advance.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change].** **Fires.** The trigger is
  any change, and the changelog has a `Changed` group for exactly this. Task 8.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component].** Trigger does
  **not** fire: no component's CLI surface, model, lifecycle or guardrails
  changes, and no skill document is touched.

### Task 8 — changelog entry

Modifies `docs/changelogs/upcoming.md` only. Adds a `## Changed` group with one
entry naming the five documents and saying the change is heading structure with
no prose edited.

**Proves it:** the file is no longer just its three-line preamble, and the entry
names all five files.

## Verification

What the suite cannot check, and what does check it:

- **That the headings are honest.** No test can tell whether
  `## What the commands print` names `:325-336` well. This needs a person, or a
  reviewer reading the outline against the prose, at the `verify` stage. It is
  the item's main residual risk and the spec says so.
- **That no prose moved.** This *is* mechanically checkable and Task 6.1 and
  6.2 are the check. They are stronger than a human read here, because a
  reviewer skimming a 200-line diff of mostly-context will not notice one
  re-wrapped paragraph.
- **That the outline reads correctly in a Markdown viewer.** `grep` proves the
  headings exist at the right offsets; it does not prove GitHub renders the
  outline as intended. Render the five files and read their outlines.
- **That the sweep was complete.** Unfalsifiable by construction — absence of a
  further mismatch cannot be proved. Mitigated instead by the spec listing what
  was inspected and left alone, so a reviewer checks the calls rather than
  redoing the sweep.

## Notes

- No task depends on another except Task 6, which depends on Tasks 1 through 5,
  and Task 8, which is independent. Tasks 1 through 5 touch disjoint files and
  the suite is green between any two of them, so they could run in any order;
  the given order is largest file first, so the riskiest bulk edit is isolated
  in its own commit while the tree is otherwise untouched.
- Commit per task. Five documentation commits, one for the inbox note, one for
  the changelog. Task 6 commits nothing.
