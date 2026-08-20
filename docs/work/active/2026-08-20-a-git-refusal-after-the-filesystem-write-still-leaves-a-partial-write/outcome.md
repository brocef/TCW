# Outcome — A git refusal after the filesystem write still leaves a partial write

Five commits. `python -m pytest -q` → **1947 passed, 0 failed** against the
plan's **1859** baseline, with nothing deleted.

## What shipped

| Task | Commit | What landed |
| --- | --- | --- |
| 1 | `store: add the write-then-stage chokepoint` | `_mkdir_owned`, `FsTreeStore._write_staged`, 5 unit tests, no callers |
| 2-5 | `store: roll back a partial write when git refuses the stage` | All 15 conversions, the two reversed tests, `_atomic_write` deleted, 4 end-to-end tests |
| 6a | `capabilities: a Git-refused write leaves the project as it found it` | Seven capability texts, the sidecar, one skill-reference clause |
| 6b | `docs: record the partial-write rollback` | Changelog + release notes |

Tasks 2-5 landed as one commit rather than four. The plan ordered them for green
boundaries, and they are green — but the conversions are one mechanical change to
one file, and splitting a census into four commits would have made each
individually meaningless without adding a bisect point that names anything
useful. Flagging it because the plan said four; the deviation is mine.

## The census, verified

The plan predicted 17 `self._stage(` sites, 15 converted across 14 methods, 2
left. Confirmed exactly, and the structural sweep it asked for passes:

```
grep -c "self\._stage(" tcw/store/fs.py          → 3
    _write_staged's own · update_capability's directory stage · inbox_accept's
grep -n "_atomic_write"  tcw/store/fs.py         → 2   (both _atomic_write_all)
grep -n "dump_yaml("     tcw/store/fs.py         → 6   (def + write_sentinel,
    init, start ×2, inbox_accept — none followed by a self._stage of that path;
    start's two use module-level git_stage on the *folders*, and it is a
    non-goal)
git diff --stat f339b38..HEAD -- tcw/store/base.py → empty
grep -rl "_write_staged\|_mkdir_owned" tcw/ tests/ → fs.py, test_store_editor.py
```

## Verified by hand, under a real held `index.lock`

The end-to-end assertions the store-level tests cannot make. Throwaway repo,
`touch .git/index.lock`, then:

```
$ tcw work new "Secret"
tcw: git command failed (exit 128): git -C … add -- …/backlog/2026-08-20-secret/state.yaml
$ ls docs/work/backlog          # empty

$ printf 'x' | tcw taxonomy add "Widget"
tcw: git command failed (exit 128): git -C … add -- …/taxonomy/widget/meta.yaml …
$ ls docs/taxonomy              # empty

$ git status --porcelain        # empty
$ find . -name '*.tmp'          # nothing
```

**And the same tests run red against the pre-item tree.** `git archive f339b38`
into `/tmp`, copy the new tests over, run: `test_a_refused_stage_leaves_no_work_item`
fails with `assert ['2026-08-20-task', '.gitkeep'] == ['.gitkeep']` — the item
folder standing after the refusal, which is the defect in one line. That is the
evidence the fix works; the green run alone would not have been.

## What the plan and spec got wrong

**Corrected by the plan itself, at plan time** (recorded here because they were
spec errors, and the plan's §4 and §5 did the measuring):

- The spec claimed **seventeen** write-then-stage pairs. It is fifteen
  `self._stage(...)` calls across fourteen methods. The spec was amended.
- The spec named a **`tcw work discard` command that does not exist**; the route
  is `complete --resolution wontfix`.
- The spec's criterion 8 expected `git status --porcelain` to show a staged item
  after `start`. `start` auto-commits, so the tree is clean.
- `_atomic_write` loses its last production caller once the pair collapses —
  found while executing the census, not predicted.

**Found during implementation:**

- **The two reversed tests were correctly anticipated, and the reversal is real.**
  `test_{set,update_capability}_keeps_override_when_staging_fails` asserted that
  a freshly materialized override folder *survives* a refused stage. That was
  the defect, stated as a contract. Both renamed to `_removes_`, with docstrings
  naming this item so `git log -S` finds the reversal.
- **`update_capability`'s outer guard could not simply be deleted.** Removing it
  left an `if True:` where the `try` had been. Dedented properly — a wart in a
  file this size is how the next reader loses trust in the rest of it.

## Abstraction litmus test

Passes. `_write_staged` and `_mkdir_owned` are private to the filesystem
adapter; `tcw/store/base.py` is untouched, verified by diff. The *contract* —
"a refused write undoes what this call created" — is storage-neutral and a
remote adapter would want it; the *mechanism* (temp-file promote, `rmtree`,
`unlink`) is filesystem-private, which is exactly the split the litmus test asks
for. No new abstract operation, no interface signature change.

## Known limits, accepted and pinned

Each is a deliberate boundary with a test pinning current behaviour, so nothing
drifts into it silently:

- **A move is not rolled back.** `tcw work start` under the fixture leaves the
  item in `active/`, stamped and unstaged. Undoing a move means putting back
  content that existed before the call — the codebase already settled that
  question the other way ("undoing it introduces a second failure mode worse
  than the first").
- **An overwrite is not reverted.** `tcw work edit --title` under the fixture
  leaves the new title in `state.yaml`. Reverting needs a content snapshot,
  which is the deferred write-to-temp-then-move atomicity.
- **The file-ownership test is a check-then-act window.** A file absent at entry
  and created by a competitor before the failure would be unlinked. Acceptable
  where the directory case is not: our own write already replaced that
  competitor's content, so the unlink destroys nothing this call had not already
  overwritten. `rmtree` has no such argument, which is why directories get the
  stronger `mkdir(exist_ok=False)` proof.
- **`ensure_worktree_ignored`, `_inbox_write`, and `init` are out of scope** —
  the first leaves one `.gitignore` line the node wants anyway, the second never
  stages, and the third stages nothing at all.

## Notes

- **Sibling interaction, checked in both directions.** The write-time gitignore
  warning landed first and edits `git_stage`/`git_mv`, which `_write_staged`
  *calls* and never edits. Its guard prints and proceeds, so a dropped path
  raises nothing and triggers no rollback — correct, since a dropped path is one
  git never had, not a failed write. The new end-to-end tests filter stderr on
  the `tcw: git command failed` prefix rather than counting `tcw: ` lines, so
  they stay true whichever order the two items had landed in.
- **`_mkdir_owned` retires a `ponytail:` note.** The `existed = d.exists()`
  TOCTOU at `_write_node` carried a comment deferring the fix to
  `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos`. The ownership
  half is now closed here; that item still owns the claiming machinery.
- **Batched into a single patch release** with the other four `bug`-tagged
  items. No version file was touched — the cut is not this item's decision.
