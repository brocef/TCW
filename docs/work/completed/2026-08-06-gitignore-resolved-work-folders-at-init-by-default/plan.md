# Plan: gitignore resolved work folders at init by default

1. **`tcw/store/fs.py` — the helper.** Extract the append-if-missing body of
   `ensure_worktree_ignored` into `ensure_ignored(node_root, *lines) -> bool`
   (True when it wrote). `ensure_worktree_ignored` becomes a two-line caller that
   stages on True.

2. **`tcw/store/fs.py` — `init`.** When `c == "work"`, call `ensure_ignored` with
   the comment line plus, for each status in `RESOLVED_STATUSES`,
   `docs/work/<status>/*` and `!docs/work/<status>/.gitkeep`. No staging.

3. **`tcw/cli.py` — `run_init`.** When `work` is among the components, print one
   line stating that the resolved folders are excluded in `.gitignore`.

4. **`tests/test_smoke.py`** (or the file that already covers `init`) — one test
   over a `tmp_path` git repo: rules present, `check-ignore` behavior for an item
   folder vs `.gitkeep`, re-run does not duplicate, `taxonomy`-only init writes
   no `.gitignore`, and pre-existing `.gitignore` content survives.

5. **This repo.** Replace the two trailing-slash lines in `.gitignore` with the
   new four, `touch docs/work/discarded/.gitkeep`, and `git add` both `.gitkeep`
   files.

6. **Capabilities.** Reword `work/keep-resolved-work-out-of-git` (setup is now
   the default, manual `git rm --cached` only for a pre-existing node) and add a
   sentence to `cli/scaffold-the-doc-trees`. Both stay `Supported`.

7. **Docs sync** — run the `documentation-sync` skill. Expected to fire:
   `README.md` (the `tcw init` / `tcw work init` sections),
   `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, and
   `skills/tcw-work/references/transitions.md` (the ignored-destination
   paragraph now describes a default rather than an opt-in).

8. **Verify** — `pytest`, `tcw validate`, and the criterion-6 `git ls-files`
   checks.
