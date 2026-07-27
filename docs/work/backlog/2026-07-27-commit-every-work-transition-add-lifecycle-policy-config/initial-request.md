# Commit every work transition; add lifecycle policy config

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

Child 2 of 5. Depends on child 1. Owns behavior and configuration; adds no
statuses.

## Scope

- `work.auto-commit-transitions`, default **true** — every transition commits its
  own status move through the existing scoped `git_commit(node, msg, *paths)`,
  extending what `start --worktree` already does. No empty commits. **Stage
  commits stay `[judgment]`**: nothing runs at the end of a stage, so there is
  nothing to hang an automatic stage commit on, and no stage-finalization command
  is being introduced.
- `work.trunk-branch` — compare `HEAD`, warn on mismatch, commit where you are.
  It never checks out or commits to another branch.
- Stop persisting `dod:` — it is a fixed constant on every completed item and
  records nothing. Keep the checklist as a closeout prompt; keep the real gates.
- `LifecyclePolicy` + `WorkStore.lifecycle_policy()`; the FS adapter reads
  node-local `work.lifecycle`. Bindings are **declared, never inferred**:
  `{skill: …}` or `{command: …}`; neither or both fails validation.
- The hook execution contract from the epic spec: node-root cwd, shell execution,
  `TCW_SLUG`/`TCW_STATUS`/`TCW_TRANSITION`/`TCW_NODE_ROOT`, 300s default timeout,
  `pre` hooks abort in declared order, **a failing `post` hook never rolls back**.
- `tcw validate` rejects unknown ids, non-mapping/non-list shapes, blank or
  duplicate refs — and never reorders or disturbs unrelated config.
- `tcw work lifecycle [work-ref]` in human, `--json`, and `--directive` modes.
- `tcw work complete --already-integrated`, for a branch merged outside TCW.

## Done when

- A node with no `work.lifecycle` behaves exactly as before, apart from
  transition commits.
- Every rejected policy shape has a test and an actionable message.
- `--directive` emits one complete instruction, or nothing; exits 0 for both;
  exits non-zero with empty stdout and a stderr diagnostic on any error.
- A qualified descendant item uses its own node's policy.
- Auto-commit creates no empty commits on an existing repository.

## Notes

`auto-commit-transitions` defaulting to true is a **behavior change** — plain
`tcw work start` commits nothing today. It needs a prominent release note, not
just a changelog line.
