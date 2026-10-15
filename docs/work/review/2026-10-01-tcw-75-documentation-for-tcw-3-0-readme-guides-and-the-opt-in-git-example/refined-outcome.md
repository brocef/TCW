# Refined outcome — Documentation for TCW 3.0: README, guides and the opt-in git example

**Accepted, 2026-10-15**, by bounded adversarial review under the owner's rule
for the TCW 3.0 epic: a child is approved when it passes adversarial review,
and the owner reviews the epic as a whole once every child is done. Round 1
(three reviewers by area) was NOT DONE; one fix round; round 2 (one
confirming reviewer over the whole change) was DONE, and its single small
finding was fixed. `outcome.md` records each finding and its fix.

## What was delivered

On `work/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example`
(fast-forwarded into `epic/tcw-3.0`), 22 commits from `5b0dcf95`:

- The README, the work, Jira, configuration, multi-project, taxonomy and
  capabilities, and linking and validation guides, rewritten for 3.0; a new
  `docs/guide/cli.md` (naming, output streams, exit codes).
- The configure skill rewritten: a router and six references, `jira.md` and
  `personal.md` new, `tracker.md` gone; one heading and one
  Shared/Overridable/Personal-only label per configuration key, tied to the
  code by tests.
- `docs/lifecycle/abstraction.md` (twelve backend operations, both
  questions), `implementation.md` and `harness.md`; the worktree section of
  `AGENTS.md`.
- The opt-in git example: `docs/guide/examples/commit-item-after-move.sh`
  and its configuration, tested in real repositories.
- Guards: vocabulary, link and anchor, allowance-name and command checks over
  the 19 owned documents; the allowance shrunk to entries only TCW-76's files
  name; release-note and changelog entries, the release note opening with the
  3.0.0 introduction.

## Acceptance criteria

1-11 are met, with the evidence in `outcome.md`. **Criterion 12 (the full
suite) is deferred to the end of the epic** by the owner's rule for this
epic; TCW-76 runs it once.

## Deferred, and why

- **Version cut and publication:** none for this item; 3.0.0 is cut at the end
  of the epic, after TCW-76 (CLAUDE.md's order: complete every item, cut,
  push, then issues). The item came from no GitHub issue.
- **To TCW-76:** the remaining allowance entries (`AGENTS.md`, three
  capability records), `PENDING_TARGETS`, `Planning doc` on 13 records, Pi
  text from `main` at the merge, and the documentation entries' descriptions
  in `tcw-config.yaml`.
- **Separate changes:** `docs/work/inbox/2026-10-15-tidy-what-tcw-75-s-reviews-left-in-code-text.md`,
  best done before TCW-76's code freeze.
