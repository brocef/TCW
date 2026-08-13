# Honor the configured work.path at every work-store call site

## Capability changes

Changed:

- `work/configure-the-work-store-location`
- `work/manage-the-work-inbox`
- `work/start-a-work-item`
- `work/complete-a-work-item`
- `capabilities/detect-capability-drift`

No taxonomy change is needed. The registered `configurable-work-store-location`
feature already covers the behavior, and this work restores the supported
capabilities to their documented configuration-aware semantics.

## Problem

`FsWorkStore.open` resolves the configured store root and the Git repository
containing it (`tcw/store/fs.py:1922-1952`), and its write primitives stage in
that repository (`tcw/store/fs.py:1954-1961`). Several callers bypass those
values and reconstruct a default filesystem layout instead:

- work-store discovery accepts a literal `<node>/docs/work` before opening the
  configured store (`tcw/store/fs.py:172-179`), so a stale or fabricated default
  folder can shadow an invalid configured store;
- delegation and escalation write to literal child or parent `docs/work/inbox`
  paths (`tcw/work/recursion.py:231-251`), while `_inbox_write` creates the
  entire supplied parent chain (`tcw/work/recursion.py:217-228`), turning a bad
  target into a successful but unreadable request;
- epic reconciliation edits the item through the opened store but stages and
  commits through the code node with a `docs/work` pathspec
  (`tcw/work/recursion.py:170-209`);
- capability drift returns no shipped-but-missing findings unless the literal
  default directory exists, even though it then opens the configured store
  (`tcw/capabilities/cli.py:199-206`); and
- `start --worktree` writes item metadata through the store, then commits both
  it and the code-repository `.gitignore` using one code-repository commit with
  hardcoded work paths (`tcw/work/cli.py:537-560`). When the store and code are
  in different repositories, one commit cannot contain both sets of changes.

These defects make a supported external-store layout silently lose inbox
requests, omit real drift, or leave staged metadata behind, and make epic
reconciliation fail with an unhandled Git error.

## Goals

- Make every runtime call site that asks whether a node has a work store, reads
  one, writes one, or commits one resolve that store through `FsWorkStore`.
- Keep the owning code node, configured work root, and store Git root distinct;
  use each only for the operations it owns.
- Make delegate, escalate, reconcile, capability drift, and `start --worktree`
  behave correctly when the configured store is in a different Git repository.
- Fail clearly when an intended store write or commit cannot land; do not report
  success after writing to a phantom location or leaving intended changes
  staged.
- Preserve behavior for the default `docs/work` layout and for nodes that truly
  have no usable work store.
- Cover the defect class with a repo-wide audit and two-repository regression
  fixtures.

## Non-goals

- Moving, merging, or otherwise migrating an existing work store.
- Changing project identity, reference qualification, lifecycle-hook ownership,
  or the location of code worktrees.
- Adding work-store paths or Git operations to the abstract `WorkStore`
  interface. Store-root and repository routing remain filesystem-adapter
  concerns.
- Making a code worktree branch contain lifecycle artifacts stored in another
  repository. That cross-repository history cannot be represented by one Git
  branch.
- Changing the meaning of `work.auto-commit-transitions`, `--force`, or
  `--take-over`.

## Design

Treat `FsWorkStore.open(node_root)` as the single authority for whether the node
has a usable work store and, after it opens, for the resolved `root`, owning
`node_root`, and `store_git_root`. Remove the fast path in `_has_work_store` that
accepts a default directory without validating configuration. Callers that are
explicitly allowed to operate without a work component may catch the same
`ValueError` contract already used by node discovery and validation
(`tcw/store/fs.py:125-139`, `tcw/validate.py:62-70`).

Route delegate and escalate to the target store's `root / "inbox"`. Inbox entry
creation may create a missing inbox directory inside an already validated store,
but it must not create the store root or its ancestors. A failed target-store
resolution or write must surface as a command error and must not leave a phantom
`docs/work` tree.

Route reconciliation staging and commits through the epic store's
`store_git_root`, with pathspecs derived from resolved paths relative to that Git
root. Preserve its idempotent no-change behavior and its existing
auto-completion/capability gates.

For capability drift, attempt to open the work store and degrade to an empty
shipped-but-missing set only when no usable store exists. An external configured
store participates identically to a default store; a decoy default directory
does not change the result.

Split `start --worktree` persistence along repository ownership. Commit
work-item state and any pending transition in the store repository using paths
derived from the opened store. Commit `.gitignore` in the code repository when
it changed. Create the code worktree only after both required commits succeed,
and report partial progress clearly if either commit fails. The worktree branch
is based on the code repository and therefore carries code-repository setup,
not lifecycle files owned by a different repository.

Audit production Python call sites for literal `docs/work` construction and
node-root Git operations applied to paths returned by `FsWorkStore`. Retain
literals that define the default layout, initialization, resolved-status ignore
rules, validation fallback for malformed nodes, or documentation; replace only
operations whose correctness depends on the active configured store.

## Acceptance criteria

1. With a child node whose `work.path` points into a separate parent Git
   repository, `tcw work delegate` writes exactly one entry under the child's
   configured inbox; `tcw work inbox list` from the child sees it, and no
   `<child>/docs/work` path is created.
2. With a parent node using an external store, `tcw work escalate` writes the
   entry to that configured inbox and creates no default-store tree.
3. Inbox writing refuses to manufacture a missing store root or ancestor chain,
   and the CLI returns a clear non-zero error without claiming success.
4. `_has_work_store` and all registered-node discovery paths validate the
   configured store even when a decoy `<node>/docs/work` directory exists; an
   invalid configured path is not shadowed by that directory.
5. `tcw work reconcile <epic>` on an external store updates and stages the
   rollup in the store repository. With commit enabled, the commit contains the
   resolved work-store path and leaves it clean; the code repository receives no
   work-artifact change. Re-running an unchanged reconciliation remains a no-op.
6. `tcw capabilities drift` reports the same shipped-missing findings for the
   same configured store whether or not a decoy default work directory exists.
   A node with no usable work store retains the documented graceful behavior.
7. `tcw work start <slug> --worktree` with separate code and store repositories
   commits the work transition and `worktree`/`branch` fields in the store
   repository, commits a changed `.gitignore` only in the code repository,
   creates the code worktree only after required persistence succeeds, and
   leaves both repositories without staged TCW changes.
7b. With the default in-repository layout that start still produces exactly one
   commit, carrying both status paths and `.gitignore`, as it does today. Neither
   layout's commit contains any work-store path other than the started item's —
   a second work item staged in the store repository stays staged.
8. A forced Git failure in each write/commit path returns non-zero with an
   actionable error and does not silently proceed as though the intended write
   was persisted.
9. Equivalent tests for the default in-repository `docs/work` layout continue
   to pass, including transition auto-commit on and off.
10. A repo-wide production-code scan accounts for every literal `docs/work`
    path and every Git operation involving a work-store path; no remaining call
    site independently reconstructs the active store location.

## Risks

- `start --worktree` spans two repositories and cannot be atomic across them. A
  failure after the first commit can leave durable partial progress, so command
  ordering and error messages must make the recoverable state explicit.
- Tightening `_has_work_store` may expose malformed configurations that a decoy
  default directory previously hid. That is intentional, but discovery callers
  must preserve their established skip-versus-error contracts.
- The tightening is broader than the decoy case. `FsWorkStore.open` requires
  `inbox` plus every `WORK_STATUSES` folder, where the fast path accepted any
  `docs/work` directory — so a default-layout store missing a later-added status
  folder disappears from node discovery instead of merely failing at use. The
  implementation must test that case and settle it explicitly (strict plus a named
  repair command in the release notes, or a structural allowance for default
  stores), rather than inheriting whichever behavior falls out.
- Narrow pathspec derivation must handle stores at repository-relative nested
  paths without sweeping unrelated staged changes into TCW commits.
- Inbox-store validation must prevent phantom roots without breaking an
  otherwise valid store whose `inbox` leaf alone needs restoration.
- Tests using a single repository can pass while repository ownership remains
  wrong; the regressions require distinct, initialized Git repositories and
  cleanliness assertions in both.
