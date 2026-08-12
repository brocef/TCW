# Honor the configured work.path at every work-store call site

## Origin

Four GitHub issues, all filed 2026-08-12 by @brocef during a migration of the
`proposit` workspace to child nodes with an external `work.path`, and accepted
together as one item because they are four instances of a single defect: a call
site that hardcodes `docs/work` and the node root instead of resolving through
`FsWorkStore`. Two of them independently name the same shared guard,
`_has_work_store` (`store/fs.py:173`), which tests the `docs/work` directory
before consulting the config.

Reported against `tcw 0.21.0` on macOS 26.5.2 (darwin 25.5.0), editable install
from a local checkout.

| Issue | Call site | Failure mode |
| ----- | --------- | ------------ |
| #15 | `recursion.py` delegate/escalate | Silent — phantom inbox in the code repo, cross-node request lost |
| #16 | `recursion.py` reconcile | Loud — `CalledProcessError`, epics unusable on such a node |
| #17 | `capabilities/cli.py` `_shipped_but_missing` | Silent — check skipped, 79 real drifts unreported |
| #18 | `work/cli.py` start `--worktree` | Silent — worktree metadata staged but never committed |

### Issue #15

GitHub issue [#15](https://github.com/brocef/TCW/issues/15), filed 2026-08-12 by @brocef.

> `tcw work delegate` and `tcw work escalate` write to `<node>/docs/work/inbox`, ignoring the target node's configured `work.path`. Because `_inbox_write` does `inbox.mkdir(parents=True, exist_ok=True)`, the command reports success and silently fabricates a work-store folder in the target's *code* repo. The request lands where no `tcw work inbox list` will ever read it — a lost cross-node request with no error.
>
> ### Environment
>
> - tcw version: 0.21.0
> - OS / platform: macOS 26.5.2 (darwin 25.5.0)
> - Install method: editable (`pip install -e`) from a local checkout
> - Layout: orchestrator node `proposit-app` at `~/Projects/proposit-orchestration`
>   (default store `docs/work`), four registered child nodes whose code repos are
>   nested one level down and whose `tcw-config.yaml` each set
>   `work.path: ~/Projects/proposit-orchestration/docs/<repo-name>/work`.
>   The work stores therefore live in the *parent's* git repo, and each child's
>   own repo has no `docs/work` at all.
>
> ### Steps to reproduce
>
> 1. Configure a child node `proposit-mobile` with `work.path` pointing outside its own repo:
>    ```yaml
>    # proposit-mobile/tcw-config.yaml
>    work:
>      path: /Users/brian/Projects/proposit-orchestration/docs/proposit-mobile/work
>    ```
> 2. Confirm the store resolves: `cd proposit-mobile && tcw work path`
>    → `/Users/brian/Projects/proposit-orchestration/docs/proposit-mobile/work` ✅
> 3. Confirm the child repo has no `docs/work`: `ls proposit-mobile/docs/work` → no such directory
> 4. From the parent node: `tcw work delegate proposit-mobile "migration smoke delegation"`
>
> ### Expected vs. actual
>
> - Expected: the entry is written to the configured store's inbox,
>   `/Users/brian/Projects/proposit-orchestration/docs/proposit-mobile/work/inbox/`,
>   where `cd proposit-mobile && tcw work inbox list` will show it.
> - Actual: exit 0, and it prints
>   ```
>   /Users/brian/Projects/proposit-orchestration/proposit-mobile/docs/work/inbox/2026-08-12-migration-smoke-delegation.md
>   ```
>   A brand-new `proposit-mobile/docs/work/inbox/` directory is created inside the child's code repo. `cd proposit-mobile && tcw work inbox list` does not list it — it reads the configured store, which is empty. The request is silently lost.
>
> `escalate` has the identical defect at `work/recursion.py:251`. It is not visible in my layout only because the root node happens to use the default `docs/work`; the moment a root sets `work.path`, every child's escalation goes into a phantom folder too.
>
> ### Remediation
>
> Both functions hardcode the store location instead of opening the target node's store:
>
> ```python
> # work/recursion.py:240 (delegate)
> return _inbox_write(children[child_ref] / "docs" / "work" / "inbox", ...)
> # work/recursion.py:251 (escalate)
> return _inbox_write(parent / "docs" / "work" / "inbox", title, body, origin, initiative)
> ```
>
> Resolve through `FsWorkStore.open(target).root / "inbox"` — the same adapter `tcw work inbox path` already uses — so the configured `work.path` is honored in both directions.
>
> Separately, `_inbox_write`'s unconditional `inbox.mkdir(parents=True, exist_ok=True)` is what turns a wrong path into a silent success. Creating the *inbox* inside an existing store is reasonable; creating the store's whole parent chain is not. Consider requiring the store root to already exist so a mislocated write fails loudly.
>
> Related: `_has_work_store` (`store/fs.py:173`) returns True on a bare `docs/work` directory *before* consulting the config, so the phantom folder this bug creates then satisfies the node-membership check — a stale or fabricated `docs/work` shadows the configured path.
>

### Issue #16

GitHub issue [#16](https://github.com/brocef/TCW/issues/16), filed 2026-08-12 by @brocef.

> `tcw work reconcile` on an epic whose node uses an external `work.path` dies with an unhandled `subprocess.CalledProcessError` and a raw Python traceback. It runs `git -C <code repo> add -- <absolute path inside the store repo>`; git exits 128 because the path is outside that repository. The rollup is never written.
>
> ### Environment
>
> - tcw version: 0.21.0
> - OS / platform: macOS 26.5.2 (darwin 25.5.0)
> - Install method: editable (`pip install -e`) from a local checkout
> - Layout: orchestrator node `proposit-app` at `~/Projects/proposit-orchestration`
>   (default store `docs/work`), four registered child nodes whose code repos are
>   nested one level down and whose `tcw-config.yaml` each set
>   `work.path: ~/Projects/proposit-orchestration/docs/<repo-name>/work`.
>   The work stores therefore live in the *parent's* git repo, and each child's
>   own repo has no `docs/work` at all.
>
> ### Steps to reproduce
>
> 1. Child node `proposit-core` with `work.path` pointing into the parent's repo (see Environment).
> 2. `cd proposit-core`
> 3. `tcw work new "migration reconcile smoke epic"`, then add `type: epic` and an `initial-request.md` to the created item.
> 4. `tcw work new "migration reconcile smoke task" --initiative 2026-08-12-migration-reconcile-smoke-epic`
> 5. `tcw work reconcile 2026-08-12-migration-reconcile-smoke-epic`
>
> ### Expected vs. actual
>
> - Expected: the rollup block is written into the epic's `initial-request.md` and committed in the repository that owns the store (the same repo every other transition correctly commits to).
> - Actual:
>
> ```
>     subprocess.run(["git", "-C", str(node_root), "add", "--", *live], check=True)
>     ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
>   File "/Users/brian/.pyenv/versions/3.14.6/lib/python3.14/subprocess.py", line 578, in run
>     raise CalledProcessError(retcode, process.args,
>                              output=stdout, stderr=stderr)
> subprocess.CalledProcessError: Command '['git', '-C', '/Users/brian/Projects/proposit-orchestration/proposit-core', 'add', '--', '/Users/brian/Projects/proposit-orchestration/docs/proposit-core/work/backlog/2026-08-12-migration-reconcile-smoke-epic/initial-request.md']' returned non-zero exit status 128.
> ```
>
> `node_root` is the child's **code** repo; the file is in the **parent's** repo. The `initial-request.md` edit is left on disk unstaged and uncommitted.
>
> This makes epics unusable on any node with an external work store — `reconcile` is required "before each coordination decision, after any child status change, and before closeout".
>
> ### Remediation
>
> `work/recursion.py` reconcile uses the node root for both git operations:
>
> ```python
> git_stage(node_root, content)                              # ~:207
> git_commit(node_root, f"tcw work: {msg}", "docs/work")     # :209
> ```
>
> Both should target the store's repository and the store's real relative path — `FsWorkStore` already computes exactly these as `store_git_root` and `root`. The hardcoded `"docs/work"` pathspec on line 209 is wrong for the same reason even when the `git -C` target is fixed: for an external store the correct pathspec is `root.relative_to(store_git_root)`.
>
> Note the pattern is already solved correctly inside `FsWorkStore` (`_stage`/`_rm`/`_mv` all route through `self.store_git_root`) — `recursion.py` just bypasses the store and shells out to git itself.
>

### Issue #17

GitHub issue [#17](https://github.com/brocef/TCW/issues/17), filed 2026-08-12 by @brocef.

> `tcw capabilities drift`'s `shipped-missing` check is gated on the literal directory `<node>/docs/work` existing. On a node with an external `work.path` that directory is gone, so the check returns `[]` unconditionally and drift is silently under-reported — same store, same data, no warning that a check was skipped.
>
> ### Environment
>
> - tcw version: 0.21.0
> - OS / platform: macOS 26.5.2 (darwin 25.5.0)
> - Install method: editable (`pip install -e`) from a local checkout
> - Layout: orchestrator node `proposit-app` at `~/Projects/proposit-orchestration`
>   (default store `docs/work`), four registered child nodes whose code repos are
>   nested one level down and whose `tcw-config.yaml` each set
>   `work.path: ~/Projects/proposit-orchestration/docs/<repo-name>/work`.
>   The work stores therefore live in the *parent's* git repo, and each child's
>   own repo has no `docs/work` at all.
>
> ### Steps to reproduce
>
> Node `proposit-shared` with `work.path` pointing into the parent's repo, and at least one `Missing` capability whose `Planning doc` names a completed work item.
>
> 1. `cd proposit-shared && tcw capabilities drift | grep -c shipped-missing` → **0**
> 2. Create an empty decoy directory that no command reads: `mkdir -p proposit-shared/docs/work`
> 3. `cd proposit-shared && tcw capabilities drift | grep -c shipped-missing` → **79**
> 4. `rmdir proposit-shared/docs/work` → back to **0**
>
> The external store, the capabilities, and the completed items are byte-identical in all three runs. The only variable is whether an *empty, unused* `docs/work` directory exists.
>
> ### Expected vs. actual
>
> - Expected: 79 `shipped-missing` findings in both cases — the node has a work store, it is just configured elsewhere, and `tcw work path` resolves it fine.
> - Actual: 0 findings, reported as `no capability drift`. A migrated node looks clean while 79 real drifts go unmentioned.
>
> ### Remediation
>
> `capabilities/cli.py:203`:
>
> ```python
> def _shipped_but_missing(node, st) -> list[tuple[str, str]]:
>     if not (node / "docs" / "work").is_dir():
>         return []
>     from tcw.store.fs import FsWorkStore
>     work = FsWorkStore.open(node)
> ```
>
> The guard's intent is "degrade to empty when no work node is present", but it tests a filesystem convention rather than asking the store. Since `FsWorkStore.open` already raises `ValueError` when there is no usable store, the guard can just be the `try`:
>
> ```python
>     try:
>         work = FsWorkStore.open(node)
>     except ValueError:
>         return []
> ```
>
> `validate.py` (lines 67-71 and 84-89) already uses exactly this `try FsWorkStore.open / except ValueError` shape for the same question — this call site is the one that didn't get updated.
>
> More generally, `docs/work`-directory existence is used as a proxy for "has a work node" in several places (`store/fs.py:173` `_has_work_store` checks it *before* the config, so a stale directory also shadows a configured path). Auditing those against `FsWorkStore.open` would close the class.
>

### Issue #18

GitHub issue [#18](https://github.com/brocef/TCW/issues/18), filed 2026-08-12 by @brocef.

> `tcw work start --worktree` writes `worktree:`/`branch:` into the item's `state.yaml` and stages it, then commits with a hardcoded `docs/work/...` pathspec against the *code* repo. On a node with an external `work.path` that pathspec matches nothing, `git_commit_result` drops it, and the commit silently no-ops. The worktree metadata is left staged-but-uncommitted in the store repo, where it leaks into whatever the user commits next.
>
> ### Environment
>
> - tcw version: 0.21.0
> - OS / platform: macOS 26.5.2 (darwin 25.5.0)
> - Install method: editable (`pip install -e`) from a local checkout
> - Layout: orchestrator node `proposit-app` at `~/Projects/proposit-orchestration`
>   (default store `docs/work`), four registered child nodes whose code repos are
>   nested one level down and whose `tcw-config.yaml` each set
>   `work.path: ~/Projects/proposit-orchestration/docs/<repo-name>/work`.
>   The work stores therefore live in the *parent's* git repo, and each child's
>   own repo has no `docs/work` at all.
>
> ### Steps to reproduce
>
> 1. Child node `proposit-core` with `work.path` pointing into the parent's repo (see Environment).
> 2. `cd proposit-core`
> 3. `tcw work new "migration worktree smoke" --tag bug`
> 4. `tcw work start 2026-08-12-migration-worktree-smoke --worktree`
> 5. `git -C ../  status --short` (the store repo)
>
> ### Expected vs. actual
>
> Step 4 reports success and the worktree is created correctly:
>
> ```
> started 2026-08-12-migration-worktree-smoke → .../docs/proposit-core/work/active/2026-08-12-migration-worktree-smoke
>   (worktree .../proposit-core/.worktrees/2026-08-12-migration-worktree-smoke)
> ```
>
> The status transition itself commits correctly in the store repo (`tcw work: … → active`) — that part goes through `FsWorkStore` and is fine.
>
> - Expected: the worktree metadata added to `state.yaml` is committed too, leaving both repos clean.
> - Actual: the store repo is left with
>
> ```
> M  docs/proposit-core/work/active/2026-08-12-migration-worktree-smoke/state.yaml
> ```
>
> staged and uncommitted:
>
> ```diff
>  started: '2026-08-12T20:49:52.345335Z'
> +worktree: .worktrees/2026-08-12-migration-worktree-smoke
> +branch: work/2026-08-12-migration-worktree-smoke
> ```
>
> No error is printed. The `git_commit_result` error path exists but never fires, because "commit nothing" is not an error.
>
> ### Remediation
>
> `work/cli.py:555`:
>
> ```python
> paths = [f"docs/work/backlog/{bare}", f"docs/work/active/{bare}", ".gitignore"]
> err = git_commit_result(node, f"tcw work: start {bare} (worktree)", *paths)
> ```
>
> Two problems for an external store: `node` is the code repo rather than the store's repo, and `docs/work/...` is not the store's path. Both are already available on the opened store as `store_git_root` and `root.relative_to(store_git_root)`; deriving the prefix from those fixes it.
>
> The surrounding comment notes the pathspec deliberately names both status folders and that "`git_commit_result` drops pathspecs git has nothing for, so listing the already-committed source folder is harmless" — that tolerance is what converts this from a loud failure into a silent one. Worth checking that at least one intended path survived before treating the commit as done.
>
> Worth noting the feature's premise doesn't fully survive the split either: the comment explains `--worktree` commits regardless of `auto-commit-transitions` so the branch carries the item's own status move. With an external store that move lives in a different repository, so the worktree branch can never contain it. That is inherent to the separation rather than a bug, but the guarantee documented there no longer holds and it may be worth saying so.
>

## Product changes

A node whose `tcw-config.yaml` sets `work.path` should behave like any other
node. Today four commands do not:

- `tcw work delegate` / `escalate` reach the target's real inbox, so a cross-node
  request is readable by `tcw work inbox list` at the other end.
- `tcw work reconcile` writes and commits the epic rollup instead of dying with a
  traceback, which is what makes epics usable on such a node at all.
- `tcw capabilities drift` reports its `shipped-missing` findings rather than
  answering `no capability drift` because a directory it never reads is absent.
- `tcw work start --worktree` leaves both repositories clean.

Cutting across all four: **a write that cannot land should fail loudly.** Three
of the four are silent today, and the silence is the actual harm — a lost
delegation, an under-reported drift, and staged metadata that leaks into the
user's next commit all look like success at the terminal.

## Technical changes

The reports converge on one shape: these call sites reconstruct the store's
location from the node root and the literal string `docs/work`, where
`FsWorkStore` already computes `store_git_root` and `root` correctly and routes
its own `_stage`/`_rm`/`_mv` through them. Resolving through the opened store is
the fix in every case.

Two shared pieces are what make this one item rather than four:

- `_has_work_store` (`store/fs.py:173`) tests the `docs/work` directory *before*
  consulting the config, so a stale or fabricated directory shadows a configured
  path. #15 and #17 flag it independently, from opposite directions.
- `_inbox_write`'s unconditional `inbox.mkdir(parents=True, exist_ok=True)` is
  what converts a wrong path into a silent success — it fabricates the store's
  whole parent chain, not just the inbox.

The abstraction litmus test applies directly here: "where does this node's work
store live" is a store-interface question, and every one of these call sites
answers it with a filesystem convention instead of asking. Fixing the four
without closing that class invites the fifth.

## Meta changes

`--worktree`'s documented guarantee — that the branch carries the item's own
status transition regardless of `auto-commit-transitions` — cannot hold when the
store lives in a different repository. That is inherent to the separation rather
than a defect, so it wants a documentation change, not a behavioral one.

Whether `work.path` pointing outside the node's own repo is a configuration this
project intends to support at all is worth settling before the fix, since it
decides whether these are bugs or an unsupported layout failing loudly.
