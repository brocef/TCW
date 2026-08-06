# Outcome: gitignore resolved work folders at init by default

Built as specced, plus two bugs the new default exposed.

## What landed

- `tcw/store/fs.py` — `ensure_ignored(node_root, *lines) -> bool` extracted from
  `ensure_worktree_ignored` (which keeps its `git_stage` on True);
  `resolved_ignore_rules()` derived from `RESOLVED_STATUSES`; `init` calls it
  once per node when scaffolding `work`, unstaged.
- `tcw/cli.py` — `run_init` prints the exclusion when `work` is scaffolded.
- `tests/test_smoke.py` — `test_init_ignores_resolved_work_folders` (rules
  present once after two runs, pre-existing `.gitignore` content kept, item
  folder ignored, `.gitkeep` not, `backlog/` untouched) and
  `test_init_without_work_writes_no_gitignore`.
- `.gitignore` — this repo moved to the `<dir>/*` + `!.gitkeep` form; both
  `.gitkeep` files are back in the index.
- Capabilities `cli/scaffold-the-doc-trees` and
  `work/keep-resolved-work-out-of-git` reworded; both remain `Supported`.
- Docs: `README.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `skills/tcw-work/references/transitions.md`.

## Deviations from the plan

Two failures appeared once the test nodes started ignoring their resolved
folders by default — both real defects on the ignored path, not test artifacts,
and both fixed at the shared helper rather than at the caller:

1. **`git_stage` on an ignored path aborts.** `git add` errors on an ignored
   pathspec rather than no-opping, so `reconcile` staging an epic's artifact
   after the epic had moved into `completed/` blew up
   (`test_epic_completable.py`). `git_stage` now filters ignored paths and
   no-ops when nothing is left.
2. **`git rm --cached` refuses a path staged with different content.** A
   transition stages the item's own state before moving it, so the index differs
   from both HEAD and the worktree — `git rm` demands `-f` for that. Surfaced as
   a 500 on discard through the `tcw serve` API
   (`test_serve_write.py`). `git_mv`'s untrack branch now passes `-f`;
   `--cached` still means the files stay on disk.

## Out of scope, fixed anyway

`tests/test_skill_lifecycle_parity.py::test_the_router_stays_within_its_line_budget`
was already failing on `main`: `skills/tcw-work/SKILL.md` was 62 body lines
against a budget of 60, grown by `69eeb0a` (lifecycle document tabs). Unrelated
to this item — the edit here went into `references/transitions.md`, which the
budget does not cover — but it blocks the version cut, so the web-editing note
was condensed back to two lines in its own commit.
