# Refined outcome — Make tcw init honor a configured taxonomy or capabilities path

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–6 met, each by a test and a hands-on
  run in scratch nodes (config byte-identical after `init`; nothing created on
  a refusal).
- Full suite after the review fixes (started after `22507f6e`, the last code
  commit), from the item worktree with its private virtual environment:
  **4777 passed, 3 skipped** (exit 0).
- Hands-on (mine): `taxonomy.path: ./knowledge/terms` with no folder —
  `tcw taxonomy list` exits 1; `tcw taxonomy init` scaffolds
  `knowledge/terms`; `list` then exits 0; the config still reads
  `./knowledge/terms`; no `docs/taxonomy`.

## Accepted deviations from the spec

- An already-provisioned repository gets "already provided … nothing to
  scaffold" rather than "run `tcw provision`" (review finding; tested).
- Plain `tcw init` (all components) on a node where one component declares a
  repository refuses the whole run and names the command for the rest.
- A whitespace-only or `null` `<component>.path` is refused by `init`, as the
  readers already refuse a whitespace-only one.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `skills/configure/references/stores.md`, changelog and
  release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed. The review's findings 4–6 (an explicit
  `--taxonomy-path` not anchored in a linked worktree; a symlinked node folder
  not resolved before anchoring; an absolute path outside any repository)
  predate this change and are narrow; recorded here rather than filed.
