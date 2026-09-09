# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- **README.md restructured from a reference manual into an adoption pitch.**
  Reduced from 1628 to ~320 lines. The opening now leads with the problem, a
  runnable worked example across all three axes, the multi-repository case, an
  explicit adoption-cost section, and a corrected storage-abstraction claim; the
  reference material moved into `docs/guide/`. `Status` was rewritten from
  build-phase archaeology (“Phases 1–5”, “work Spec 2”) into a table of what is
  built and an explicit statement of what is not.
- **`tests/test_documented_cli_surface.py`** now checks `docs/guide/work.md`
  rather than `README.md` for `tcw work stage` and `tcw work scaffold`, matching
  where those verbs are now documented. The forward-direction check needs no
  change: `_doc_files()` discovers the new guides through `git ls-files`.

## Added

- `docs/guide/work.md`, `docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/multi-repo.md`, `docs/guide/configuration.md`,
  `docs/guide/web-viewer.md`, `docs/guide/linking-and-validation.md` — the
  reference material extracted from README.md, each with an H1 and cross-links.
- `docs/releasing.md` — the PyPI/Trusted-Publishing procedure, moved out of the
  README because it serves maintainers rather than users.

## Fixed

- **Restored the README's missing headings.** `### Declaring which documents
track which changes` opened at line 1084 and the next `###` was at 1432, so
  the entire `tcw work` command reference, the Definition of Done, transition
  commits, and tags rendered inside a section about documentation entries — in
  every Markdown viewer and in GitHub's outline. The extracted
  `docs/guide/work.md` gives that material its own headings. This is the defect
  filed as
  `2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document`,
  which had moved since it was filed but was still present.
- **Removed a contradiction between two README sections.** The storage-
  abstraction section claimed portability to external trackers “is what makes it
  viable at enterprise scale” while `Status` listed those adapters as unbuilt.
  The section now states plainly that only filesystem stores ship today.
