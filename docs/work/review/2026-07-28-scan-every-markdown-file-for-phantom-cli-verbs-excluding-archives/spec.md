# Spec: scan every Markdown file for phantom CLI verbs, excluding archives

## Capability changes

None. Checked against the ledger rather than assumed: `tcw capabilities list`
returns 57 entries, every one of them a `tcw` CLI or plugin action a user
performs (`work/start-a-work-item`, `cli/validate-a-node`, …). There is no
subject for the contributor test suite and no capability whose body describes
documentation accuracy. A pytest guard that only maintainers run is not
something a user can do, so nothing in `docs/capabilities/` gains, loses, or
changes status.

## Problem

`tests/test_documented_cli_surface.py` enforces a universally quantified claim —
its docstring says the defect is a verb "documented in `README.md` and the
agent-facing `skills/tcw-work/references/commands.md` without ever existing"
(`tests/test_documented_cli_surface.py:1-16`) — but it checks a hand-enumerated
list of five roots (`tests/test_documented_cli_surface.py:25-35`):

```python
DOC_FILES = sorted(
    [REPO / "README.md"]
    + list((REPO / "skills").rglob("*.md"))
    + list((REPO / "commands").glob("*.md"))
    + list((REPO / "agents").glob("*.md"))
    + list((REPO / "docs" / "capabilities").rglob("*.md"))
)
```

The list has already been wrong once, and the code says so: the comment at
`tests/test_documented_cli_surface.py:30-33` records that `docs/capabilities/`
"was the one place a phantom verb survived the first sweep, because the sweep did
not look here". The fifth root was appended after the fact. Any tree added
tomorrow is outside the guard by default, and nothing signals that.

That default is not hypothetical today. Measured at HEAD, the current list covers
104 files; enumerating every non-archival Markdown file in the repo covers 133.
The 29 files the guard does not currently look at include:

- `AGENTS.md` and its symlink `CLAUDE.md` — the directives every agent in this
  repo reads before acting.
- all 22 `docs/taxonomy/**/description.md` bodies — the registered vocabulary,
  which describes what commands operate on.
- `docs/work-inbox-template.md` and four `docs/migration-guide-*.md` files —
  documents that exist specifically to be followed literally.

Widening to those 133 files finds **zero** new failures (see Notes for what this
corrects in the request), so the change costs nothing today and closes the hole
permanently.

## Goals

- The guard's file set is derived by exclusion: every Markdown file in the repo
  is checked unless it falls in a tree named as archival, with a stated reason.
- A new documentation tree — `docs/guides/`, a top-level `CONTRIBUTING.md`, a
  `skills/` sibling — is covered the moment the file exists, with no test edit.
- Files that legitimately name commands that no longer exist (release history,
  frozen lifecycle artifacts, retired plans) stay out, and the exclusion list
  says why for each.
- The suite is green after the change.

## Non-goals

- **Fixing the archival documents.** The 16 archived files that name dead verbs
  (7 changelogs, 3 release notes, 1 plan, 2 superpowers specs, 3 work items) are
  correct as history and stay untouched.
- **Improving what the parser detects.** The docstring's stated limitation —
  "Prose that describes a command without writing it out slips past"
  (`tests/test_documented_cli_surface.py:15-16`) — is unchanged. So is the
  false-positive class in `_check` (see Risks). This item changes *which files*
  are read, not *how* they are read.
- **A shared "archival tree" constant.** Settled below; the list stays in the
  test.
- **Making the guard runnable outside a git checkout.** `pyproject.toml:20-22`
  packages only `tcw*`, so `tests/` never ships in a wheel; the suite runs from a
  clone or not at all.

## Design

### Enumerate with git, not with `rglob`

The file set comes from one call:

```
git -C <repo> ls-files --cached --others --exclude-standard -z -- '*.md'
```

`--cached` gives tracked files, `--others --exclude-standard` adds untracked
files that `.gitignore` does not cover. This is the design decision the request
did not address, and it matters for three concrete reasons:

1. **It excludes build and vendor output for free, and keeps doing so.** There
   are 1222 `*.md` files on disk and 270 in this set. The 952 excluded are
   `node_modules/**` (~700), `.venv/**`, `.pytest_cache/README.md`, `logs/*.md`,
   `.superpowers/sdd/*.md`, and the gitignored `docs/work/completed/**` and
   `docs/work/discarded/**` (`.gitignore:28-31`). Hand-listing those in the test
   would rebuild the original defect in a new costume — the next ignored tree
   someone adds would be scanned and would redden the suite for no reason. The
   repo already declares what is not source; reuse that declaration.

2. **It survives the `plugins/tcw` symlink.** `plugins/tcw` is a symlink to `..`,
   i.e. the repo root — a loop that `pyproject.toml:28-31` already documents and
   guards against (`norecursedirs = ["plugins", …]`, with the comment "without
   these, collection recurses through it infinitely"). To git it is a single
   index entry, never a tree. An `rglob`-based scan is only safe here because
   pathlib happens not to recurse symlinked directories.

3. **`--others` keeps the "new file is covered immediately" property literal.**
   A brand-new, not-yet-`git add`ed doc is in the set. Without `--others` the
   guard would silently ignore every doc until it was staged — and the item's
   own acceptance criterion (write a new file, watch the suite go red) would not
   hold as written. Verified: a probe at `docs/guides/probe.md` containing
   `` `tcw work frobnicate` `` was picked up unstaged and reported `no such verb:
   tcw work frobnicate`.

### Exclude archival trees by path prefix

Five prefixes, each carrying its one-line reason in the source:

| Prefix | Reason |
| --- | --- |
| `docs/work/` | Lifecycle artifacts, frozen once written; they quote the verbs a change is about, including ones being removed or never built. |
| `docs/plan/` | The retired build-phase specs; the tracker they belong to is retired. |
| `docs/superpowers/` | Archived specs and plans from a prior workflow. |
| `docs/changelogs/` | Historical entries, correct as of the version they describe. |
| `docs/release-notes/` | Same. |

Two properties of the matching rule:

- Prefixes carry a **trailing slash**, so a directory prefix cannot swallow a
  sibling file. Without it, `docs/work/` would also exclude
  `docs/work-inbox-template.md`, which is live documentation and one of the 29
  files this change is meant to add.
- Matching is on the repo-relative POSIX path git emits, so it is independent of
  the working directory the suite is run from.

Everything else about the test — `_invocations`, `_help`, `_subcommands`,
`_walk`, `_check`, the module-scoped `tree` fixture, and the parametrization at
`tests/test_documented_cli_surface.py:131` — is untouched. Only the definition of
`DOC_FILES` changes.

### Where the exclusion list lives: in the test

**Settled: keep it in the test file.** The request asked whether `tcw validate`
wants the same notion. It does not, and the two notions are close to opposites.
`tcw validate` scans `docs/{taxonomy,capabilities,work}` (`tcw/validate.py:26`,
`tcw/validate.py:62-65`) — the three *store* trees. It deliberately includes
`docs/work/`, the largest exclusion here, because work items carry `tcw://`
references it must resolve; and it never touches `docs/plan/`,
`docs/superpowers/`, `docs/changelogs/`, or `docs/release-notes/` at all. A grep
for archival-tree handling across `tcw/` returns nothing. One consumer, no second
one in sight, and the only candidate wants a different set: an interface with one
implementation fails this repo's own litmus test. If a second consumer ever
appears, promoting a module-level tuple is a five-minute change.

### The `stage-spec.md` rule: folded in

**Settled: in scope, as a one-line addition to the `Steps` section of
`skills/tcw-work/references/stage-spec.md`** (steps at
`skills/tcw-work/references/stage-spec.md:32-47`) stating that a sweep for
sibling defects is repo-wide by default, or the spec says why it was narrowed.

Reasoning: the two changes cover disjoint failure modes — the guard catches
written-out invocations, the rule covers what it structurally cannot parse (a
stale factual claim, a flag named only in prose, a file nobody opened) — so this
is a complement, not a duplicate. A separate work item would spend a full
`request → spec → plan → implement → verify` spine on a single sentence, which
costs more than the sentence. The rule is honestly weaker than the guard: it is
an instruction someone must remember, which is exactly the category this repo
prefers to move into tooling. It is folded in *because* the guard now covers the
mechanizable part, leaving prose as the residue that only prose can address.

Constraint on the edit: `tests/test_skill_lifecycle_parity.py:129-132` requires
each stage document's `Steps` body to carry at least one enforcement marker from
`("[auto]", "[gated]", "[prompted]", "[judgment]")`, and
`tests/test_skill_lifecycle_parity.py:31` fixes the section set. The addition must
be a step or step-line in `Steps` with a marker, not a new section.

## Acceptance criteria

1. `DOC_FILES` in `tests/test_documented_cli_surface.py` is built from a
   repo-wide enumeration minus a named exclusion list. Reading the file shows no
   list of included roots.
2. The enumeration is `git ls-files` with `--cached --others --exclude-standard`,
   so tracked files, brand-new unstaged files, and only those are scanned.
3. The exclusion list contains exactly the five archival prefixes in the Design
   table, each with a one-line reason in the source, and each written with a
   trailing `/`.
4. `python -m pytest tests/test_documented_cli_surface.py -q` passes with one
   parametrized case per scanned file and **zero failures**. The case count is
   not asserted as a literal — it moves whenever a doc is added — so the binding
   form is that it equals the output of

   ```sh
   git ls-files --cached --others --exclude-standard -- '*.md' \
     | grep -vE '^docs/(work|plan|superpowers|changelogs|release-notes)/' | wc -l
   ```

   Measured at `ff1e562`: 133 files, 133 passed, 0 failed — up from the 104 the
   inclusion list covers.
5. `python -m pytest -q` is green overall, including
   `tests/test_skill_lifecycle_parity.py`.
6. **The auto-coverage property is demonstrated by this exact procedure**, and
   the result is recorded in the item's verification notes:

   ```sh
   mkdir -p docs/guides
   printf 'Run `tcw work frobnicate` to frobnicate.\n' > docs/guides/probe.md
   python -m pytest tests/test_documented_cli_surface.py -q   # expect 1 failed
   rm -rf docs/guides
   python -m pytest tests/test_documented_cli_surface.py -q   # expect green again
   git status --short                                          # expect clean
   ```

   The failure message must name `docs/guides/probe.md` and
   `no such verb: tcw work frobnicate`. `docs/guides/` must not be added to the
   test, to `.gitignore`, or to git.
7. The inverse holds: adding the same probe at
   `docs/changelogs/probe.md` leaves the suite green, and it is removed
   afterwards.
8. `skills/tcw-work/references/stage-spec.md` gains one step-line under `Steps`
   requiring a repo-wide sibling-defect sweep by default or a stated narrowing,
   carrying an enforcement marker.
9. `docs/changelogs/upcoming.md` carries an entry for the change
   (`Any-Code-Change` trigger in `CLAUDE.md`). No `docs/release-notes/upcoming.md`
   entry: no user-facing behavior changes.

## Risks

- **A working-tree draft can redden the suite.** `--others` means an untracked
  `.md` a contributor is mid-way through writing is checked. This is the intended
  behavior — an unstaged doc is still a doc — but it is a change in when the
  guard speaks up. Escape hatch already exists and needs no code: gitignored
  paths are excluded, so scratch space under `logs/` or `.worktrees/` is unaffected.
- **False positives grow with the file set.** `BACKTICKED`
  (`tests/test_documented_cli_surface.py:37`) matches any backtick span
  containing the word `tcw`, and `_check`
  (`tests/test_documented_cli_surface.py:112`) then slices from the first `tcw`
  and reads what follows as a command. A real instance exists in the excluded
  set: `` `--settings '{"enabledPlugins":{"tcw@tcw":true}}'` `` in
  `docs/work/backlog/2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness/spec.md`
  is reported as "no such flag: --settings on tcw". Measured: zero such hits in
  the 133-file candidate set today. Out of scope to fix; if one appears later the
  fix is in the parser, not in re-narrowing the scope.
- **The guard now depends on `git` being on PATH.** Acceptable: the module
  already shells out to `tcw` (`tests/test_documented_cli_surface.py:60`), other
  suites shell out to `git` (`tests/test_capabilities.py:16-18`), and `tests/` is
  never packaged (`pyproject.toml:20-22`). No fallback path is added; a missing
  git is a broken dev environment, not a case to degrade gracefully into.
- **Someone widens the exclusion list to silence a real failure.** The list is
  the one remaining piece of judgment. Mitigated only by the required one-line
  reason per entry, which makes "I added this to get green" hard to write down.

## Notes

**What the request got wrong.** `initial-request.md:50-54` states that scanning
every `*.md` outside the five excluded trees "produces exactly **three**
failures, all archival — `docs/plan/phase-5-work.md` … and two
`docs/superpowers/` documents". Re-verified at HEAD (`ff1e562`) by running the
test's own `_invocations`/`_check` against the candidate set: the candidate set
of 133 files produces **zero** failures. The three files named are *inside*
`docs/plan/` and `docs/superpowers/`, i.e. inside the exclusion list, so they
cannot also be residue outside it.

The number itself is real; the framing is inverted. Three is what you get if you
exclude only `docs/work/`, `docs/changelogs/`, and `docs/release-notes/` — which
is evidently the scan that was run, and which is precisely the evidence that
justified adding `docs/plan/` and `docs/superpowers/` to the list. So the
request's conclusion survives intact and is in fact stronger than stated: the
exclusion list is a principled class, and applying it in full leaves a clean
scan. The full suppressed set is 16 files — 7 in `docs/changelogs/`, 3 in
`docs/release-notes/`, 1 in `docs/plan/`, 2 in `docs/superpowers/`, 3 in
`docs/work/` — every one of them archival, none of them a live document.

Two smaller notes:

- The request's "also exclude `node_modules/` and any build output under `web/`"
  (`initial-request.md:56`) needs no explicit rule under the `git ls-files`
  design; both are already gitignored. Naming them in the test would be dead
  code.
- `CLAUDE.md` is a symlink to `AGENTS.md` and both are tracked, so the identical
  content is scanned twice under two parametrization ids. Harmless — the check
  is a pure read — and deduplicating by resolved path would be more code than the
  duplicate costs.
