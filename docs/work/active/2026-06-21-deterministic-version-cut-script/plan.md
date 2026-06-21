# Plan — Deterministic version-cut script

TDD: failing test first, then minimal code.

1. **`tests/test_cut_version.py`** (load the script by path)
   - `next_version`: patch/minor/major increments; explicit `X.Y.Z`;
     invalid bump → SystemExit.
   - `current_version`: reads agreeing version; drift → SystemExit.
   - `bump_files`: all 5 files updated; a file with no/!=1 match → SystemExit.
   - end-to-end `main(["patch"], root=tmp_repo)`: versions bumped, `v{new}.md`
     hold the old upcoming content, fresh `upcoming.md` reset, commit + tag made.

2. **`scripts/cut_version.py`**
   - Pure fns + `main`; shebang; `if __name__ == "__main__": main()`.

3. **Docs sync**
   - `CLAUDE.md` Versioning section → "cut a release with `python
     scripts/cut_version.py <bump>`".
   - `docs/changelogs/upcoming.md` (Internal). No release-note (no user-facing
     change); no README (no public CLI change).
