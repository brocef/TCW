---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-111

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `23ab7fbb`, `v4` with this item's 22
commits rebased onto it (`0287fc4e..23ab7fbb`). The dispatching session
checked both findings against the repository before writing this round.

The reviewer recommended accepting, with two small findings that belong to
this change. The user's rule for the TCW-99 children is that an item is
accepted only when the review finds no open finding belonging to the change,
so this round is recorded as rejected and both go back to implement.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on `v4` at `23ab7fbb` in two halves by
  folder: `1982 passed, 2 skipped` and `4125 passed, 111 skipped`. `pnpm
  test` `191 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean;
  the end-to-end suite `15 passed`.
- By the reviewer: the item's test files in groups, all passing. One failure,
  `test_shipped_prompts::test_the_wheel_carries_exactly_the_prompts_and_procedures`,
  came from a `node_modules` link planted in the review worktree, not from
  this item; the test passes in the full run on `v4`.
- A test inventory over the 68 changed or deleted test files: no test
  vanished without a renamed replacement; no skip added beyond two root-only
  skips in `test_git_example`; the mechanical conversion removes and adds 59
  assertion lines, renames only; the one assertion changed in meaning
  (`test_identity`, a several-part name now names a nested item) is right.
- By hand in a scratch project: `--nest`, the refused rename of an item with
  nested items, the nested rename, `rm` refused with a 3.x file or a
  `resources/` state file below, parent loops and a self-parent reported, the
  `edit --parent` warning, `drafts/` reported in an epic, a newer
  `tcw-version` leaving a term out with exit 1.
- The commit hook by hand: a parent's move commits its own files and leaves
  a nested item out; the nested item's move commits it. The guide's block is
  the script byte for byte.
- `fitted_words` gives exactly 255 characters at every room tried; the
  longest identifier in this repository is 121 characters.
- No git call added under `tcw/`; no private name in the change.
- `documentation-sync`: both `upcoming/` entries present; the capability
  records match the code; the deferrals to TCW-117 fall within the spec's
  non-goals.

## Acceptance criteria

All are met except 22, the suite, which is the run above. AC 14's 240-
character parent case is tested for the files backend only; the Jira side is
covered by the stricter 227-character refusal through the same code. AC 16's
new full identifier goes to standard output rather than standard error,
which is enough.

The implementer's decisions agree with the spec; the two sweep allowlist
entries are justified.

## Findings

1. `docs/changelogs/upcoming/TCW-111-…md:26-27`: the wrap puts "1. (TCW-111)"
   at the start of an indented line, which renders as a numbered list item.
2. `tcw/store/fs.py:1097`: the refusal reads "<path> holds a TCW 3.x
   meta.yaml; run 'tcw migrate' in this project first", without the
   `cannot remove '<id-path>': ` that spec 2.5 gives, so it does not say
   which removal was refused (taxonomy and capabilities `rm`).

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session:

- `tcw capabilities set … --parent` accepts a self-parent or a loop, which
  only `validate` reports; the spec refuses at write time for work items only.
- The work store's reserved-name finding lost the 2.x pointer to the
  migration guide (for TCW-116 or TCW-117).
- The release note says items are renamed wherever their folder sits, and
  leaves out that an item with nested items cannot be renamed until TCW-114.

## What implement must do

- (a) Keep "exit 1." on one line in the changelog entry.
- (b) Start the 3.x removal refusal with `cannot remove '<id-path>': ` as
  spec 2.5 gives, for both namespaces, with the tests reading it.
- (c) `implement/round-2.md`.
