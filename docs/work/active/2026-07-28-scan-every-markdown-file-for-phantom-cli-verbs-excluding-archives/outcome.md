# Outcome — Scan every Markdown file for phantom CLI verbs, excluding archives

Shipped as planned. The doc guard's file set is now derived by exclusion from
`git ls-files`; coverage went from 104 files to 133 with zero new failures.

## What shipped

### Task 1 — invert `DOC_FILES` (`eca9c7e`)

`test(docs): derive the CLI-surface doc scan by exclusion instead of an inclusion list`

`tests/test_documented_cli_surface.py`, `DOC_FILES` block only:

- `ARCHIVAL` — module-level tuple of the five prefixes, each with its one-line
  reason as an inline comment, each with a trailing `/`.
- `_doc_files()` — shells out to
  `git -C <REPO> ls-files --cached --others --exclude-standard -z -- '*.md'`,
  splits on `\0`, drops empties and any path starting with an `ARCHIVAL` prefix,
  returns `sorted(REPO / p ...)`. Its docstring carries the three reasons for
  using git over `rglob`.
- `DOC_FILES = _doc_files()`.
- Module docstring gained a `Scope, files:` paragraph; the existing parser-limits
  paragraph became `Scope, parsing:`.

`_invocations`, `_help`, `_subcommands`, `_walk`, `_check`, the `tree` fixture,
and the parametrization are untouched, as the plan required.

### Task 2 — `stage-spec.md` sweep rule (`f646c67`)

`skill(stage-spec): require a repo-wide sibling-defect sweep or a stated narrowing`

New step 6 under `## Steps` (commit moved to step 7), carrying the
`— agent [judgment]` marker that `tests/test_skill_lifecycle_parity.py:129-132`
requires. Wording extends the request's ask with the *why*: a scope inherited
from the report or the previous stage is a scope nobody chose.

### Task 3 — documentation sync (`07a6cd1`)

`docs(changelog): record the doc-guard scope inversion and the stage-spec sweep rule`

Evaluated over the finished diff, not per-task:

| Entry | Trigger | Result |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fired** — new `## Internal` entry for the scope inversion, plus a `## Changed` entry for the `stage-spec.md` rule |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **fired, answered by task 2** — the edit is to `stage-spec.md`, a `tcw-work` reference. The router needed no change: the step sits inside an existing stage document reached by an existing gate |
| `docs/release-notes/upcoming.md` | `Public-API` | did not fire — contributor-facing test change, no user-visible behavior |
| `README.md` | `Public-API` | did not fire — same; README documents the CLI, not the suite |

All four predictions in `plan.md` task 3 held.

## Test result

```
$ python -m pytest tests/test_documented_cli_surface.py -q
133 passed in 3.22s

$ python -m pytest tests/test_skill_lifecycle_parity.py -q
71 passed in 0.61s

$ python -m pytest -q
1127 passed in 186.69s (0:03:06)
```

1127 is up from 1098 before this item — exactly +29, matching the 133−104 file
increase, since the doc guard is parametrized one case per file.

### Manual verification (acceptance criteria 6 and 7)

The suite cannot test what happens when a file that does not yet exist is added,
so both probes were run by hand. Actual output:

**Criterion 6 — a new tree is covered with no test edit.** With
`docs/guides/probe.md` created (a directory registered nowhere — not in the test,
not in `.gitignore`, not in git):

```
FAILED tests/test_documented_cli_surface.py::test_documented_verbs_and_flags_exist[docs/guides/probe.md]
E   AssertionError: docs/guides/probe.md documents a nonexistent CLI surface:
E       `tcw work frobnicate` — no such verb: tcw work frobnicate
```

After `rm -rf docs/guides`: `133 passed`, and `git status --short` clean.

**Criterion 7 — archival trees stay excluded.** With `docs/changelogs/probe.md`
holding the same content: `133 passed`. After removal, `git status --short`
clean.

## What the plan or spec got wrong

Nothing material. Every plan task landed as written and all four
Documentation-Sync predictions were correct.

One refinement, made in `spec.md` before implementation began and noted here for
the record: acceptance criterion 4 as originally drafted asserted "**134
passed**" for a 133-file set, and its parenthetical contradicted itself about
whether the probe was included in the count. Rewritten to assert zero failures
with the case count bound to the `git ls-files … | wc -l` expression rather than
to a literal, since the literal moves whenever a doc is added. Measured values
(133 files, 133 passed) recorded alongside it.

The spec's own correction of the request — that the candidate set produces
**zero** failures rather than the three the request claimed, because the three
files named are *inside* the exclusion list — was independently re-verified in
the coordinating session before the spec was committed: 133 candidate files, 0
failures.

## Notes

- The `--others` behavior is the one thing here most likely to surprise someone
  later: an untracked, unstaged Markdown draft is in scope, so a work-in-progress
  doc naming a nonexistent verb reddens the suite before it is ever committed.
  This is intended — it is what makes "a new tree is covered immediately"
  literally true, and criterion 6's probe depends on it — and it is called out
  explicitly in the changelog entry rather than only in the spec's Risks.
- The shared-constant question was settled *against* extraction and the reasoning
  is in `spec.md`: `tcw validate` scans the three store trees including
  `docs/work/`, which is the largest exclusion here, so the two notions of
  "which trees matter" are close to opposites rather than shareable. One
  consumer, no second in sight.
- `CLAUDE.md` is a symlink to `AGENTS.md` and both are tracked, so identical
  content is scanned twice under two parametrization ids. Harmless (the check is
  a pure read) and deduplicating by resolved path would cost more than the
  duplicate does.
