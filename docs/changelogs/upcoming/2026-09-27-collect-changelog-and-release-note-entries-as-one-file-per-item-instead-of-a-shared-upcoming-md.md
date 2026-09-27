## Changed

- `scripts/cut_version.py` combines `docs/{changelogs,release-notes}/upcoming/*.md`
  (every file except `README.md`, in file-name order) into each folder's
  `v{version}.md` instead of rotating a single `upcoming.md`. `## ` sections with
  the same heading merge; the changelog leads with Added, Changed, Fixed,
  Removed, Internal, and other headings follow in first-appearance order. Entry
  files are `git rm`ed in the release commit. `rotate_upcoming` is replaced by
  `combine` and `combine_upcoming`; the cut aborts before touching anything if an
  `upcoming/` folder is missing.
- This repo's `work.documentation` entries now name
  `docs/{changelogs,release-notes}/upcoming/<slug>.md`; the two `upcoming.md`
  files moved to `upcoming/2026-09-27-carried-over.md`, and each folder gained a
  `README.md` with the drafting guidance.
- `documentation-sync` skill: `references/release-notes-and-changelogs.md`
  teaches one entry file per change (named by work item slug, `##` headings, no
  `#` title), rewrites the version cross-check for folders, and adds a section
  and migration row for projects still on a single `upcoming.md`.
  `references/cut-version.md` Step 2 and the fold into an unpushed version
  describe the combining rules. `SKILL.md`, the `documentation-sync` and
  `unattended-work` procedures, and `configure`'s `references/docs-sync.md`
  follow.

## Internal

- `tests/test_cut_version.py` covers merging by heading, heading order, `###`
  subsections, text before the first heading, an empty folder, the README never
  shipping, and a missing folder aborting. The eval fixture deliberately stays
  on a single `upcoming.md` (eval B10 lists exact changed paths).
