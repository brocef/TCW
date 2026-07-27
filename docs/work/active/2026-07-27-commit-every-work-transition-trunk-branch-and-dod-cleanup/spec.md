# Specification

The **behavior half** of the original child 2, split because it shares no code
with the configuration half. Sibling:
[Add lifecycle policy config and the hook layer](tcw://W/2026-07-27-add-lifecycle-policy-config-and-the-hook-layer).
Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks).

The design below was written and reviewed as one document before the split; the
sections are carried over unchanged rather than rewritten, so the review that
produced them still applies.

## Capability changes

- **Changed:** `work/start-a-work-item`, `work/complete-a-work-item`,
  `work/submit-a-work-item-for-review`, `work/rework-a-reviewed-work-item`,
  `work/discard-a-work-item` — every transition now commits its own move.

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
| Nothing to commit | **`git status --porcelain` reports no non-`??` entry** for the pathspec | Skip silently. Already committed, or nothing tracked to record. |
| Anything else — `index.lock` held, no write permission, a failing pre-commit hook, a detached or corrupt repo | `git commit` exits non-zero for any other reason | **Report on stderr, exit non-zero.** The item has still moved; the move is not rolled back. |

**Detection is porcelain, not stderr matching.** Three different English
sentences cover the benign cases — `nothing to commit`,
`error: pathspec ... did not match any file(s) known to git` (a source folder git
never knew, because the item was created but not yet committed), and
`nothing added to commit but untracked files present`. All are localized and all
have changed across git versions. Porcelain output is contractually stable and
exits 0 in every case. Each was confirmed by running it, not recalled.

Two consequences that only surfaced by trying it:

- **Untracked entries must be excluded** from the check. A scoped commit records
  tracked content only, so a pathspec holding nothing else has nothing to commit,
  and calling `git commit` anyway produces a benign failure that would be
  misreported as a real one.
- **Pathspecs must be filtered before being passed.** `git commit` fails outright
  if *any* pathspec matches nothing, so a transition's now-empty source folder
  would abort a commit whose destination path is perfectly valid.

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
- **`LifecyclePolicy`, hook execution, `tcw validate` policy rejections, and
  `tcw work lifecycle`** — the sibling child owns all four.
- Stage commits. Nothing runs at the end of a stage, so there is nothing to hang
  one on, and no stage-finalization command is being introduced.
  `auto-commit-transitions` covers **transitions only**.
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
5. A store outside a git repository fails at item *creation*, as it always has
   — not a regression, and pinned so nobody "fixes" it. Every write stages, and
   staging is `git add` with `check=True`. `git_commit_result`'s not-a-repo
   branch is defensive depth for a repo that vanished mid-run, tested directly
   at the function level.
6. A commit that fails for a reason *other* than "nothing to commit" or "not a
   repo" — simulated with a held `index.lock` — reports on stderr and exits
   non-zero, while leaving the item moved. It is not silently swallowed.
7. A transition performed through `tcw serve`'s API is committed too.
8. `start --worktree` produces the status move on the branch, with no duplicate
   commit, and works with `auto-commit-transitions` set to `false`.
9. `trunk-branch` mismatch prints one warning and commits on the current branch;
   matching prints none; an item whose own `branch` field equals `HEAD` prints
   none.
10. A newly completed item has no `dod:` key; an item completed before the change
    keeps its stored one and still loads.
11. `--already-integrated` skips the merge, keeps every other gate, and tolerates
    an already-removed worktree and branch.
12. README, release notes, changelog, and `skills/tcw-work/SKILL.md` describe the
    shipped behavior — including that transitions now commit.

## Risks

- **Auto-commit is the largest behavior change in the epic.** It alters what
  every `tcw work` command does to the repository, including from the web app.
  Path-scoped commits bound the blast radius, and criterion 2 is the one that
  actually proves it.
- **Committing from the store surprises library callers.** Anything embedding
  `FsWorkStore` gets commits it did not ask for. Mitigated by the config flag,
  but the default is deliberate and the release note has to lead with it.
- **Swallowing git failures is the subtle risk.** Two benign conditions must be
  skipped silently and every other must be loud; getting that wrong turns a
  refused write into a reported success. Criterion 6 exists solely for this.

## Notes

`--already-integrated` is completion mechanics rather than commit behavior, so it
sits here only because it has to sit somewhere and it is small. It is the natural
consumer of the `pr` field child 1 added — but no coupling should be invented. If
the two never connect, `pr` was premature and that is worth saying at epic close.
