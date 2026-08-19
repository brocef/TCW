# 13 — Release integrity

Checks that only mean anything against an **installed** build. These are the last
gate before publishing, and the ones most likely to catch a packaging mistake
that every in-process test misses.

## Functionality covered

- The five-file version lockstep
- Wheel/sdist completeness: package data, prompts, templates, web assets
- The console-script entry point
- `scripts/cut_version.py`
- Installation into a clean environment

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `python -m build` produces a wheel and an sdist without error. |
| 2 | The wheel installed into a **fresh virtualenv** with no other dependencies present gives a working `tcw` on `PATH`. |
| 3 | In that clean venv, from a temp dir, the full scenario-02 happy path runs green. This is the assertion that catches a data file missing from the wheel. |
| 4 | Every shipped stage prompt and artifact template is reachable from the installed package — enumerate them via the CLI (`tcw work lifecycle --json`, `tcw work scaffold` over every artifact id) rather than by listing files in the source tree. |
| 5 | `tcw --version` in the clean venv matches the version in `pyproject.toml`. |
| 6 | All **five** version-bearing files agree: `pyproject.toml`, `tcw/__init__.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`. |
| 7 | `.agents/plugins/marketplace.json` carries **no** version key — deliberately, and a well-meaning addition would be a regression. |
| 8 | `scripts/cut_version.py` run against a **copy** of the repo in the temp dir bumps all five, rotates `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` into `v<version>.md`, recreates fresh `upcoming.md` files, commits, and tags. |
| 9 | `cut_version.py` **aborts** when the five files disagree, and changes nothing — verified with a manifest hash, and with the git tag list unchanged. |
| 10 | `cut_version.py` does **not** push. Assert against a local bare remote: after the cut, the remote has neither the commit nor the tag. |
| 11 | `patch`, `minor`, `major` and an explicit `X.Y.Z` all produce the expected version. |
| 12 | The sdist contains the test suite and the source layout needed to build from it. |
| 13 | `tcw` runs on the **oldest supported Python** declared in `pyproject.toml`, if that interpreter is available; skip loudly if not. |

## Refusals asserted

9 (version drift aborts), 10 (no push).

## Explicitly not covered here

Publishing to PyPI. That requires credentials and MFA and is a human step.

## Notes for the implementer

Assertion 8 must run against a **copy**, never this repository — it commits and
tags. `git clone` the repo into the temp dir (a local clone is fine and fast) and
operate there. Getting this wrong tags the developer's real repo, which is the
single most damaging thing any script in this suite could do. Guard it: assert
the working directory is under the temp dir before invoking the script, and fail
hard if it is not.

Assertion 3 is the highest-value line in the whole suite. Everything else tests
behaviour that source-tree tests also see; this one tests the artifact users
actually install.
