# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- `git_mv` (`tcw/store/fs.py`) now checks whether the destination is gitignored.
  `git mv` does not consult `.gitignore` for its destination, so a node that
  ignored a status folder had every transition into it stage — and commit — the
  file at the supposedly-ignored path. An ignored destination now drops the
  source from the index (`git rm --cached --ignore-unmatch`) and moves it with
  `shutil.move`; the scoped transition commit records the deletion, and
  `git_commit_result`'s existing empty-pathspec filter drops the destination.
  Reached by `_effect_transition` and by re-parenting alike. Unignored
  destinations are unchanged.

## Internal

- `.gitignore`: `docs/work/completed/` and `docs/work/discarded/` — this repo's
  own dogfooding history is no longer carried in the tracked tree. Existing
  folders untracked with `git rm -r --cached`; nothing was rewritten out of
  history.
- Scrubbed a private project's name from `docs/plan/` prose and from the quoted
  repro material in two backlog items, which now use `example-*` placeholders.
