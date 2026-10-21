# Plan — docs/use-cases.md

1. Write `docs/use-cases.md` (Design 1). For each stated behavior, cite the
   file that shows it: `tcw/store/fs.py` (`find_project_root`),
   `tcw/work/open.py` (delegation checks), `tcw/work/jira/tickets.py`,
   `docs/guide/multi-repo.md`, `docs/guide/jira.md`.
2. Add `## Use cases` to both spec templates (Design 2), and to this item's
   own spec.
3. Add the documentation entry and update `DOCUMENTATION` in
   `tests/test_repo_lifecycle.py` (Design 3).
4. Point to the document from `CLAUDE.md` (Design 4).
5. Changelog entry (Any-Code-Change does not fire, since no code changes, but
   a `docs/changelogs/upcoming` "Internal" entry records the process change).
   No release note: nothing changes for users.
6. Targeted tests (`tests/test_repo_lifecycle.py`), `tcw validate`, then bare
   `pytest`.
7. A read-only reviewer checks every behavior the document states against the
   code.
