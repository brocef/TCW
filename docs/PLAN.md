# TCW — Taxonomy · Capabilities · Work

A filesystem-native (storage-abstracted) framework for describing and evolving a software project along three axes, defined in **dependency order** — also the `tcw` binary's three subcommand groups:

1. **Taxonomy** — the *things* a project deals with (domain entities). The **nouns**. → [`specs/2026-06-18-taxonomy-design.md`](specs/2026-06-18-taxonomy-design.md)
2. **Capabilities** — what those things can do / their states. The **behaviors**. *(component spec pending; exists today as co-located prose + a skill)*
3. **Work** — how those things and behaviors change over time. The **verbs**. → [`specs/2026-06-18-work-sdlc-design.md`](specs/2026-06-18-work-sdlc-design.md)

Taxonomy comes first because the other two reference it — a capability describes the behavior of *something*, and a work item changes *something*; that something is a taxonomy term. One binary, `tcw`, exposes all three over a shared store core.

The model is **storage-abstracted** (a filesystem default, but able to run against an external tracker). The prime directive — the abstraction litmus test — and the abstract-spine discipline live in [`../AGENTS.md`](../AGENTS.md); read it before changing any component's model.

## History

These specs were brainstormed inside the `skill-cefailures` repo and extracted here once the scope (a standalone CLI + framework) outgrew a plugin skill. The full design dialogue — the capabilities-absorption decision, the storage-abstraction reframe, a dual review (subagent + local model), and the taxonomy `extends` federation model — lives in that repo's git history. See [`DESIGN-HISTORY.md`](DESIGN-HISTORY.md) for the distilled design narrative and decision log.

---

## Standing up TCW as its own project

A checklist of what's needed to turn this planning repo into a working project.

### Repo scaffolding
- [ ] `README.md` — what TCW is, install, quickstart.
- [ ] `AGENTS.md` (+ `CLAUDE.md` symlink) — **done** (relocated and generalized from `skill-cefailures`'s `WORK-SDLC.AGENTS.md`); carries the prime directive.
- [ ] `.gitignore` (Python). `LICENSE` is already present.
- [ ] Decide the docs convention (the `docs/release-notes/` + `docs/changelogs/` + `docs/FOLLOWUPS.md` pattern from `skill-cefailures`, or simpler).

### Python package
- [ ] `pyproject.toml` — package `tcw`; console entry point `tcw = tcw.cli:main` so `tcw` lands on `PATH` via `pip install -e .` (or `pipx`). Runtime dep: `PyYAML`. Dev: `pytest`.
- [ ] Package layout:
  ```
  tcw/
    __init__.py
    cli.py            # top-level argparse; dispatches `tcw taxonomy | capabilities | work`
    store/
      base.py         # abstract store interface(s); the shared tree-store core
      fs.py           # FsTaxonomyStore, FsWorkStore
    taxonomy/         # the taxonomy spec
    work/             # the work-sdlc spec
    capabilities/     # later
  tests/              # pytest over tmp_path git repos
  ```

### Build order (per the specs)
- [ ] **Taxonomy** first (`tcw taxonomy` + `FsTaxonomyStore`) — fully specced, and the other two reference it.
- [ ] **Work** (`tcw work` + `FsWorkStore`) — also fully specced (the work-sdlc spec, Part B).
- [ ] Extract the shared tree-store core only once taxonomy + work both exist (don't pre-abstract).
- [ ] **Capabilities** (`tcw capabilities`) — after its component spec is written.

### Reframe carried over from the specs
- [ ] The moved specs still say `work …` / reference `WORK-SDLC.AGENTS.md`. Rename `work …` → `tcw work …` throughout the work-sdlc spec and point it at this repo's `AGENTS.md`; add the `tcw` umbrella entry point.
- [ ] The work-sdlc spec's "Spec 4 — Migration" (retire `FOLLOWUPS.md`, the `process-inbox` commands, the `capabilities-sdlc` skill) now targets **Proposit-App / `skill-cefailures` as a *consumer*** of `tcw`, not work done inside this repo.

### Distribution & the origin repo
- [ ] Decide how consumers get `tcw` on `PATH` (`pipx install` from this repo/git, or a symlink like `skill-cefailures`'s broker CLI).
- [ ] `skill-cefailures` becomes a **consumer**: its `capabilities-sdlc` skill's artifact docs fold into `tcw`'s capabilities component; its skill catalog references `tcw`.

### Hygiene
- [ ] CI running `pytest`; semver tags; push to `origin` (a remote already exists).
