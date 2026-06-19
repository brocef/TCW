# Phase 1 — Scaffold

**Status:** ✓ built (see *Build notes* below)
**Delivers:** a `pip install -e .`-able `tcw` package with the CLI skeleton, the abstract store base, and `tcw init`.
**Depends on:** nothing (this is the entry point).
**Unblocks:** Phase 2 (taxonomy) and Phase 3 (work) both build on the package + store base laid down here.

The bootstrap that turns this planning repo into a working Python project. (Folds in the old `PLAN.md` checklist.)

## Repo scaffolding

- [x] `README.md` — what TCW is, install, quickstart.
- [x] `AGENTS.md` (+ `CLAUDE.md` symlink) — present; carries the prime directive.
- [x] `LICENSE` — present.
- [x] `.gitignore` (Python).
- [x] `CHANGELOG.md` — single changelog (the decided docs convention; no release-notes/changelogs split until there's something to release).

## Python package

- [x] `pyproject.toml` — package `tcw`; console entry point `tcw = tcw.cli:main` so `tcw` lands on `PATH` via `pip install -e .` / `pipx`. Dev: `pytest`. *(`PyYAML` deferred — Phase 1 parses no front-matter; added in Phase 2 where it's first imported.)*
- [~] Package layout:
  ```
  tcw/
    __init__.py
    cli.py            # top-level argparse; dispatches `tcw taxonomy | capabilities | work | init`
    store/
      base.py         # abstract store interface(s); the shared tree-store core lands here LATER (Phase 4)
      fs.py           # FsTaxonomyStore, FsWorkStore, FsCapabilitiesStore as each phase adds them
    taxonomy/         # Phase 2
    capabilities/     # Phase 3
    work/             # Phase 5
  tests/              # pytest over tmp_path git repos
  ```
  *(Per `AGENTS.md`: do **not** pre-abstract a shared tree-store core now. `store/base.py` starts with only what Phase 2 needs; the common primitive is extracted in Phase 4 once two components are real.)*

## CLI skeleton + `tcw init`

- [x] `tcw.cli:main` — top-level argparse with subcommand groups `taxonomy`, `capabilities`, `work`, and `init`. Groups for unbuilt components stub to "not yet implemented" until their phase lands.
- [x] **`tcw init`** — the **unified scaffolder** (resolves the taxonomy-spec open question "`tcw taxonomy init` vs a unified `tcw init`"). Scaffolds whichever component trees you name (`tcw init taxonomy work`), defaulting to all three: creates `docs/taxonomy/`, `docs/capabilities/`, and `docs/work/{inbox,backlog,active,blocked,completed}/` skeletons in the current git work-tree. Refuses outside a git repo (suggest `git init`). *(Implemented as `tcw.store.fs:init` — directory scaffolding is an FS-adapter detail by the litmus test.)*
- [~] **Node detection** (shared by every component): walk up from cwd to the nearest git work-tree containing the component's `docs/<component>/` dir; operate there. Bounded to that node (do not descend into a child node's dirs). *(Phase 1 ships `git_root()` — the git-work-tree resolution `init` needs. The component-dir-aware `find_node()` lands in Phase 2, the first phase with a component operation that must resolve a node.)*

## Distribution

- [x] `pipx install` from this repo/git, exposing `tcw` on `PATH`. Native Python packaging — no symlink hack (that was the broker CLI's workaround for a non-packaged script; `tcw` is a real package). *(Verified via `pip install -e .` — same console-entry mechanism pipx uses.)*

## Hygiene (can trail the first components)

- [ ] CI running `pytest`; semver tags; push to `origin` (a remote already exists).

## Done when

`pip install -e .` puts `tcw` on `PATH`; `tcw init` scaffolds the three component dirs in a fresh git repo; `tcw --help` lists the four subcommand groups; `pytest` runs green (even if only a smoke test exists).

## Build notes (Phase 1)

All four "Done when" criteria verified: editable install puts `tcw` on `PATH`, `tcw init` scaffolds `docs/{taxonomy,capabilities,work/…}` in a fresh repo, `tcw --help` lists the four groups, and `pytest` is green (5 tests in `tests/test_smoke.py`).

Files shipped: `pyproject.toml`, `tcw/{__init__,cli}.py`, `tcw/store/{__init__,fs}.py`, `tests/test_smoke.py`, plus `README.md`, `CHANGELOG.md`, `.gitignore`.

**Deliberately deferred (YAGNI — nothing in Phase 1 exercises them):**
- `tcw/store/base.py` — no abstract operation exists yet. The `TaxonomyStore` ABC is introduced in **Phase 2**; the shared tree-store core is extracted in **Phase 4** (per AGENTS.md: don't pre-abstract).
- Component packages `tcw/taxonomy/`, `tcw/capabilities/`, `tcw/work/` — created by their own phases when they hold real code. The CLI stubs "not yet implemented" inline, so empty packages aren't needed now.
- `PyYAML` dependency — added in Phase 2 (front-matter parsing) where it's first imported.
- `find_node()` (component-dir-aware node detection) — Phase 2, the first node-resolving component op. `git_root()` ships now because `init` needs it.
- CI / semver tags / push — *Hygiene*; explicitly "can trail the first components".
