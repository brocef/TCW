# Outcome — Close the headings that swallow the rest of the document

Thirteen headings inserted across five documents. No prose edited, moved, or
removed anywhere.

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

Every insertion went in bottom-up within its file, through one script that
refuses unless the target line starts with an expected prefix, so a shifted line
number fails loudly rather than putting a heading in the wrong place.

## Acceptance criteria

All eight pass. Output is from runs made against `4029d417`.

1. **Thirteen headings present, each before the span named.** `grep` over
   `README.md` and `docs/guide/*.md` returns exactly thirteen matches:
   `configuration.md:94, :165`; `multi-repo.md:316, :327`; `README.md:386`;
   `taxonomy-and-capabilities.md:56`; `work.md:325, :340, :377, :386, :397,
   :422, :565`.
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
