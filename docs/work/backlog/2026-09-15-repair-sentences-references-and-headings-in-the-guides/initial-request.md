# Repair misplaced sentences, broken references and overloaded headings in the guides

## What is wanted

`docs/guide/` should contain no duplicated sentence, no cross-reference that points the
wrong way or nowhere, no section describing repository-wide contributor tooling from
inside a document about one feature, and no heading that covers two or three separate
questions. These were found by the heading sweep, which could only insert headings and
so could not fix them.

1. **`configuration.md`** — a four-line tail under "Declaring which documents track which
   changes" that repeats the file's opening almost word for word and holds a sentence
   about hooks (`tcw serve` runs none) that belongs under "How bindings run".
2. **`taxonomy-and-capabilities.md`** — "see `tcw capabilities` above", but that section
   is below.
3. **`web-viewer.md`** — a same-page link to a heading that lives in
   `linking-and-validation.md`, so it resolves to nothing.
4. **`web-viewer.md`** — documents `pnpm prettify` and `pnpm prettify:check` (repository-wide
   contributor formatting) in the web viewer guide, and states its opening sentence twice.
5. **References whose antecedent moved** — in `work.md` ("Pass `-i` …" with no command
   named; "the same `--status` / `--all` filters"; "the legal transitions above"),
   `multi-repo.md` ("the one thing that relaxes with it"), and a borderline case in
   `multi-repo.md` that may need nothing.
6. **Headings that pose several questions or run long** — six joined headings (clearest:
   "Checking a stage, reading its instructions, and starting its document", 71 lines),
   `work.md`'s "What happens to resolved work" (78 lines, including a 31-line block on the
   auto-delete hook), `multi-repo.md`'s "Where a component store lives" (70 lines), and two
   `multi-repo.md` sections that open with the same clause.

## Constraints

- **Blocked by the README rewrite**
  (`2026-09-15-rewrite-the-readme-to-a-new-outline`, active on its worktree). It
  requires `web-viewer.md` to stay byte-identical, rewrites `work.md`'s tracker section,
  and gives contributor tooling a home in the README's Development section — which is the
  destination part 4 lacked. Start after it lands, and re-check line positions then.
- **Part 6 needs an agreed stopping point before it starts.** The heading sweep took three
  review rounds, each finding holes in the previous round's fixes, and stopped
  deliberately. A heading standing in for a move is not a repair (tried and reverted for
  the "legal transitions above" paragraph).
- Parts 1 to 5 do not reopen the headings the sweep inspected and left alone on purpose;
  its spec lists them with reasons.

## Out of scope

- `pnpm prettify:check` failing (part 7 of the entry) — tracked in
  `2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout`.
- `README.md`'s "ship alongside them" reference (part 5) — the README rewrite replaces the
  file.

## Notes

- The entry recommended splitting parts 1–5 and part 6; they were kept together at triage
  under the maintainer's rule of combining changes to the same documents.
- Checked at triage on `main`: every defect in parts 1–6 is still present; the
  `web-viewer.md` link is the only broken anchor across `README.md` and `docs/guide/`.
- Part 4's destination (the README's Development section) is inferred from the README
  rewrite's spec, not stated by the maintainer.
- Reference material: asked; none provided.

## References

- `docs/work/completed/2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document/` —
  the sweep that found these; its spec records the rule for when a heading swallows
  something and the sections deliberately left alone.
- `docs/work/active/2026-09-15-rewrite-the-readme-to-a-new-outline/spec.md` — criterion 13
  and Design § 2, which set the blocking constraints above.

## Note (2026-09-24 backlog cleanup)

The README rewrite this waited on is done, so the blocker was removed. Part 4 is now only deleting the `pnpm prettify` copy from `docs/guide/web-viewer.md`: the README Development section already documents it. Line numbers in the intake have moved.
