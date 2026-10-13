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
| 2 | The wheel installed into a **fresh virtualenv** gives a working `tcw` on `PATH`. Install with `pip --no-index --find-links <local wheelhouse>` so "no network" and "clean environment" are enforced by the same command, and assert every resolved dependency came from the wheelhouse. |
| 2a | The **sdist** installed into another fresh venv also yields a working `tcw --version` and at least one built-in stage prompt. A wheel can be complete while the sdist fails to build or omits package data. |
| 3 | In that clean venv, from a temp dir that is not a git repository, the short walk runs green: `tcw init --id walk`, `printf 'Need X\n' \| tcw work new "A b"`, `tcw work advance <slug>` (prints `spec`), `echo hi \| tcw work comment <slug>`, `tcw work show <slug>`, `tcw taxonomy add Widget`, `tcw capabilities add ns/do-a-thing`, `tcw validate` (exit 0, nothing on stdout), `tcw projects list` (prints `walk`). This is the assertion that catches a data file missing from the wheel. |
| 4 | Every shipped stage prompt and procedure is reachable **and non-empty** from the installed package. Enumerate through the CLI (`tcw work lifecycle --json` for the stages, then `tcw work stage prompt <stage>` for each stage worked in, `flow` and `side`; `tcw work procedure <name>` for each procedure) rather than by listing source-tree files, and assert the *content*: each prints non-empty built-in instructions. Exit 0 alone passes against a package whose prompts were all dropped. The `terminal` stages, `completed` and `discarded`, are not worked in and exit 2 by design. Until TCW-74 adds `tcw/work/prompts/review.md` and `qa.md`, `review` and `qa` have no built-in prompt and are left out. |
| 5 | `tcw --version` in the clean venv matches the version in `pyproject.toml`. |
| 6 | All **five** version-bearing files agree: `pyproject.toml`, `tcw/__init__.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`. |
| 7 | `.agents/plugins/marketplace.json` carries **no** version key — deliberately, and a well-meaning addition would be a regression. |
| 8 | `scripts/cut_version.py` run against a **copy** of the repo in the temp dir bumps all five, combines the entry files in `docs/changelogs/upcoming/` and `docs/release-notes/upcoming/` into each folder's `v<version>.md` (one `# v<version>` title, each section heading once), deletes those entry files while keeping each folder's `README.md`, commits, and tags. |
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

**This is the scenario that can damage the developer's real repository.** Both
`python -m build` and every `cut_version.py` probe run inside a **local clone**
under the temp root — `build` alone would otherwise drop `dist/`, `build/` and
egg metadata into the working checkout, and the version cut commits and tags.

A "cwd is under the temp dir" check is **not sufficient**. Before invoking the
release script assert all three, and abort hard if any fails:

1. `git rev-parse --show-toplevel` equals the expected clone path.
2. `realpath scripts/cut_version.py` is below that same clone.
3. The **original** repository's `HEAD`, tag list and porcelain status are
   snapshotted before and compared after — the backstop that catches a mistake
   the first two miss.

Each of `patch`, `minor`, `major` and the explicit `X.Y.Z` case needs its own
fresh clone. Never reuse a clone after it has been tagged once.

Assertion 3 is the highest-value line in the whole suite. Everything else tests
behaviour that source-tree tests also see; this one tests the artifact users
actually install.
