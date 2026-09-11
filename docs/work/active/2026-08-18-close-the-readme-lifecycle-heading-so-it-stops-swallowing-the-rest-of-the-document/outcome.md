# Outcome — Close the headings that swallow the rest of the document

Twenty-three headings inserted across five documents. No prose edited, moved, or
removed anywhere.

The count grew from thirteen during implementation and review. Ten of the
twenty-three were found after the spec was first committed, and the story of how
is the most useful thing in this document — see *What the plan and spec got
wrong*.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `83ce958d` | Seven headings in `docs/guide/work.md` |
| 2 | `31ea1e2a` | Two headings in `docs/guide/configuration.md` |
| 3 | `f68f58fd` | Two headings in `docs/guide/multi-repo.md` |
| 4 | `dde560c9` | One heading in `docs/guide/taxonomy-and-capabilities.md` |
| 5 | `dd33952c` | One heading in `README.md` |
| 6 | — | Whole-change checks; commits nothing |
| 7 | `61ad5832` | `docs/work/inbox/2026-09-11-prose-defects-the-heading-sweep-found.md` |
| 8 | `4029d417` | Changelog entry |
| — | `9738d6fa` | Six more headings: `multi-repo.md`'s `## Connected projects` split |
| — | `48594cf5` | Two heading names corrected after verification |
| — | `c481410a` | Three more headings; counts brought to twenty-two |
| — | `0127de94` | One more heading; counts brought to twenty-three |

Every insertion went in bottom-up within its file, through one script that
refuses unless the target line starts with an expected prefix, so a shifted line
number fails loudly rather than putting a heading in the wrong place.

## Acceptance criteria

All eight pass. Output is from runs made against `4029d417`.

1. **Twenty-three headings present, each before the span named.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep -cE '^\+#{2,3} '`
   returns 23, and each matches a Design-table row. By file: `README.md` 1,
   `configuration.md` 2, `taxonomy-and-capabilities.md` 1, `work.md` 11,
   `multi-repo.md` 8.
2. **No prose removed.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^-[^-]' | grep -v '^-$'`
   prints nothing.
3. **Nothing but headings and blank lines added.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^+[^+]' | grep -vE '^\+(#{2,3} |$)'`
   prints nothing.
4. **`configuration.md:1-93` byte-identical** to `3a063f6f`. `diff` is empty.
5. **`pnpm prettier --check README.md 'docs/guide/**/*.md'`** — "All matched
   files use Prettier code style!"
6. **`python -m pytest -q`** — `2594 passed in 814.11s`. The `3a063f6f` baseline
   was `2594 passed in 957.16s`, run before the spec was committed. Same count.
7. **Nothing modified outside the allowed paths.** `git status --short` is empty
   and every commit touches only `README.md`, `docs/guide/`, `docs/work/`, or
   `docs/changelogs/`.
8. **`docs/guide/web-viewer.md` unmodified**, and the follow-up item exists at
   `docs/work/inbox/2026-09-11-prose-defects-the-heading-sweep-found.md` naming
   all five defects.

## What the plan and spec got wrong

Four things.

- **The plan said two of the `work.md` insertions would need a blank line added
  above the heading; only one did.** The plan named `:331/:332` and `:336/:337`
  as paragraphs running together, then said "insertions 6 and 7 add one above
  the heading as well as below it". Insertion 7 targets `:325`, where `:324` is
  already blank, so only insertion 6 added one. The observation about `:331/:332`
  was correct and irrelevant: no heading was inserted there.

- **The sweep was wrong, and stayed wrong through three passes.** The spec
  shipped with thirteen headings and a claim that the sweep covered `README.md`
  and all of `docs/guide/`. It did not. `multi-repo.md`'s `## Connected
  projects` — 159 lines, the largest section in either tree, answering six
  separate reader questions — was missed by me and by both advisors, all three
  of us on the same unexamined instinct that its parts shared a subject and were
  therefore fine. I found it only by printing every section with its line count
  and reading the outline as a reader would, which is the check that should have
  come first rather than last.

  **The root cause was that the spec had no stated rule.** Without one, "does
  this heading swallow something?" is taste, and taste agreed with itself three
  times. The rule now in the spec — a heading must describe its entire span, and
  within it a passage needs its own entry when it answers a question the heading
  does not pose, with length explicitly not the test — was written after the
  fact, and immediately paid for itself: the verifier used it to find that the
  spec was breaking its own rule by excluding a five-line claim-recovery
  paragraph on length grounds. Three further headings followed from the same
  reading, and a fourth from an advisor finding I had left unactioned twice.

  Ten of the twenty-three headings exist because of work done after the spec was
  committed. A spec that states its criterion up front would have found most of
  them in the first pass.

- **The plan's proof for Task 1 named the wrong baseline count.** It said
  `work.md` would show "nineteen `##` headings where there were twelve" only
  after a correction; the first draft said thirteen, having counted the `#`
  title as a `##`. Caught by running `grep -c` before committing the plan rather
  than after. It is the kind of number that is never checked once it is written
  down, which is the argument for making every proof a command rather than a
  claim.

- **Acceptance criterion 5 as first written was not achievable and had to be
  reworded before the spec was committed.** It said `pnpm prettify:check`
  passes. That command fails on 168 files at `3a063f6f` — test fixtures and
  `web/client` sources inside the formatting surface that are not formatted —
  so the criterion would have failed on a tree this item never touched. It was
  narrowed to `pnpm prettier --check README.md 'docs/guide/**/*.md'`, which is
  clean at `3a063f6f` and therefore actually tests something this item can
  break. The 168-file failure went to the follow-up item. This is the one case
  where the spec stage's instruction to run every executable criterion before
  committing caught a criterion that would have been unfalsifiable in the wrong
  direction.

- **`outcome.md` itself carried stale counts through two revisions** and was
  corrected only when the verifier listed them. It said thirteen headings after
  the count had reached twenty-two. A document that records what shipped is the
  one document where a stale number is not a cosmetic problem.

- **The spec's claim that the sweep was repo-wide is narrower than it sounds.**
  It covered `README.md` and `docs/guide/`, which is where the request pointed.
  It did not sweep `skills/`, `docs/lifecycle/`, or the migration guides, all of
  which are Markdown with headings. That was deliberate — the request is about
  the user-facing documentation the README split produced — but the spec says
  "repo-wide by default" in the abstract and then does not say it narrowed.
  Stated here rather than left to a reader to notice.

## Notes

- **The item's premise was stale and this is a reinterpretation.** The request
  names `README.md:605`, which has not existed since the README was split from
  ~1150 lines to 423. The spec's Problem section is where that is argued out:
  the defect survived the split rather than being fixed by it, and three of the
  six topics the request listed as swallowed — the board, the JSON projection,
  descendants — were still swallowed at `3a063f6f`, under
  `## Automation and piping` instead of under a lifecycle-hooks heading. Had the
  split actually fixed them, closing the item would have been the right answer.
- **`initial-request.md` was deliberately not rewritten** to cite lines that
  exist today. One advisor recommended refreshing it. The request records what
  was asked when it was asked; editing it to match the tree would erase the
  evidence that the premise moved, which is the most interesting thing about
  this item.
- **The headings' names are the residual risk.** Criteria 2 and 3 prove
  mechanically that no prose moved. Nothing proves
  `## What the commands print` is a good name for `work.md:325-338`. That needs
  a person reading the outline against the prose.
