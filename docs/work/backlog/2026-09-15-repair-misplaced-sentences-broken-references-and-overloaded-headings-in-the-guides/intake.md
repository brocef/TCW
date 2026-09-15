## Inbox manifest

- `2026-09-11-prose-defects-the-heading-sweep-found.md`

## Inbox body

# Defects the heading sweep found that no heading can fix

## Desired outcome

`README.md` and `docs/guide/` contain no duplicated sentence, no cross-reference
that points the wrong way or nowhere, and no section describing repository-wide
contributor tooling from inside a document about one feature. And
`pnpm prettify:check`, which `docs/guide/web-viewer.md` calls "repository-wide
and deterministic", passes on a clean checkout.

## Context

Found while doing
`2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document`,
which swept `README.md` and every file under `docs/guide/` for headings that
name one topic and swallow another. That item fixed thirteen of those by
inserting headings and touching no prose. Its acceptance criteria pin that: a
diff check that must show no removed line is the only mechanical proof the
request's "without reflowing the content itself" was honoured.

These five cannot be fixed that way. Each needs a sentence deleted, moved, or
rewritten, so folding them in would have destroyed that check. They were
recorded rather than done, with the requester's rule in mind that a scope
inherited from a previous stage is a scope nobody chose.

All five verified at `3a063f6f`. Line numbers are from that commit and have
since shifted by the heading insertions.

1. **`docs/guide/configuration.md:223-226`** — a four-line tail under
   `## Declaring which documents track which changes` that is about neither
   documents nor tracking. Its first sentence ("`tcw-config.yaml` is a file in
   your own repository and is trusted exactly as much as any other file there —
   this is not a sandbox") repeats `:3-5` of the same file almost word for word.
   Its second ("`tcw serve` does **not** run hooks, so a `pre` hook that would
   block a transition does not block it from the web app") is about hook
   execution and now has a home: `## How bindings run`, added by the heading
   item.

2. **`docs/guide/taxonomy-and-capabilities.md:53-54`** — "see `tcw capabilities`
   **above**", but `## tcw capabilities — the user stories` is at `:60`, below.
   One word.

3. **`docs/guide/web-viewer.md:47`** — links to
   `#tcw-links--reference-a-tcw-object` as a same-page anchor. That heading lives
   in `docs/guide/linking-and-validation.md:6`, so the link resolves to nothing.
   Probably created by the README split, and worth checking whether the split
   left other same-page anchors pointing at headings that moved.

4. **`docs/guide/web-viewer.md:20-31`** — documents `pnpm prettify` and
   `pnpm prettify:check`, repository-wide contributor formatting with nothing to
   do with the web viewer, inside a document titled "The local web viewer". The
   fix is moving it to contributor documentation, which is a judgment about
   where contributor tooling is documented. Separately, `:3` and `:5` state
   nearly the same sentence twice.

5. **Five references whose antecedent is now in another section.** Three were
   created by the heading change itself and two predate it. Each needs a word or
   a clause, which is prose work the heading item's zero-deletion check forbids.
   - `README.md:388` — "Three read-only review agents ship alongside **them**".
     "Them" is the six stage-reading skills, now in the preceding section.
   - `docs/guide/work.md:424` — "Pass `-i`, `--incl-desc`, or
     `--include-descendants`" names no command; `tcw work list` is in the
     preceding section and is not repeated until `:448`.
   - `docs/guide/work.md:426` — "the same `--status` / `--all` filters" were
     defined at `:407-409`, in the preceding section.
   - `docs/guide/multi-repo.md:143` — "The one thing that relaxes with **it**".
     "It" is the absent-project tolerance, two sections up.
   - `docs/guide/work.md:488` — "Only the legal transitions **above** are
     permitted". "Above" is the state machine at `:10`. This one predates the
     change. The right repair is moving the paragraph to the state machine
     section; a heading over it was tried during review and reverted, because a
     heading standing in for a move is not a repair.
   - Borderline, recorded rather than dropped: `docs/guide/multi-repo.md:332`
     opens "What is checked differs by component", referring to provisioning
     checks two sections up. The heading supplies the referent, so this reads
     correctly today and may need nothing.

6. **The deferred half of the sweep.** The heading item stopped deliberately
   rather than run a fourth review round. What it left:
   - Six conjunctive headings that name two or three questions each, of which
     `## Checking a stage, reading its instructions, and starting its document`
     (`configuration.md:94`, 71 lines, three questions) is the clearest. A
     heading posing two questions is evidence its span is two sections, unless
     one question is a sub-case of the other.
   - `docs/guide/work.md:103-180`, `## What happens to resolved work`, 78 lines,
     containing a 31-line block on the bindable auto-delete hook.
   - `docs/guide/multi-repo.md:183-251`, `## Where a component store lives`,
     70 lines, containing the `repository:` block and the store-resolution
     ladder.
   - `docs/guide/multi-repo.md:57` and `:99` open with the same clause, and
     `:91-93` is addressing material inside a section about reading locators.

7. **`pnpm prettify:check` fails on 168 files at `3a063f6f`** — test fixtures
   under `tests/fixtures/` and sources under `web/client/` that are inside the
   formatting surface and are not formatted. This is the one entry here that is
   not a documentation change: a documented contributor command that is red on a
   clean checkout teaches contributors to ignore it, and the prose in item 4
   calling it deterministic is false while it stays that way.

## Constraints

- **This is at least three items, not one.** Items 1 to 5 are prose edits, item
  6 is more heading work, and item 7 is a formatting decision. Splitting them at
  triage is probably right; they are filed together because they were found
  together and the reasons connect.
- **Item 7 is either a large mechanical reformat or a `.prettierignore` change**,
  and which one is a real decision rather than a chore.
- **Item 4's repair needs a destination.** There is no contributor guide today.
  Deciding where contributor tooling is documented is the substance of it, and
  is why it was not folded into the heading item.
- **Item 6 is the deferred half of a sweep that took three review rounds.** Each
  round found holes in the previous round's fixes rather than in the original
  work, so the heading item stopped deliberately at a named line rather than run
  a fourth. Whoever picks item 6 up should expect the same and agree a stopping
  point before starting.
- **Items 1 to 5 and 7 do not re-open the heading question.** The heading item
  recorded what it inspected and deliberately left alone, with reasons, in its
  `spec.md`. Disagreeing with one of those calls is a separate request. Item 6
  is the exception: it is the heading question, left open on purpose.

## Supporting resources

- `tcw://work/2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document`
  — the item that found all of these. Its `spec.md` records them under *Found
  but not fixed here*, states the rule that decides when a heading swallows
  something, and lists under *Inspected and deliberately left alone* the
  sections it judged sound. Its `outcome.md` records why the sweep needed three
  review rounds.

## Triage (2026-09-15)

Parts 1 to 6 of the entry above are one item: all are edits to `docs/guide/` (and
one sentence of `README.md`), and the maintainer asked for items touching the same
feature to be combined. The entry's own advice to split was weighed against that.

- **Not in scope here:** part 7 (`pnpm prettify:check`) is tracked in `2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout`.
- **Already handled elsewhere:** the `README.md` "ship alongside them" reference in
  part 5 disappears with `2026-09-15-rewrite-the-readme-to-a-new-outline`, which replaces the README.
- **Blocked by `2026-09-15-rewrite-the-readme-to-a-new-outline`:** that item requires `docs/guide/web-viewer.md` to stay
  byte-identical (parts 3 and 4 edit it), rewrites `docs/guide/work.md`'s tracker
  section (parts 5 and 6 edit that file), and gives contributor tooling a home in the
  README's Development section, which is the destination part 4 lacked.
- Checked at triage: the `web-viewer.md` anchor is the only broken anchor across
  `README.md` and `docs/guide/`; every other defect in parts 1 to 6 is still present.
- Part 6 took three review rounds last time; agree a stopping point before starting.
