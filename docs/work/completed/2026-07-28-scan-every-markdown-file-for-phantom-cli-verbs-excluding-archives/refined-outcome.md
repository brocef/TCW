# Refined outcome — Scan every Markdown file for phantom CLI verbs, excluding archives

**Verdict: accepted.** Verified in the coordinating session on 2026-07-30.
Subagent dispatch was unavailable for this item (account session limit), so spec,
plan, implementation, and this assessment all ran inline.

## Evidence, criterion by criterion

| # | Criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | `DOC_FILES` built from repo-wide enumeration minus a named exclusion list; no list of included roots | met | `tests/test_documented_cli_surface.py` — `ARCHIVAL` tuple + `_doc_files()`; the five-root list is gone |
| 2 | Enumeration is `git ls-files --cached --others --exclude-standard` | met | `_doc_files()` body, verbatim flags |
| 3 | Exactly the five archival prefixes, each with a one-line reason, each trailing-slashed | met | `ARCHIVAL` — `docs/work/`, `docs/plan/`, `docs/superpowers/`, `docs/changelogs/`, `docs/release-notes/` |
| 4 | Case count equals the `git ls-files … \| wc -l` expression; zero failures | met | `133 passed`; expression returns `133` |
| 5 | Full suite green including `test_skill_lifecycle_parity.py` | met | `1127 passed`; parity suite `71 passed` |
| 6 | New-tree auto-coverage demonstrated by the exact procedure | met | `docs/guides/probe.md` failed naming `no such verb: tcw work frobnicate`; green and clean after removal. Full output in `outcome.md` |
| 7 | Inverse holds — probe in an archival tree leaves the suite green | met | `docs/changelogs/probe.md` → `133 passed`; removed, tree clean |
| 8 | `stage-spec.md` gains one `Steps` line with an enforcement marker | met | New step 6, `— agent [judgment]`; parity suite green |
| 9 | Changelog entry present; no release-notes entry | met | `docs/changelogs/upcoming.md` `## Internal` + `## Changed`; `upcoming.md` release notes untouched |

**Suite:** `python -m pytest -q` → `1127 passed in 186.69s`. Up from 1098 before
this item — exactly +29, matching the 133−104 coverage increase one-for-one,
which is independent corroboration that the widening did what it claims.

## Checks beyond the criteria

- **The mechanism replaces a judgment, which is the item's actual point.** The
  repo directive is that anything which must be guaranteed belongs in tooling
  rather than in an instruction someone must remember. Criterion 6's probe is the
  proof: a directory registered in no list at all was covered on creation.
- **Abstraction litmus test: not applicable.** Nothing here touches the store
  interface — a test-scope change and a skill prose line.
- **Harness compatibility: unaffected.** `tests/` never ships in a wheel
  (`pyproject.toml` packages only `tcw*`), and the `stage-spec.md` rule is inert
  prose read identically by Claude and Codex.
- **Capabilities: no delta, confirmed not assumed.** The spec checked all 57
  ledger entries; a maintainer-only pytest guard is not something a user can do.
- **The new `git` dependency is proportionate.** The module already shells out to
  `tcw`, sibling suites shell out to `git`, and the suite only ever runs from a
  clone. No fallback path was added, correctly — a missing `git` is a broken dev
  environment, not a case to degrade into.

## Deferred follow-ups

None opened. Two decisions were settled *against* further work, both with
reasoning recorded in `spec.md`:

- **No shared "archival tree" constant.** `tcw validate` scans the three store
  trees *including* `docs/work/` — the largest exclusion here — so the only
  candidate second consumer wants a near-opposite set. One consumer; extracting
  an interface with one implementation would fail the repo's own litmus test.
  Promoting the tuple later is a five-minute change if that ever changes.
- **The companion post-mortem recommendation was folded in, not deferred**
  (task 2). It covers the residue the guard structurally cannot parse — a stale
  factual claim, a flag named only in prose — so it complements rather than
  duplicates. A separate item would have spent a full lifecycle spine on one
  sentence.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Four commits:
  `eca9c7e`, `f646c67`, `07a6cd1`, plus the outcome commit.
- **Version:** none cut at closeout. Per the user's decision on 2026-07-30, a
  single **minor** bump covers the whole seven-item batch once it finishes. This
  item alone would have justified only a patch — no user-facing surface changed.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, `version offered` all satisfied. The sixth entry — *originating
  GitHub issue answered and closed* — **does not apply**: this item came from
  post-mortem recommendation #1 of
  `2026-07-28-audit-the-work-backlog-with-subagents-and-make-the-workflow-reachable-from-codex`,
  not from an issue.

## Notes

The item's own `Meta changes` section asked for a mechanism in place of a
judgment, and the result is honest about where that boundary now sits: the guard
mechanizes what can be parsed, and task 2's `stage-spec.md` rule is explicitly
the weaker instrument for the part that cannot be. Recording that asymmetry
rather than presenting both as equivalent is the more useful outcome.
