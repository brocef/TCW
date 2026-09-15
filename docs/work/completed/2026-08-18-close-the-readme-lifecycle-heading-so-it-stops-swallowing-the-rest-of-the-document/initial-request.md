# Close the README lifecycle heading so it stops swallowing the rest of the document

Filed by the C8 audit of
`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`. Pre-dates the
epic; surfaced by C7 (`2026-08-12-repoint-the-work-skill-and-docs-at-the-cli`)
while establishing that section's real bounds, and recorded in its
`refined-outcome.md`.

## Product changes

`README.md:605` opens `### Binding your own skills and commands to the
lifecycle`. **The next `###` is at `:1102`** — verified: it is the only `###`
between lines 590 and 1150.

Everything from roughly `:737` to `:1017` therefore renders *inside* that
heading, in any Markdown viewer and in GitHub's own outline: transition commits,
the Definition of Done, the whole `tcw work` command listing, the board, the
JSON projection, descendants, and decomposition. None of it is about binding
skills or commands to anything.

A reader who opens the README's outline sees the command reference filed under a
section about lifecycle hooks. A reader who follows the heading expecting the
hook documentation to end finds it never does.

## Technical changes

Insert the missing heading (or headings) so the trailing material sits under an
accurate one, without reflowing the content itself. **The section's actual
content — `:605` to `:735`, ending at the paragraph "…does not block it from the
web app" — was rewritten by C7 and should not be re-touched.**

Check whether any other `###` in the README has the same problem while in the
file; this one was found by measuring one section's bounds, not by looking.

## Meta changes

None.

## References

- `docs/work/completed/2026-08-12-repoint-the-work-skill-and-docs-at-the-cli/refined-outcome.md`
  — where this was carried forward. Its `outcome.md` also notes this is why C6's
  plan appeared to contradict itself about which README lines were in scope.

## Notes

- Purely structural. No prose needs rewriting, which is what makes it small.
