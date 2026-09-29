# Plan — Resolve project-graph paths regardless of letter case and through a symlinked config

## Tasks

1. **Failing tests** — `tests/test_project_graph_paths.py`, reusing
   `tests/test_worktree_sibling_nodes.py`'s `repo`, `config`, `git`, `validate`
   and `workspace`. Criteria 1–4 red today (1 skipped on a case-sensitive disk).
2. **Code** — `tcw/store/project.py`: `_config_file`, `_canonical`, the call
   sites named in the spec's sweep, `_probe_worktree`.
3. **Full suite.**

## Documentation Sync

- `docs/guide/multi-repo.md` [Guide-Topic-Change]: worktree resolution now
  covers submodules; a symlinked `tcw-config.yaml` belongs to its folder.
- `docs/changelogs/upcoming/<slug>.md`, `docs/release-notes/upcoming/<slug>.md`.
- Not firing: README, skills, configure references (no key or command change).

## Verification

Each criterion by its test; hands-on: the two reproductions from the request.
