# Refined outcome — Close the headings that swallow the rest of the document

**Accepted.** Twenty-four headings across five documents, no prose changed, all
eight acceptance criteria met.

## The verification decision

Taken autonomously, on three independent readings plus my own.

- **`tcw-verifier`** ran every mechanical criterion itself and substituted the
  295 tests that actually read these files for the sixteen-minute suite. It read
  each heading against its span, confirmed twenty-two of twenty-four were
  accurate, and named two it would word differently. Both were changed.
- **`adversarial-code-reviewer`** verified the no-prose-change claim
  independently rather than trusting the diff checks the spec names, and traced
  `README.md:605` back to the commit that existed on the filing date to test the
  premise. It ended NOT DONE, on its own belongs-to-this-change list and the
  unrun suite. Both are now cleared.
- **My own checks**: a script reconciling the spec's Design table against the
  tree, an anchor-slug and broken-link sweep across every Markdown file in the
  repository, an outline read of all five documents with per-section prose
  counts, and confirmation that nothing in `tcw/` or `tests/` parses these files
  by heading.
- **Full suite**: `2594 passed in 944.25s`, matching the `3a063f6f` baseline of
  `2594 passed in 957.16s`.

## What the acceptance is not

It is not a claim the sweep is finished. Thirteen findings were routed to a
follow-up item deliberately, including six conjunctive headings this change
created and two sections over seventy lines it never examined. The item is
accepted as a correct and complete execution of a scope that was consciously
narrowed, not as a document tree with no remaining heading defects.

## The one thing worth remembering

**The spec shipped without a criterion, and that cost three review rounds.**
"Does this heading swallow something?" was taste until the rule was written
down, and taste agreed with itself across me and two advisors — all three of us
walked past a 159-line section answering six questions, on the shared instinct
that its parts belonged to one subject.

Once the rule existed it caught the spec contradicting itself twice: first
excluding a paragraph on a length argument the rule forbids, then asserting a
floor the change itself violated. Its final form mentions length nowhere. A
passage earns a heading when no other section could hold it correctly, and does
not when the right answer is a prose move this item ruled out.

Eleven of the twenty-four headings were found after the spec was committed. A
spec that states its test up front would have found most of them in the first
pass. That is the transferable lesson, and it is why this document exists.

## Deferred, and why

- **Every prose-level repair**, to
  `docs/work/inbox/2026-09-11-prose-defects-the-heading-sweep-found.md`. The
  zero-deletion diff check is the only mechanical proof that "without reflowing
  the content itself" was honoured, and each of these breaks it. That includes
  the five references whose antecedent a new heading moved into another section
  — a defect class this change creates by construction, which the reviewer
  bounded at five by auditing all twenty-four.
- **Closing any originating GitHub issue.** There is none; this item was filed
  by an internal audit.
- **The version cut.** Per the run's standing instruction, the changelog entry
  accumulates in `upcoming.md` and no version is cut here.
