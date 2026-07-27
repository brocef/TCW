# Specification

Child 2 of [the lifecycle epic](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks).
Depends on child 1, which shipped the `review` status and the `submit`/`rework`
edges.

Scope is **behavior and configuration**. No new statuses, no new transitions, no
documentation restructure.

## Capability changes

- **Changed:** `work/start-a-work-item`, `work/complete-a-work-item`,
  `work/submit-a-work-item-for-review`, `work/rework-a-reviewed-work-item`,
  `work/discard-a-work-item` — every transition now commits its own move.
- **New:** configure the work lifecycle; inspect the effective lifecycle
  contract.

## Current state

Verified against the code:

- **`FsWorkStore._effect_transition` (`fs.py:2182`) is the single choke point.**
  Every status move — from the CLI *and* from `tcw serve`'s HTTP API — passes
  through it. `start()`, `submit()`, `rework()`, and `complete()` all reach it
  via `WorkStore.transition()`.
- `git_commit(node_root, message, *paths)` (`fs.py:277`) already exists and takes
  a pathspec. Today it has exactly one caller: `_start` in the `--worktree`
  branch (`work/cli.py:468`), committing `"docs/work", ".gitignore"` before
  creating the worktree. **Plain `tcw work start` commits nothing.**
- `complete()` calls `set_field` twice (resolution, `dod`) *before*
  `transition()`, so those writes are already staged when the move happens.
- `dod_checklist()` (`fs.py:1845`) reads an optional `dod.yaml` and otherwise
  returns `DEFAULT_DOD`. `_complete` passes the whole checklist as `dod_ack`
  (`work/cli.py:590`), so the "acknowledgement" is unconditional and the stored
  value is a constant.
- The node config pattern is established: `_config()` (`fs.py:1860`) reads the
  sentinel tolerantly and raises a path-naming error on malformed YAML;
  `_write_tags` shows the read-modify-write that preserves unrelated keys.
- `tcw work drop` deletes rather than transitions (`base.py:1032` → `_delete`),
  so it is not a transition and gets no commit.

## Design

### Auto-commit belongs in the adapter, not the CLI

`_effect_transition` is where it goes. Two reasons, and the second is the one
that decides it:

1. **The prime directive.** "Commit this move" has no abstract analog — a Jira
   store has no commits. It is an FS-adapter private detail by definition.
2. **`tcw serve` performs real transitions.** If auto-commit lived in
   `work/cli.py`, a status moved from the web app would leave the repository
   with an uncommitted `git mv` staged — the exact stranded-state problem this
   feature exists to eliminate, reintroduced through the other door.

```python
def _effect_transition(self, slug: str, to_status: str) -> None:
    src = self._find(slug)
    dst = self.root / to_status / slug
    (self.root / to_status).mkdir(parents=True, exist_ok=True)
    self._mv(src, dst)
    self._commit_transition(slug, src, dst, to_status)
```

**Scope the commit to the two paths involved**, not to `docs/work`:

```python
git_commit(self.node_root, f"tcw work: {slug} → {to_status}",
           str(src.relative_to(self.node_root)),
           str(dst.relative_to(self.node_root)))
```

`git commit -- <paths>` is a partial commit that takes the *working tree* state
of those paths. Passing `docs/work` — which is what the existing `--worktree`
call does — would sweep in every other work item's uncommitted edits. Naming the
source and destination folders keeps the blast radius to the item that actually
moved. This is a deliberate improvement on the existing call site, not a copy of
it.

**No empty commits.** `git commit` exits non-zero with "nothing to commit" when
the pathspec is clean. That is not an error condition here: it means someone
already committed the move, which is fine. Detect it and return quietly rather
than propagating a `CalledProcessError`.

**Not in a git repo at all** — possible for a `tmp_path` store in a test, or a
node whose repo was removed — is also not an error. Auto-commit degrades to a
no-op.

**But "degrade to a no-op" must not become "swallow every git failure".** Those
are three different outcomes and conflating them would hide exactly the errors an
operator needs to see:

| Condition | Detection | Outcome |
|---|---|---|
| Not a git repository | `git rev-parse --git-dir` fails | Skip silently. Not an error. |
| Nothing to commit | `git commit` exits non-zero, stdout says nothing to commit | Skip silently. The move was already committed. |
| Anything else — `index.lock` held, no write permission, a failing pre-commit hook, a detached or corrupt repo | `git commit` exits non-zero for any other reason | **Report on stderr, exit non-zero.** The item has still moved; the move is not rolled back. |

The third row is the one worth getting right. The item moving without a commit
is recoverable — the operator commits it. Silently reporting success when the
repository refused the write is not.

The move is never rolled back on a commit failure: the `git mv` already happened
in both the index and the working tree, and undoing it introduces a second
failure mode worse than the first.

### `work.auto-commit-transitions`

```yaml
work:
    auto-commit-transitions: true    # the default
```

Read through `_config()`, following `registered_tags()`. Absent means `true`;
this is a behavior change on every existing node and the release note must say
so plainly.

Set to `false`, transitions stage the move exactly as they do today and leave
committing to the caller.

### `--worktree` stops double-committing

`_start`'s worktree branch currently commits before `add_worktree`. With
auto-commit the move is already committed by the time `_start` regains control,
so that call becomes wrong — it would either create a second commit or fail with
"nothing to commit".

The ordering constraint is real and must be preserved: the worktree branch is
created *from* the current `HEAD`, so the status move has to be committed before
`add_worktree` runs or the branch will not carry it. The store now guarantees
exactly that. What `_start` still owns is `.gitignore` and the `worktree`/
`branch` fields, which are set *after* the transition — those still need their
own commit, and it must land before `add_worktree`.

So: `_start` keeps a commit, but a narrower one covering `.gitignore` and the
item's `state.yaml`, and it must tolerate "nothing to commit" the same way.
When `auto-commit-transitions` is `false`, `--worktree` still commits — the
worktree flow cannot function otherwise, and silently producing a branch missing
its own status move would be worse than ignoring the setting. **The setting is
documented as not applying to `--worktree`**, rather than left to be discovered.

### `work.trunk-branch`

```yaml
work:
    trunk-branch: main
```

Compare against the current `HEAD` symbolic ref at transition time. On mismatch,
print one warning naming both branches and commit where you are. Never check
out, never commit elsewhere, never refuse.

Unset means no check. `[prompted]`, and therefore testable.

**Suppress the warning inside a TCW-created worktree.** A `--worktree` item is
*supposed* to be on `work/<slug>`, so warning there would fire constantly on the
one workflow that is behaving correctly.

Detection is by the **item**, not by the checkout: suppress when the item being
transitioned carries a non-empty `branch` field and `HEAD` equals it. That reads
one already-persisted field and needs no git plumbing. Probing whether the
current directory is a linked worktree would also catch worktrees TCW knows
nothing about, which is not the case being excused.

### Stop persisting `dod:`

`complete()` drops `self.set_field(slug, "dod", dod_ack)`. The `dod_ack`
parameter stays in the signature — removing it is an interface change for no
gain, and a remote adapter may have somewhere to put it.

The checklist keeps being *printed* by `_complete` before `--confirm`. That is
`[prompted]` and is the only thing it ever really did.

**Items completed before this change keep their stored `dod:`.** Same shape as
child 1's `phase`: the key becomes unread, nothing rewrites it, and no migration
pass is added. Child 1 established this pattern and proved it; child 2 follows
it rather than inventing a second answer.

### `LifecyclePolicy`

A storage-neutral model plus `WorkStore.lifecycle_policy()`. The FS adapter
reads node-local config:

```yaml
work:
    lifecycle:
        stages:
            spec: [{skill: superpowers:brainstorming}]
            plan: [{skill: superpowers:writing-plans}]
        transitions:
            complete:
                pre: [{command: "pytest -q"}]
                post: [{command: "./notify.sh"}]
```

Keyed by the epic's fixed ids. Stages: `inbox`, `request`, `spec`, `plan`,
`implement`, `verify`, `postmortem`. Transitions: `start`, `submit`, `complete`,
`rework`, `discard`.

A binding is `{skill: <ref>}` **or** `{command: <shell>}`, never a bare string.
Neither key or both keys is a validation error. Guessing which a bare string
meant is a class of bug bought for nothing.

Declaration order is significant and must round-trip unchanged.

### `tcw validate` rejections

Each needs a test and a message naming the offending key:

| Rejected | Message must name |
|---|---|
| unknown stage or transition id | the id, and the legal set |
| `work.lifecycle` not a mapping | the key and the found type |
| `stages`/`transitions` not a mapping | the key |
| a stage value that is not a list | the stage id |
| a transition value that is not a mapping of `pre`/`post` | the transition id |
| `pre`/`post` not a list | the transition id and which phase |
| a binding that is not a mapping | the id and the position |
| a binding with neither `skill` nor `command` | the id and the position |
| a binding with both | the id and the position |
| a blank ref | the id and the position |
| a duplicate ref within one id | the id and the ref |

Validation must not reorder bindings or disturb unrelated `tcw-config.yaml`
keys. That is asserted by round-tripping a config with a deliberately unsorted,
comment-free set of unrelated keys.

### Hook execution

**Execution lives in the CLI, not the store.** The store owns the *policy* — a
Jira adapter could serve the same mapping. Running a shell command is a local
concern, and a store method that shells out would be one no remote adapter could
honor.

This has a consequence worth stating rather than discovering: **`tcw serve` does
not run hooks.** A status changed by clicking a button in the web app performs
the transition and its commit, and runs no configured command. Executing
arbitrary shell from an HTTP handler on a click is not a behavior to add by
accident, and the web app is a viewer/editor, not an automation surface.

**This is an accepted asymmetry, not an oversight:** the same user action has
different side effects depending on which surface performs it. It is the right
trade — a locally-served HTTP endpoint that runs configured shell on request is a
meaningfully worse security posture than a CLI the user invoked deliberately —
but it is a real gap, and the web-complete modal should say that hooks did not
run rather than leaving the user to infer it. Documenting it is part of criterion
23; a `pre` hook that would have *blocked* a transition does not block it from
the web app.

For CLI transitions:

- **Working directory** is the node root — the directory holding
  `tcw-config.yaml`. Never the process cwd.
- **Commands run through the shell**, so pipelines and `&&` work. The config
  lives in the user's own repository and is trusted exactly as much as any other
  file there. This is stated so nobody mistakes it for a sandbox.
- **Environment** inherits the caller's, plus `TCW_SLUG`, `TCW_STATUS`,
  `TCW_TRANSITION`, `TCW_NODE_ROOT`.
- **Timeout** defaults to 300s per command, configurable via
  `work.lifecycle.timeout`. A timeout is a failure, and on a `pre` hook it
  aborts.
- **`pre` hooks run in declared order; the first non-zero exit aborts the
  transition.** Remaining hooks do not run and the item does not move.
- **A failing `post` hook never rolls back.** The move and its commit have
  happened; unwinding a committed transition is worse than the failure. TCW
  reports it and exits non-zero so a caller notices, and the item stays where it
  moved to. The exit code is the only signal — this must be tested, because
  "reports the failure but succeeded anyway" is the kind of thing that silently
  regresses to a swallowed exception.
- **Skill bindings are never executed by the CLI.** It cannot invoke a skill;
  only the agent can. A skill binding is reported, never run.
- **TCW waits for the command and nothing more.** If a hook backgrounds a
  process, TCW does not track, wait on, or kill it; the timeout applies to the
  command TCW launched. Reaping stray grandchildren is the hook author's
  problem, and pretending otherwise would mean process-group management for a
  case that has not come up.

#### `pre` hooks run before the store is touched at all

This is an **ordering constraint on the CLI**, and it is the one place the hook
layer can corrupt state if implemented casually. `complete()` writes the
resolution with `set_field` *before* it calls `transition()`. If a `pre` hook ran
inside `complete()`, an aborting hook would leave the item unmoved but already
carrying a resolution — an item that reads as closed while sitting in `active`.

So: the CLI evaluates every `pre` hook for a transition, and only if all of them
pass does it call the store method at all. No `WorkStore` interface change and no
transaction concept is needed — the ordering is entirely within the CLI's
control, which is precisely why hook execution lives there.

Acceptance criterion 15 asserts the item's *fields* as well as its status after
an aborted `complete`, because "did not move" alone would pass even if the
resolution had been written.

**What is deliberately not solved:** a crash, `SIGKILL`, or disk failure
*between* the store's own `set_field` and `_effect_transition` still leaves a
resolution on an unmoved item. That window exists today, is not created by this
change, and closing it needs transactional multi-file writes in the FS store —
which is already tracked as
[Transactional multi-file writes in the Fs store](tcw://W/2026-07-03-transactional-multi-file-writes-in-the-fs-store).
This child must not grow into that.

### `tcw work lifecycle [work-ref]`

Read-only. Never executes, never changes state.

- **Human** (default): every id in lifecycle order with its objective, allowed
  inputs, required artifact, TCW-owned destination path, and configured bindings.
- **`--json`**: the same contract, stable enough for tooling and tests.
- **`--directive [--stage <id> | --transition <id>]`**: for Claude's dynamic
  context injection. Emits **one complete instruction line or nothing at all** —
  never a bare value — so an unbound id renders as empty rather than as a broken
  sentence.

```
$ tcw work lifecycle --stage spec --directive
For this stage, invoke the superpowers:brainstorming skill.

$ tcw work lifecycle --stage implement --directive
                                    (unbound: empty, exit 0)
```

Bound and unbound are **both success** (exit 0). Failure is distinguishable: on
an unreadable config, an unknown id, or an unresolvable work reference,
`--directive` writes **nothing to stdout**, a diagnostic to stderr, and exits
non-zero. A silent empty injection must never mask an error.

`--directive` never executes a binding. For a command binding it emits an
instruction naming the command; running it stays the agent's step.

Without a work reference it reports the local node's policy. With a local or
qualified reference it resolves the item's owning node and reports that node's
policy — so a qualified descendant uses its own configuration.

### `tcw work complete --already-integrated`

For an item started with `--worktree` whose branch was merged outside TCW,
typically by a merged pull request.

- Requires the same `--confirm` and resolution.
- **Skips the auto-merge**, and nothing else.
- Every other gate runs unchanged: blockers, the epic-children check, capability
  reconciliation, `--confirm`.
- Tolerates a worktree or branch an external flow already removed.
- Attempts safe cleanup of whatever TCW-created worktree state remains.

Default completion keeps auto-merging. Creating a pull request does not make an
item complete — it stays `active` or moves to `review`. When the PR merges, the
operator resumes closeout with `--already-integrated`.

## Out of scope

- Any new status or transition — child 1 shipped those.
- What a methodology *document* contains, and `tcw work methodology` — child 3.
- Stage documents, the skill restructure, commands — child 4.
- Stage commits. Nothing runs at the end of a stage, so there is nothing to hang
  one on, and no stage-finalization command is being introduced.
  `auto-commit-transitions` covers **transitions only**.
- A repo-local `docs/work/lifecycle/<stage>.md` override or any
  `bare-wins-local` resolution tiering.
- **Concurrency.** Two processes transitioning the same item simultaneously —
  two agents, or the CLI and `tcw serve` at once — can race: one `git mv`
  succeeds and the other finds its source gone, or both contend on `index.lock`.
  Auto-commit widens that window because a commit takes longer than a rename.

  This is **not solved here and must not be**. TCW has no locking today, and the
  problem already has an owner:
  [Concurrency-safe work claims for multi-agent repos](tcw://W/2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp).
  What this child owes is that the failure be *legible* rather than a raw
  traceback: a lost race must report that the item is no longer where it was, and
  an `index.lock` collision falls into the "report and exit non-zero" row of the
  commit-failure table above.

## Acceptance criteria

1. Every transition — `start`, `submit`, `rework`, `complete` (both
   resolutions), and `discard` — leaves a commit containing exactly the moved
   item.
2. An unrelated modified file elsewhere under `docs/work/` is **not** swept into
   a transition commit.
3. `auto-commit-transitions: false` produces a staged-but-uncommitted move,
   matching today's behavior.
4. A repeated transition attempt on an already-committed move does not raise;
   no empty commit is created.
5. A store opened outside a git repository still transitions, without error.
5b. A commit that fails for a reason *other* than "nothing to commit" or "not a
    repo" — simulated with a held `index.lock` — reports on stderr and exits
    non-zero, while leaving the item moved. It is not silently swallowed.
6. A transition performed through `tcw serve`'s API is committed too.
7. `start --worktree` produces the status move on the branch, with no duplicate
   commit, and works with `auto-commit-transitions` set to `false`.
8. `trunk-branch` mismatch prints one warning and commits on the current branch;
   matching prints none; inside a TCW worktree prints none.
9. A newly completed item has no `dod:` key; an item completed before the change
   keeps its stored one and still loads.
10. A valid policy round-trips in declared order, with unrelated
    `tcw-config.yaml` keys untouched.
11. Every row of the rejection table has a test whose message names the
    offending id.
12. `tcw work lifecycle` and `--json` expose the same contract.
13. `--directive` emits one complete instruction when bound, empty when unbound,
    exit 0 for both; and on every error path exits non-zero with empty stdout
    and stderr output.
14. A qualified descendant item resolves its own node's policy, not the
    anchor's.
15. A `pre` hook exiting non-zero aborts the transition, the item does not move,
    **and no field was written** — an aborted `complete` leaves no `resolution`
    on the item. Later `pre` hooks do not run.
16. A `post` hook exiting non-zero leaves the item moved and committed, and
    `tcw` exits non-zero.
17. A hook runs with cwd at the node root and sees all four `TCW_*` variables.
18. A hook exceeding the timeout is treated as a failure.
19. A skill binding is reported and never executed.
20. `tcw serve` runs no hooks.
21. `--already-integrated` skips the merge, keeps every other gate, and tolerates
    an already-removed worktree and branch.
22. A node with no `work.lifecycle` behaves exactly as before, apart from
    transition commits.
23. README, release notes, changelog, and `skills/tcw-work/SKILL.md` describe the
    shipped behavior.

## Risks

- **Auto-commit is the largest behavior change in the epic.** It alters what
  every `tcw work` command does to the repository, including from the web app.
  Path-scoped commits bound the blast radius, and criterion 2 is the one that
  actually proves it.
- **Committing from the store surprises library callers.** Anything embedding
  `FsWorkStore` gets commits it did not ask for. Mitigated by the config flag,
  but the default is deliberate and the release note has to lead with it.
- **The `pre`-abort path can leave a partial state** if a hook fails after
  `complete()` has already run `set_field` for the resolution. Hooks must
  therefore run **before** `complete()` is called at all, not inside it — a
  constraint on the CLI's ordering that criterion 15 must check by asserting the
  resolution is also absent after an aborted `complete`.
- **Skill bindings cannot fail closed on Codex**, which cannot enumerate skills.
  Nothing may depend on that check firing. This is the assumption most likely to
  be quietly reintroduced.
- **Scope.** This is the largest child. If it needs splitting, the natural seam
  is auto-commit + `dod` (behavior) versus `LifecyclePolicy` + hooks +
  `lifecycle` (configuration) — they share no code.

## Notes

`--already-integrated` sits oddly in this child: it belongs to completion
mechanics, not to configuration or commits. It is here because the epic plan put
it here, and because it is small. If this child needs splitting, it moves with
the behavior half.

The `pr` field child 1 added is `--already-integrated`'s natural companion —
record the PR, then complete against it — but nothing in this child *requires*
`pr`, and no coupling should be invented. If the two never connect, `pr` was
premature after all and that is worth saying out loud at epic close.
