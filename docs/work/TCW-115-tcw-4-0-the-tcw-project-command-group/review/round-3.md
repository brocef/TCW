---
verdict: accepted
judges: 3
---

# Review round 3 — TCW-115

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `08d3c7ff`, branch `v4` with TCW-113 and
TCW-115 both landed, over `963d3c53..08d3c7ff` and the three rebase conflicts
the dispatching session resolved. Rounds 1 and 2's results carry forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session on the joined
  branch in two halves by folder: `2175 passed, 2 skipped` and `5108 passed,
  111 skipped`, recorded in `implement/round-3.md`. `pnpm test`
  `229 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/test_project_provision.py` and
  `tests/test_families.py`, `94 passed`; `tests/work/test_scope_work.py`,
  `25 passed`. Both mutations in implement round 3, applied in a scratch
  copy, turn their tests red.
- By hand, through a guarded wrapper, cloning only a local scratch
  repository: with a child's work store declared in another repository and
  not fetched, `work list --scope down` and `work show --scope down` in the
  parent, and the same under `-C`, warn with `tcw -C <child folder> project
  provision --component work` and exit 0; in the child itself the advice is
  the plain form. Run exactly as advised, the command fetched the child's
  store and left the parent's untouched, and the child's items are then
  listed.

## The questions

- The AC 38 decision is faithful to both specs: under TCW-113's default
  scope a missing inherited store warns and exits 0, `--scope up|down|all`
  exit 7, every one naming the `-C` command, and the project itself gets the
  plain form. Implement round 3's decision supersedes the "exits 7" in AC 38
  (`spec/spec.md:1761-1762`) for the default scope; the spec text is
  otherwise stale on that point.
- The folder `project_facts` passes is always the active project's, under
  `-C` and `tcw serve` too; every reader of another project's work store goes
  through it.
- The three conflict resolutions are correct. One old command name was left
  by TCW-115's sweep: `skills/configure/references/personal.md:129` said
  "`config show`" without the `tcw ` prefix. The dispatching session
  corrected it to `tcw project config` at this review.
- No TCW-113 code bypasses TCW-115's advice or bound.

No open finding belongs to this change.

## Needs a separate change

Under the default scope, `tcw taxonomy show <term>` in a child whose
parent's taxonomy store is not fetched says only `no such term` (exit 4),
with no warning and no pointer to the fetch command. This is TCW-113's
`show`, and the dispatching session has added it to TCW-113's implement
round 3.
