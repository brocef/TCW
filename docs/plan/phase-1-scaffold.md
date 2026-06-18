# Phase 1 — Scaffold

**Status:** ☐ not started
**Delivers:** a `pip install -e .`-able `tcw` package with the CLI skeleton, the abstract store base, and `tcw init`.
**Depends on:** nothing (this is the entry point).
**Unblocks:** Phase 2 (taxonomy) and Phase 3 (work) both build on the package + store base laid down here.

The bootstrap that turns this planning repo into a working Python project. (Folds in the old `PLAN.md` checklist.)

## Repo scaffolding

- [ ] `README.md` — what TCW is, install, quickstart.
- [x] `AGENTS.md` (+ `CLAUDE.md` symlink) — present; carries the prime directive.
- [x] `LICENSE` — present.
- [ ] `.gitignore` (Python).
- [ ] `CHANGELOG.md` — single changelog (the decided docs convention; no release-notes/changelogs split until there's something to release).

## Python package

- [ ] `pyproject.toml` — package `tcw`; console entry point `tcw = tcw.cli:main` so `tcw` lands on `PATH` via `pip install -e .` / `pipx`. Runtime dep: `PyYAML`. Dev: `pytest`.
- [ ] Package layout:
  ```
  tcw/
    __init__.py
    cli.py            # top-level argparse; dispatches `tcw taxonomy | capabilities | work | init`
    store/
      base.py         # abstract store interface(s); the shared tree-store core lands here LATER (Phase 4)
      fs.py           # FsTaxonomyStore, FsWorkStore, FsCapabilitiesStore as each phase adds them
    taxonomy/         # Phase 2
    work/             # Phase 3
    capabilities/     # Phase 5
  tests/              # pytest over tmp_path git repos
  ```
  *(Per `AGENTS.md`: do **not** pre-abstract a shared tree-store core now. `store/base.py` starts with only what Phase 2 needs; the common primitive is extracted in Phase 4 once two components are real.)*

## CLI skeleton + `tcw init`

- [ ] `tcw.cli:main` — top-level argparse with subcommand groups `taxonomy`, `capabilities`, `work`, and `init`. Groups for unbuilt components can stub to "not yet implemented" until their phase lands.
- [ ] **`tcw init`** — the **unified scaffolder** (resolves the taxonomy-spec open question "`tcw taxonomy init` vs a unified `tcw init`"). Scaffolds whichever component trees you name (`tcw init taxonomy work`), defaulting to all three: creates `docs/taxonomy/`, `docs/capabilities/`, and `docs/work/{inbox,backlog,active,blocked,completed}/` skeletons in the current git work-tree. Refuse outside a git repo (suggest `git init`).
- [ ] **Node detection** (shared by every component): walk up from cwd to the nearest git work-tree containing the component's `docs/<component>/` dir; operate there. Bounded to that node (do not descend into a child node's dirs).

## Distribution

- [ ] `pipx install` from this repo/git, exposing `tcw` on `PATH`. Native Python packaging — no symlink hack (that was the broker CLI's workaround for a non-packaged script; `tcw` is a real package).

## Hygiene (can trail the first components)

- [ ] CI running `pytest`; semver tags; push to `origin` (a remote already exists).

## Done when

`pip install -e .` puts `tcw` on `PATH`; `tcw init` scaffolds the three component dirs in a fresh git repo; `tcw --help` lists the four subcommand groups; `pytest` runs green (even if only a smoke test exists).
