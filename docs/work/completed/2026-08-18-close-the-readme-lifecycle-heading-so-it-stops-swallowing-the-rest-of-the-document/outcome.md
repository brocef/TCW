# Outcome — Close the headings that swallow the rest of the document

Twenty-four headings inserted across five documents. No prose edited, moved, or
removed anywhere.

The count grew from thirteen during implementation and three rounds of review,
and one heading added in review was reverted in the same review. Eleven of the
twenty-four were found after the spec was first committed. How that happened is
the most useful thing in this document — see *What the plan and spec got
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
| — | `3e32ab20` | `outcome.md` brought to twenty-three after the verifier found it stale |
| — | `62a4e39f` | The README's longest section recorded as inspected and left alone |
| — | `90cabfd0` | Round three: one heading reverted, two added, the rule's escape hatch named |
| — | `2955e052` | The length floor replaced with the test that actually decided |
| — | `46a83c36` | The borderline back-reference recorded rather than dropped |

Every insertion went in bottom-up within its file, through one script that
refuses unless the target line starts with an expected prefix, so a shifted line
number fails loudly rather than putting a heading in the wrong place.

## Acceptance criteria

All eight pass. Output is from runs made against `4029d417`.

1. **Twenty-four headings present, each before the span named.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep -cE '^\+#{2,3} '`
   returns 24, and a script reconciling the Design table against the tree
   reports no row without a heading and no heading without a row. By file:
   `README.md` 1, `configuration.md` 2, `taxonomy-and-capabilities.md` 2,
   `work.md` 11, `multi-repo.md` 8.
2. **No prose removed.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^-[^-]' | grep -v '^-$'`
   prints nothing.
3. **Nothing but headings and blank lines added.**
   `git diff -U0 3a063f6f -- README.md docs/guide/ | grep '^+[^+]' | grep -vE '^\+(#{2,3} |$)'`
   prints nothing.
4. **`configuration.md:1-93` byte-identical** to `3a063f6f`. `diff` is empty.
5. **`pnpm prettier --check README.md 'docs/guide/**/*.md'`** — "All matched
   files use Prettier code style!"
6. **`python -m pytest -q`** — `2594 passed in 944.25s`, run at `90cabfd0`. The
   `3a063f6f` baseline was `2594 passed in 957.16s`, run before the spec was
   committed. Same count. The two commits after `90cabfd0` touch only
   `docs/work/`, and the five suites that read any file under `README.md`,
   `docs/guide/` or `docs/work/` were re-run at `46a83c36`: `295 passed in
   6.10s`.
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
  `## What the commands print` is a good name for its span. That needs a person
  reading the outline against the prose, which is what three review rounds
  supplied and what a fourth would have supplied again.
- **The sweep is deliberately unfinished, and the user set the line.** Rounds
  two and three each found holes in the previous round's fixes rather than in
  the original work, so the item stopped at the reviewer's own
  belongs-to-this-change list rather than run a round four. Thirteen findings
  went to `docs/work/inbox/2026-09-11-prose-defects-the-heading-sweep-found.md`,
  including six conjunctive headings this change created, two sections over
  seventy lines the sweep never examined, and five references whose antecedent a
  new heading moved into another section. Anyone picking that up should agree a
  stopping point before starting.


## Autonomous decisions

One line per consult. Each names the question, what each advisor said, the
choice, and why.

1. **The request names `README.md:605`, which no longer exists. Close as already
   fixed, carry it forward, or return to the `request` stage?** Codex: carry it
   forward, the split removed the reported instance but the sweep clause
   survives. Opus: carry it forward, closing would record a false claim. Chose
   carry forward. Both agreed, and the evidence was independent of either: three
   of the six topics the request named as swallowed were still swallowed at the
   base commit.

2. **Should the board and the JSON projection get a heading out of
   `## Automation and piping`?** Codex: yes. Opus: no, machine-readable output
   for scripts is what "automation and piping" means. Split, taking Codex. Opus's
   argument covers `--json` but not `tcw work list`, which is the human view, not
   machine output — and the original request named the board explicitly.

3. **Should the prose defects found alongside be fixed here?** Codex: no,
   heading-only. Opus: yes, two sentences of work. Deferred them, taking Codex.
   The zero-deletion diff check is the only mechanical proof the request's
   "without reflowing the content itself" was honoured; folding prose edits in
   destroys it.

4. **`## Connected projects` is 159 lines and neither advisor flagged it. Split
   or leave?** Codex: split at four points, deciding reason discoverability not
   length. Opus: split at five points, adding one for orphaned locator
   mechanics. Split at six, taking Opus's extra boundary and adding one more, so
   each span answers one question rather than relying on a compound heading.
   Codex also supplied the rule that went into the spec.

5. **Where does the review loop stop?** Round three found holes in round two's
   fixes. The reviewer sorted its findings into belongs-to-this-change and
   needs-a-separate-change, per this repository's standing rule, and ended
   NOT DONE. Put the split to the user rather than deciding alone, because that
   rule says to. The user chose: apply the confirmed defects, file the rest.
   Done exactly that.

6. **The verifier said one left-alone call contradicted the spec's own rule.**
   No advisor split. Accepted and reversed: the exclusion rested on a five-line
   length argument, and the rule I had just written says length is not the test.

7. **Reviewer said to revert a heading I had added one round earlier.** No
   advisor split. Accepted. Three lines of prose promoted to a section is a
   heading standing in for a prose move, which this item ruled out.

### What I would have asked about if I could

- Whether `## Command reference` at 84 lines of prose should stay one section.
  It is exempted in the spec on the grounds that it answers one question, which
  is true, but it is also the section a reader is most likely to want an outline
  into. That is a preference about how the guide is read, not a defect.
- Whether the deferred prose repairs are worth an item at all, or whether the
  guide should absorb them the next time someone edits those files.
