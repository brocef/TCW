# Plan — Scan every Markdown file for phantom CLI verbs, excluding archives

Three code/doc tasks and one documentation-sync block. Small enough that no
bounded stage-document DAG is warranted — the whole change is one test file, one
skill reference line, and one changelog entry.

Ordering rationale: task 1 is the change the item exists for and is
self-verifying (the suite either goes green over 133 files or it does not). Task
2 is an independent prose edit gated by a different test
(`tests/test_skill_lifecycle_parity.py`), so it is sequenced after task 1 to keep
each commit's failure mode unambiguous. Docs come last as one block, per
`stage-plan.md` step 4.

## Task 1 — invert `DOC_FILES` to a git-derived enumeration

**Changes:** `tests/test_documented_cli_surface.py`, the `DOC_FILES` block at
`:25-35` only. Everything else in the module is untouched.

Replace the five-root inclusion list with:

- a module-level `ARCHIVAL` tuple of the five prefixes from the spec's Design
  table, each with its one-line reason as a comment;
- a helper that shells out to
  `git -C <REPO> ls-files --cached --others --exclude-standard -z -- '*.md'`,
  splits on `\0`, drops empties, and filters out any path starting with an
  `ARCHIVAL` prefix;
- `DOC_FILES = sorted(REPO / p for p in <that>)`.

Prefixes keep their trailing `/` so `docs/work/` cannot swallow
`docs/work-inbox-template.md`. Match on the repo-relative POSIX path git emits,
not on a resolved absolute path, so the result does not depend on the invoking
cwd.

Update the module docstring's `Scope:` paragraph (`:14-16`) to say the file set
is every tracked-or-untracked Markdown file outside the archival trees — the
docstring currently describes only the parser's limits and would otherwise leave
the new scope undocumented at its point of use.

**Verified by:** `python -m pytest tests/test_documented_cli_surface.py -q` —
green, with a case count equal to

```sh
git ls-files --cached --others --exclude-standard -- '*.md' \
  | grep -vE '^docs/(work|plan|superpowers|changelogs|release-notes)/' | wc -l
```

(133 at `ff1e562`, up from 104). Satisfies acceptance criteria 1–4.

## Task 2 — add the repo-wide-sweep rule to `stage-spec.md`

**Changes:** `skills/tcw-work/references/stage-spec.md`, one step-line added
under `## Steps` (`:32-47`).

Content: when a spec sweeps for defects sibling to the reported one, the sweep is
repo-wide by default, or the spec states why it was narrowed. Must carry an
enforcement marker — `— agent [judgment]` — because
`tests/test_skill_lifecycle_parity.py:129-132` requires every stage document's
`Steps` body to contain at least one marker from
`("[auto]", "[gated]", "[prompted]", "[judgment]")`, and
`tests/test_skill_lifecycle_parity.py:31` fixes the section set, so this must be
a step inside `Steps` and **not** a new section.

**Verified by:** `python -m pytest tests/test_skill_lifecycle_parity.py -q`
green. Satisfies acceptance criterion 8.

## Task 3 — documentation sync

Evaluated against `CLAUDE.md`'s Documentation Sync list over the finished diff,
in one pass after tasks 1–2 (`stage-implement.md` step 6). Predicted:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — Internal group: the doc guard's scope is now derived by exclusion from `git ls-files`, covering 133 files instead of 104, and new documentation trees are covered automatically. |
| `docs/release-notes/upcoming.md` | `Public-API` | **does not fire** — contributor-facing test change; no `tcw` CLI surface or user-visible behavior changes. Confirmed against the spec's Capability changes section. |
| `README.md` | `Public-API` | **does not fire** — same reason. README documents the CLI, not the test suite. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **fires, already covered by task 2** — `skills/tcw-work/references/stage-spec.md` is the edit. No `SKILL.md` router change: the rule is a step inside an existing stage document reached by an existing gate, so nothing about the router's routing changes. |

Re-evaluate rather than assume at implement time; this table is a prediction.
Satisfies acceptance criterion 9.

## Verification

Beyond the suite — acceptance criteria 6 and 7 are procedures the suite cannot
perform on itself, since the property under test is *what happens when a file
that does not yet exist is added*. Run both by hand at implement time and paste
the actual output into `outcome.md`:

```sh
# 6 — a new tree is covered with no test edit
mkdir -p docs/guides
printf 'Run `tcw work frobnicate` to frobnicate.\n' > docs/guides/probe.md
python -m pytest tests/test_documented_cli_surface.py -q   # expect 1 failed,
                                                           # naming docs/guides/probe.md
                                                           # and "no such verb: tcw work frobnicate"
rm -rf docs/guides
python -m pytest tests/test_documented_cli_surface.py -q   # expect green
git status --short                                         # expect clean

# 7 — the inverse: an archival tree stays excluded
printf 'Run `tcw work frobnicate` to frobnicate.\n' > docs/changelogs/probe.md
python -m pytest tests/test_documented_cli_surface.py -q   # expect green
rm -f docs/changelogs/probe.md
```

`docs/guides/` must not be added to the test, to `.gitignore`, or to git — the
whole point is that it needed no registration. Confirm `git status --short` is
clean after each probe so no scratch file rides along in a commit.

Full `python -m pytest -q` green before `submit`.

## Notes

No blockers to record (`tcw work edit --blocked-by`): this item depends on
nothing else in the backlog, and nothing in the backlog depends on it.

The spec's Risks section flags that `--others` means an in-progress untracked
draft can redden the suite. That is intended, not a defect to design around, and
needs no plan task — but it is the thing most likely to surprise someone later,
so it belongs in the changelog entry's wording rather than only in the spec.
