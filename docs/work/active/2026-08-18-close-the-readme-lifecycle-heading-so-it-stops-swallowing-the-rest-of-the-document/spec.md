# Spec — Close the headings that swallow the rest of the document

## Capability changes

None. This changes the structure of prose only. No command gains, loses, or
alters behaviour, so no ledger entry is added, revised, or re-statused.
`tcw capabilities list` carries no entry describing documentation structure, and
minting one for a heading fix would be inventing a user story nobody has.

## Problem

The request was filed against `README.md:605`, where
`### Binding your own skills and commands to the lifecycle` was followed by no
further `###` until `:1102`, so roughly 280 lines of unrelated material — the
command reference, the Definition of Done, the board, the JSON projection,
descendants, and decomposition — rendered inside a heading about lifecycle
hooks.

**That line no longer exists.** `README.md` is now 423 lines and its body was
split into `docs/guide/`. The heading the request names moved to
`docs/guide/configuration.md:11` and is now a `##`.

**The defect did not move with it.** The split relocated the swallowed prose
without giving it accurate headings, and in one place the very topics the
request enumerated are still swallowed — just by a different heading. Verified
against `3a063f6f`:

- `docs/guide/work.md:360` opens `## Automation and piping`, and the next `##`
  is `:439`. Only `:362-370` (piping into `tcw work new`) is about automation.
  `:372-377` covers promoting an intake into a request, `:379-386` declaring a
  plan's stage documents, `:388-409` the board and `tcw work show --json`, and
  `:411-437` descendants and addressing work across projects. **The board, the
  JSON projection, and descendants are three of the six topics the original
  request named as swallowed.**
- `docs/guide/work.md:317` opens `## Tags`, and the next `##` is `:360`. Tags end
  at `:323`. `:325-336` is what the commands print — the next-transition hint,
  the edit hint, and where a moved item now lives. `:337-358` is inbox entry
  formats and how an item's body surface resolves.
- `docs/guide/work.md:497` opens `## Cross-node recursion (epics across repos)`
  and runs to the end of the file. `:552-577` documents
  `tcw work start --worktree`, which applies to any item on a single node.
- `docs/guide/configuration.md:11` opens
  `## Binding your own skills and commands to the lifecycle`, and the next `##`
  is `:174`. `:94-161` documents `tcw work stage gate`, `tcw work stage prompt`
  and `tcw work scaffold` — reading and running a stage, not binding anything to
  it. `:163-172` then returns to bindings (hook order, environment, timeout, and
  that skill bindings are reported rather than run), stranded behind the
  command material.
- `docs/guide/multi-repo.md:281` opens `## Keeping a provisioned store in step`
  and runs to the end of the file. `:316-323` is what is checked when a store is
  declared, which happens at provisioning rather than afterwards. `:325-339` is
  how every reader and writer of work follows `work.path` and which repository
  owns what, true of any configured store and not only a provisioned one.
- `docs/guide/taxonomy-and-capabilities.md:15` opens
  `## tcw taxonomy — the nouns`. `:56-58` is about bootstrapping a taxonomy **or
  a capabilities ledger**, and names both commands.
- `README.md:373` opens `### Reading a lifecycle stage`, and the next heading is
  `## Status` at `:397`. `:386-393` lists the three read-only review agents and
  all thirteen slash commands the plugin ships.

A reader who opens any of these outlines sees material filed under a heading
that does not name it, which is the complaint as filed.

## Goals

1. Every span listed under **Problem** sits under a heading that names it.
2. The prose is untouched. No sentence is rewritten, reordered, deleted, or
   moved between files. Only heading lines, and the blank lines a heading needs,
   are added.
3. The sweep the request asked for covers all of `README.md` and `docs/guide/`,
   not only the file the request happened to name, and what was inspected and
   deliberately left alone is written down with its reason.

## Non-goals

- **Rewriting, deleting, or relocating any prose.** The sweep found four defects
  that no heading can fix, listed under *Found but not fixed here*. They go to a
  follow-up item. Folding them in would destroy acceptance criterion 2, which is
  the only mechanical check that "without reflowing the content itself" was
  honoured.
- **Adding headings for their own sake.** `docs/guide/web-viewer.md` has one `#`
  and no `##` across 115 lines. A document with one accurate title and a
  continuous body is not the reported defect; subdividing it for navigation is
  an improvement nobody asked for.
- **Re-touching `docs/guide/configuration.md:11-93`.** The request protects that
  span explicitly: an earlier item rewrote it and it is accurate as it stands.
- **Rewriting the item's own `initial-request.md`** to cite the lines that exist
  today. The request records what was asked when it was asked; this spec is
  where the reinterpretation belongs, and editing the request to match the tree
  would erase the evidence that the premise moved.
- **Changing document order, splitting a file, or moving a section between
  guides.**
- **Any change under `tcw/`, `skills/`, `web/` or `tests/`.** This item ships no
  code.

## Design

Insert twenty-three heading lines. Nothing else changes.

| File | Insert before | Level and text |
| --- | --- | --- |
| `README.md` | `:386` | `### Review agents and slash commands` |
| `docs/guide/configuration.md` | `:94` | `## Checking a stage, reading its instructions, and starting its document` |
| `docs/guide/configuration.md` | `:163` | `## How bindings run` |
| `docs/guide/work.md` | `:325` | `## What the commands print` |
| `docs/guide/work.md` | `:337` | `## Inbox entries and an item's body` |
| `docs/guide/work.md` | `:372` | `## Editing a body, and how it promotes an intake` |
| `docs/guide/work.md` | `:379` | `## Splitting a plan into stage documents` |
| `docs/guide/work.md` | `:388` | `## The board and the JSON projection` |
| `docs/guide/work.md` | `:411` | `## Descendants and addressing work across projects` |
| `docs/guide/work.md` | `:472` | `## Stable slugs, and which transitions are legal` |
| `docs/guide/work.md` | `:523` | `## Claiming an item, and recovering an interrupted claim` |
| `docs/guide/work.md` | `:529` | `## Rolling up an epic, and delegating across nodes` |
| `docs/guide/work.md` | `:552` | `## Running an item in an isolated checkout` |
| `docs/guide/multi-repo.md` | `:55` | `## Overriding a project's path on this machine` |
| `docs/guide/multi-repo.md` | `:86` | `## How a locator and the parent/child lists are read` |
| `docs/guide/multi-repo.md` | `:93` | `## When a declared project is not on this machine` |
| `docs/guide/multi-repo.md` | `:122` | `## A node that keeps no work store` |
| `docs/guide/multi-repo.md` | `:131` | `## What still fails closed when a project is absent` |
| `docs/guide/multi-repo.md` | `:138` | `## Relative paths inside a linked git worktree` |
| `docs/guide/multi-repo.md` | `:155` | `## Component inheritance is opt-in per axis` |
| `docs/guide/multi-repo.md` | `:316` | `## What is checked when a declared store is obtained` |
| `docs/guide/multi-repo.md` | `:325` | `## Which repository owns what` |
| `docs/guide/taxonomy-and-capabilities.md` | `:56` | `## Bootstrapping a taxonomy or a capabilities ledger` |

Line numbers are against `3a063f6f` and shift as earlier insertions land, so
implementation works from the bottom of each file upwards.

**Every insertion is a sibling, never a child.** A `###` beneath
`## Binding your own skills and commands to the lifecycle` would leave the
material subordinate to a heading that still does not name it, which is the
defect rather than its repair. Nothing in `docs/guide/` currently uses `###` at
all, so introducing a third level there would be a structural change the request
does not ask for. The one `###` is in `README.md`, where the enclosing
`## Skills — the judgment layer` is accurate and only its `###` subdivision is
incomplete.

**Three insertion points fall between paragraphs that run together with no blank
line** — `work.md:331/332`, `work.md:336/337`, and `configuration.md:161/162`. A
heading needs a blank line on each side, so those insertions add whitespace.
That is a whitespace change, not a prose change, and Goal 2 permits it.

### When a long section is a defect and when it is not

Added after implementation began, because the first pass had no stated rule and
`## Connected projects` (`multi-repo.md:10-168`, 159 lines) was missed by the
sweep on the unexamined instinct that its five parts shared a subject.

> A heading must accurately describe its entire span. Within that span, a
> contiguous passage also needs its own outline entry when it answers a distinct
> reader question the existing heading does not make discoverable. Sharing a
> subject does not exempt it: examples, qualifications, and procedural detail may
> stay together when they develop the same question.

The reverse failure is real and this rule does not catch it: a section cut so
fine that the outline becomes a list of sentences is no more navigable than one
cut too coarse. The shortest sections here are nine lines
(`multi-repo.md:88`) and nine lines (`work.md:377`), each answering one
question a neighbouring heading does not pose. That is the floor, not a target.

Length is not the test and never was. `## Command reference`
(`work.md:216-316`, 101 lines) stays one section because it answers one
question. `## Connected projects` answered five — how a connection is declared,
how to say where the project sits on this machine, what a node with no work
store does, how relative paths behave inside a linked worktree, and whether
components inherit — so it is split six ways: the environment override, how a locator and the
parent/child lists are read, what happens when a declared project is absent, a
node with no work store, relative paths inside a linked worktree, and
inheritance. The nine-line section at `:88` is the smallest in either tree and
is deliberate — it answers "how does a relative locator resolve?", a question
neither of its neighbours predicts, and it sits where it does because the
environment-override block separated it from the declaration material it
belongs with. Moving those nine lines would give a cleaner result and is the
one place the no-prose-moves rule costs something; it is recorded in the
follow-up item rather than done.

### Found but not fixed here

Five defects the sweep turned up that no heading can repair. Four are
duplicated or misplaced sentences; the fifth is the formatting check itself.
They go to one follow-up item rather than five:

- `docs/guide/configuration.md:223-226`, a four-line tail under
  `## Declaring which documents track which changes`. Its first sentence repeats
  `:3-5` of the same file almost verbatim; its second (`tcw serve` runs no hooks)
  belongs under the new `## How bindings run`. The repair is a deletion and a
  move, not a heading.
- `docs/guide/taxonomy-and-capabilities.md:53-54` says "see `tcw capabilities`
  **above**", but that section is at `:60`, below.
- `docs/guide/web-viewer.md:47` links to `#tcw-links--reference-a-tcw-object` as
  a same-page anchor. That heading lives in
  `docs/guide/linking-and-validation.md:6`, so the link is broken.
- `docs/guide/web-viewer.md:20-31` documents `pnpm prettify`, repository-wide
  contributor formatting with nothing to do with the viewer. Fixing it means
  moving text to another document, which is a content judgment this item does
  not carry. `:3` and `:5` also state nearly the same sentence twice.
- The same span calls that formatting "repository-wide and deterministic", but
  `pnpm prettify:check` fails on 168 files at `3a063f6f` — test fixtures and
  `web/client` sources that are inside the formatting surface and unformatted.
  A documented contributor command that is red on a clean checkout is a
  separate defect from the prose describing it, and is the one entry on this
  list that is not a documentation change at all.

### Inspected and deliberately left alone

- `docs/guide/work.md:523-527` — claim concurrency and take-over, under
  `## Cross-node recursion`. **This call was reversed.** It was first left alone
  because five lines seemed too short to be worth a heading, and because fixing
  it strands the epic material that resumes at `:529` behind a second heading.
  Both reasons are length arguments, and the rule this spec now states says
  length is not the test. "What happens when two commands touch an item at
  once, and what if a process dies holding a claim?" is a distinct question the
  cross-node heading does not pose. Two headings, at `:523` and `:529`.
- `docs/guide/work.md:103-181`, `## What happens to resolved work`, 79 lines
  and the longest section left in either tree after the sweep. Left alone
  deliberately, and it is the clearest test of the rule above. Every paragraph
  answers a facet of one question — what becomes of an item you complete: the
  three arrangements a project chooses between, the two commits the resolving
  transition writes, why auto-delete and the ignore rules cannot coexist, how to
  hand the item to your own archive first, what that does not promise, and what
  a rewritten history costs. The archive procedure at `:141-171` is the closest
  call, at thirty lines; it stays because it is procedural detail developing the
  heading's own question rather than a different question.
- `docs/guide/linking-and-validation.md` — swept end to end, nothing found.
- `README.md` outside `:373-396` — swept, nothing else found.

## Acceptance criteria

1. `grep -n '^#\{2,3\} ' README.md docs/guide/*.md` lists all twenty-three headings
   from the Design table, each immediately before the span named there.
2. No prose is removed. `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^-[^-]' | grep -v '^-$'`
   prints nothing. This is what pins "without reflowing the content itself".
3. Nothing but headings and blank lines is added.
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^+[^+]' | grep -vE '^\+(#{2,3} |$)'`
   prints nothing.
4. `docs/guide/configuration.md:11-93` is byte-identical to `3a063f6f`, since the
   request protects that span.
5. `pnpm prettier --check README.md 'docs/guide/**/*.md'` passes. These files
   are inside the formatting surface and clean at `3a063f6f`, so a heading
   inserted with the wrong surrounding blank lines fails the check rather than
   being a style opinion. The criterion is scoped to these paths on purpose:
   repo-wide `pnpm prettify:check` already fails on 168 files at `3a063f6f`
   (test fixtures and web client sources), which is a pre-existing defect
   recorded under *Found but not fixed here* and not this item's to repair.
6. `pytest` passes, with the same result as at `3a063f6f`.
7. No file outside `README.md`, `docs/guide/`, `docs/work/`, `docs/changelogs/`
   and `docs/release-notes/` is modified.
8. `docs/guide/web-viewer.md` is unmodified, and a follow-up item exists under
   `docs/work/` naming all five defects from *Found but not fixed here*.

## Risks

- **The sweep is a judgment call and a different reader draws the line
  elsewhere.** Mitigated by writing down what was inspected and left alone, with
  the reason, rather than reporting only what changed. A reader who disagrees can
  see exactly which call to reverse.
- **Heading text can be wrong in a way no diff check catches.** Criteria 2 and 3
  prove no prose moved; they prove nothing about whether
  `## What the commands print` is a good name. That needs a human read, which is
  what the verify stage is for.
- **Twenty-three insertions into five files, all cited against one commit.** Line
  numbers shift as they land. Working bottom-up per file avoids it, and criterion
  1 catches it if the ordering slips anyway.
- **The request's premise is stale and this spec reinterprets it.** The spec
  stage is told to stop and return to `request` when reading the tree
  contradicts the request, and the file and line the request names are gone. It
  is treated as carried forward rather than refused because the request's second
  instruction — sweep the document for the same problem — survives the split word
  for word, and because three of the six topics it listed as swallowed are still
  swallowed today. Had the split actually fixed those, closing the item would
  have been right.

## Notes

- Line citations are against `3a063f6f`, the commit this spec was written at.
- Baseline at `3a063f6f`: `pytest` is 2594 passed in about 16 minutes, and
  `pnpm prettier --check README.md 'docs/guide/**/*.md'` is clean. Both were run
  before this spec was committed, so criteria 5 and 6 are known-achievable
  rather than hoped for.
- `docs/guide/work.md:411-437` (addressing work across projects) partly restates
  `:497` onward. Noted, not acted on: deduplicating it is a prose change.
