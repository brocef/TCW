# Outcome: make the TCW marketplace syncable from the claude.ai web app

All six plan tasks shipped. **The item is not verified** — AC-7, the only
criterion that tests the thing the item is named after, requires the user's
claude.ai account and has not been run.

## What shipped

| Task | Commit | What landed |
| --- | --- | --- |
| T1 | `127607c` | Metadata across all four manifests |
| T2 | `a7ada11` | Three layout-agnostic manifest tests |
| T3 | `0e9d79b` | `plugins/tcw` removed; Codex path → `"."`; symlink test inverted |
| T4 | `51f20ab` | `norecursedirs`/`packages.find` workarounds and the stale docstring clause retired |
| T5 | — | Verification only, no diff |
| T6 | `0a128bf` | Developer changelog |
| — | `819d3a1` | AC-6 amended mid-implementation (below) |

Code diff excluding lifecycle artifacts: 8 files, +87/−19.

## Acceptance criteria

| AC | Result |
| --- | --- |
| 1 — only `CLAUDE.md` is a tracked symlink | **met** — `git ls-files -s` mode `120000` returns `CLAUDE.md` alone |
| 2 — Codex installs from a scratch clone | **met** — `marketplace add` + `plugin add` succeed, 8 skills, version `0.18.2` read from `pyproject.toml` rather than hard-coded |
| 3 — `claude plugin validate .` zero warnings | **met** — "✔ Validation passed", was one warning |
| 4 — Claude CLI marketplace add | **met** — both against a local clone of the new tree and the remote URL |
| 5 — `pytest tests/` green | **met** — 1193 passed, run after T3 and again after T4 |
| 6 — no functional `plugins/tcw` reference | **met, criterion amended** — see below |
| 7 — adding `brocef/TCW` at claude.ai/code succeeds | **NOT RUN** — user-only |

## What the plan and spec got wrong

**1. T1 under-specified the manifests it had to touch.** The plan listed
`license` for `.claude-plugin/plugin.json` only, but T2's cross-manifest
agreement test requires both plugin manifests to match — and
`.codex-plugin/plugin.json` had no `license`. Writing T1 as planned would have
made T2 fail on the commit that introduced it. `.codex-plugin/plugin.json`
gained `license` and an author email in T1. Caught by the test the plan itself
ordered first, which is the argument for that ordering.

**2. AC-6 was written too literally** (amended in `819d3a1`). It demanded that
grep for `plugins/tcw` return nothing outside `docs/changelogs/`. But T3's
replacement test carries docstrings explaining *why* a class-level symlink
assertion exists — precisely the subtle constraint most worth documenting.
Satisfying the criterion as written meant deleting that explanation to make a
grep pass. AC-6 now reads "no **functional** reference — nothing that resolves a
path, configures a tool, or is read at runtime", which is what it always meant.
Verified: the only remaining matches are two docstrings and the untracked
`.claude/settings.local.json`.

**3. The wheel check needed a different tool than assumed.** T4 proposed
`python -m build`; neither the pyenv interpreter nor `.venv` has `build` or even
`setuptools` installed. Used `pip wheel --no-deps` under build isolation
instead — same assertion, and it confirmed the wheel contains only `tcw` and its
dist-info, so `exclude = ["plugins*"]` really was redundant with
`include = ["tcw*"]`.

**Nothing contradicted the spec's central measurement.** The claim that the
symlink is not load-bearing held end-to-end on the real tree: Codex resolved
`"."`, installed all 8 skills, and reported the version from `pyproject.toml`.

## What is still unknown, and it is the main thing

This item **did not diagnose the failure** — `spec.md` says so under Non-goals,
and nothing during implementation changed that. Two candidate causes were
changed at once, and the third possibility (that claude.ai resolves the user's
own repositories through an uninstalled GitHub App, in which case nothing in
this repo was ever at fault) remains untested because the user deferred the fork
probe.

So every automatable criterion passing means only that the intended changes were
made correctly. It says nothing about whether web sync works.

**Held back pending AC-7**, per `plan.md`'s gate — all three assert a
user-facing claim nothing has verified:

- `docs/release-notes/upcoming.md` — untouched
- `README.md` — untouched; `README.md:96-131` still documents CLI install only
- the `plugin/install-as-a-plugin` capability body and its `capabilities.yaml`
  `changed:` entry — not written

If AC-7 fails, none of them land, `verify` records that the diagnosis was not
confirmed, and the fork probe becomes the follow-up item.

## Documentation Sync

Evaluated once over the finished diff, per `stage-implement.md` step 6:

| Entry | Trigger | Fired | Action |
| --- | --- | --- | --- |
| `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | yes | T6, `0a128bf` — Changed/Removed/Internal |
| `docs/release-notes/upcoming.md` | `[Public-API]` | pending AC-7 | withheld |
| `README.md` | `[Public-API]` | pending AC-7 | withheld |
| `skills/<component>/SKILL.md` | `[Skill-Driven-Component]` | no | no component's CLI surface, model/fields, lifecycle, or guardrails changed |

## Notes

- The suite takes ~3m20s, over the default 2-minute command timeout. Run it in
  the background rather than reading a timeout as a hang — the first attempt
  here looked like the recursion failure T4 was ordered to avoid, and was not.
- Before removing the symlink, the new class-level assertion was run against the
  tree that still had it and confirmed to **fail**. A guard that passes both
  before and after proves nothing.
- All Codex measurements used scratch clones with isolated `CODEX_HOME`s; the
  user's `~/.codex` was never touched. Same for `CLAUDE_CONFIG_DIR`.
