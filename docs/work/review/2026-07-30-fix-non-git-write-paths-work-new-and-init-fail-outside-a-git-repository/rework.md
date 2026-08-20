# Rework — Fail fast with clear errors on non-Git writes

## Verdict

**Rejected at `verify`.** The user's acceptance was conditional on an adversarial
Codex review passing, with the standing instruction to rework anything it found
"even if not directly related to these changes". It found five defects; all five
were reproduced independently before this verdict was written. Three of them
break the item's own promise — *refuse before the first filesystem mutation* —
so the item goes back to `implement` rather than closing with caveats.

The verification that did pass stands and does not need re-doing: `pytest` green
at 1788, the shipped-binary reproduction of criteria 1-4, and the capability
ledger (reconciled during `verify` in `92d1736`, which added the two entries
planning had missed — `work/delegate-a-request-to-a-child-node` and
`work/escalate-a-request-to-the-parent-node`).

## The common root cause

**Every high-severity finding is the same mistake: a write that touches a
repository other than the one the guard checked.**

The implementation guards the store's own repository — `store_git_root` for
`FsWorkStore`, `node_root` for the tree stores — which is right, and
`test_each_store_checks_the_repository_it_actually_writes_to` was written to pin
exactly that. But three flows write to **two** repositories:

| Flow | Repository the guard checks | Repository it also writes |
| ---- | --------------------------- | ------------------------- |
| `work start --worktree` | the work store's (`work.path`) | the code node's — `.gitignore`, the worktree |
| `work complete` on a worktree item | the work store's | the code node's — the merge-back |
| `init --work-path` | *(checked last, after scaffolding)* | both: the node's config, the external tree |

With a default store the two are the same directory and the guard covers both,
which is why the whole 28-command matrix missed it: it only ever exercised a
default store, and removed every repository in the graph at once. Finding 5 is
the same blind spot in miniature — the test named for external stores never
built one.

## What has to change

Ordered as implementation should take them; 1-3 are the acceptance blockers.

### 1. `work start --worktree` mutates two things before it refuses — HIGH

`tcw/work/cli.py:_start` calls `st.start(...)` (guarded against the work store's
repository, which is fine) and then `ensure_worktree_ignored(st.node_root)`,
which writes the code node's `.gitignore` and only then stages it. When the
work store is external and the code node's repository is gone, the store guard
passes, the item moves, `.gitignore` gains `.worktrees/`, and `git add` fails.

Reproduced: external store repository intact, `rm -rf code/.git`, then
`tcw work start <slug> --worktree --owner t@t` →

```
tcw: git command failed (exit 128): git -C .../code add -- .../code/.gitignore
rc=1
2026-08-20-a-thing  [active]          # moved
gitignore: .worktrees/|               # written
```

`spec.md:374` asserts `ensure_worktree_ignored` is "unreachable outside a
repository" because its caller runs after `st.start`. That reasoning silently
assumes the node and the store share a repository. **The spec is wrong here, not
just the code** — fix the row as part of this rework.

Fix: `--worktree` needs the code node's repository, so `_start` must require it
before it touches the store at all. Keep the criterion-1 wording — the shared
`NOT_A_REPOSITORY` sentence is exactly right for "the code node is not in a
repository", and reusing it keeps `work start --worktree` passing the pinned
one-wording test in the both-missing case.

### 2. `work complete` skips the merge-back and reports success — HIGH

`merge_worktree` (`tcw/store/fs.py`) treats *any* non-zero
`git rev-parse --verify refs/heads/<branch>` as "branch already gone — nothing to
merge" and returns `None` (success). Outside a repository that lookup fails with
128, so the merge is skipped, `_complete` proceeds, and the item reaches
`completed` with the work branch unmerged and the worktree still on disk.

Reproduced: start with `--worktree` with both repositories present, `rm -rf
code/.git`, then `tcw work complete <slug> --resolution done --confirm --force` →

```
completed 2026-08-20-a-thing (done) → .../store/work/completed/2026-08-20-a-thing
rc=0
worktree dir still there: yes
```

Pre-existing, and in scope by the user's explicit instruction. It is also the
worst of the five: a partial write announces itself, a false completion does not.

Fix: `merge_worktree` already has a "return an error message" contract and
`_complete` already renders it and returns 1. Detect the missing repository and
return that message instead of `None`. Fail closed, not open.

### 3. `init --work-path` scaffolds everything, then refuses — HIGH

`init()` (`tcw/store/fs.py`) writes the sentinel, rewrites `tcw-config.yaml`
with `work.path`, creates the whole external status tree and every `.gitkeep`,
and *only then* checks `git_root(base)` and raises. The refusal is real but the
residue is total, which contradicts the release note's unconditional claim that
a refused write "leaves the project exactly as it found it".

Reproduced: `tcw init work --id demo --work-path <non-repo>/work` → rc=1, with
`tcw-config.yaml` carrying the path and all six status folders created.

Fix: hoist the check above every mutation. Note **why** it was written late:
`git_root` shells out to `git -C <path>`, which fails on a path that does not
exist yet, so checking the target directly would wrongly refuse a legitimate
`--work-path <repo>/new/sub/dir`. The early check has to resolve to the nearest
**existing** ancestor of the target and test that. Keep the existing wording
(`work.path target is not inside a Git repository: …`) and keep the late
`target_git` computation, which the ignore rules still need.

### 4. The `CalledProcessError` handler mis-renders a string `cmd` — LOW

`tcw/cli.py:main` does `shlex.join(str(a) for a in error.cmd)`.
`CalledProcessError.cmd` is legitimately either a sequence or a string; given a
string it iterates characters and prints `g i t ' ' s t a t u s`. No current
raiser passes a string — every `check=True` call in the adapter uses an argv
list — so this is latent, not live. It is three tokens to fix and the handler's
whole point is that it is generic.

### 5. The external-store test never builds an external store — LOW

`tests/test_non_git_writes.py::test_each_store_checks_the_repository_it_actually_writes_to`
constructs its work store where `store_git_root == node_root == root`, so it
passes even if `FsWorkStore._write_git_root` wrongly inherited the base
implementation. It is the one test that was supposed to cover the split-ownership
case, and it is the reason findings 1 and 2 survived.

Fix: give it a genuinely external store (work store in one repository, node in
another) and assert the two roots differ before asserting which one is checked.
Then add the split-ownership shape the matrix lacks — **external work-store
repository present, code-node repository absent** — as coverage for 1 and 2.

## Not in scope for this rework

- `remove_worktree` warning rather than failing outside a repository, on the
  discard path. Reached only after the merge-back has been skipped by design
  (`--already-integrated`) or is not applicable (a discard), and a discard has no
  branch to lose. Left alone deliberately.
- `docs/work/.claiming/` accumulating, already recorded in `outcome.md` as
  observed-and-not-fixed.

## Artifacts this invalidates

- `spec.md:374` — the `ensure_worktree_ignored` row's "unreachable outside a
  repository" reasoning. Corrected as part of this rework.
- `outcome.md` — its acceptance-criteria table stays true for a default store but
  overstates coverage; the next `outcome.md` supersedes it.
- `docs/release-notes/upcoming.md` — "leaves the project exactly as it found it"
  is now a claim about `init --work-path` too.
