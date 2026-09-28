# Rework

Verification (2026-09-27) met criteria 1–11 but found five defects. The user
chose to send the item back and fix all five here rather than split them out.

1. **A cut can fail halfway.** `combine_upcoming` runs `git rm` on each entry
   file after the version files and `v{version}.md` are already written. `git rm`
   refuses a tracked file with uncommitted edits ("has local modifications") and
   an untracked file ("pathspec did not match"), leaving no commit, no tag and a
   changed tree. Fix: remove with `git rm -q -f --ignore-unmatch`, then delete any
   file still on disk, so the release commit carries the entries as they are on
   disk (what the old `git mv` did for an edited `upcoming.md`). Add a test for
   each case, asserting the cut commits, tags and leaves a clean tree.
2. **Two places still say "rotates".** `docs/releasing.md:6` and
   `tcw/work/procedures/documentation-sync.md:48` (the `cut-version.md` row).
   Reword both for combining.
3. **Empty sections ship as bare headings.** A heading no file gives content to
   produces `## Added` with nothing under it. Drop such sections when combining;
   add a test. Update `cut-version.md` Step 2 to say so.
4. **A `## ` line inside a code block is taken as a heading.** Do not teach the
   script about code blocks; add one sentence to the entry rules in
   `release-notes-and-changelogs.md` (and the folder READMEs) saying so.
5. **Files the cut ignores are left silently.** A non-`.md` file, or anything in
   a subfolder of `upcoming/`, stays behind with no word. Print a warning naming
   them (to standard error) and carry on; add a test. Mention it in
   `cut-version.md` Step 2.
