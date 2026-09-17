# Plan: Fix the guide's taxonomy example and a stale README citation

A small change, so the plan is compressed: two edits and a documentation pass.
Work directly on `main` in the primary checkout; nothing here needs a worktree.

## Tasks

1. **Make the guide's examples run.** Modify
   `docs/guide/taxonomy-and-capabilities.md`:
    - taxonomy block: add `tcw taxonomy add Admin "Running the service."` before
      the `Permission -p admin` line, and `tcw taxonomy add User "A person who
      signs in."` before the `--vocab user` line, keeping the column alignment of
      the comments;
    - capabilities block: change `--field "Subject=invoice,billing"` to
      `--field "Subject=invoice,admin/permission"`, which keeps two values and
      names two terms the taxonomy block created.

   Proof: acceptance criterion 1, run in a scratch directory by extracting the
   lines with `grep '^tcw taxonomy'`/`grep '^tcw capabilities'` from those blocks
   (excluding `extends`) and running each, stopping on the first non-zero exit.
   Also re-run the README's taxonomy block the same way (criterion 4).

2. **Point the two comments at the guides.** Modify `tcw/store/fs.py`:
    - `:4964` "the migration the README describes" → "the migration
      `docs/guide/work.md` describes under \"What happens to resolved work\"";
    - `:290` "which `README.md` promises does not happen" → "which
      `docs/guide/multi-repo.md` promises does not happen".

   Proof: criteria 2 and 3 by `git grep -n README tcw/` and reading the cited
   passages; `pytest -q` stays green.

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change] — fires on the `tcw/` edit even
  though it is comment-only; add one `Fixed` line for the guide's examples.
- `docs/release-notes/upcoming.md` [Public-API] — does not fire; no command's
  behavior or surface changes.
- `README.md` [Public-API] — does not fire; its example already runs.
- `docs/guide/jira.md`, `skills/<component>/SKILL.md`,
  `skills/configure/references/*` — do not fire.

## Verification

- The suite cannot check that a guide's example runs; task 1's scratch-project run
  is that check and is repeated at verify.
