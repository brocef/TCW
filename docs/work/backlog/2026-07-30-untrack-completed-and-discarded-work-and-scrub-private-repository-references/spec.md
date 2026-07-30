# Spec: untrack resolved work, scrub private repository references

## Capability changes

```yaml
new:
    - work/keep-resolved-work-out-of-git
```

Seeded `Missing` at planning (`cap-7e064f`), `Planning doc` and
`Subject=work-item/transition` already set. Nothing else in the ledger moves:
[Complete a work item](tcw://C/work/complete-a-work-item) and
[Discard a work item](tcw://C/work/discard-a-work-item) keep their current
contract — a node that ignores nothing sees no behavior change at all.

## Problem

Two independent problems, joined only by "this is a public plugin repo".

**A. Resolved work accumulates in the tracked tree.** `docs/work/completed/`
holds 76 item folders and `docs/work/discarded/` holds 7. They are this repo's
own dogfooding history, not part of what the plugin ships, and they grow without
bound.

The obvious fix — gitignore both — **does not work on its own**, and the reason
is in the transition mechanic. `_effect_transition` (`tcw/store/fs.py:2391`)
calls `self._mv(src, dst)` → `git_mv` (`tcw/store/fs.py:270`), which is:

```python
subprocess.run([... "add", "--", str(src)], check=True)
subprocess.run([... "mv", "--", str(src), str(dst)], check=True)
```

`git mv` does not consult `.gitignore` for its destination. Verified in a
scratch repo: with `completed/` ignored, `git mv a/f.md completed/f.md`
succeeds and stages `R a/f.md -> completed/f.md`, and the following commit
records the file at its new, supposedly-ignored path. So every future
`tcw work complete` would re-add the item the ignore was meant to exclude —
the ignore would look like it worked while doing nothing.

The same `_mv` is reached by re-parenting (`fs.py:2735`), so the fix belongs in
`git_mv`, not in the completion path.

**B. A private project is named in the repo.** A case-insensitive grep finds it
in `docs/plan/phase-5-work.md`, `docs/plan/phase-6-beyond.md`, two backlog
items' `initial-request.md`, and eight files under `docs/work/completed/`.

## Goals

1. `docs/work/completed/` and `docs/work/discarded/` are gitignored and out of
   the index; the files stay on disk.
2. A completion or discard into an ignored status folder produces a commit that
   **removes** the item from the tracked tree, leaves a clean working tree, and
   does not error.
3. No tracked file names the private project, and the surrounding text still
   makes sense.

## Non-goals

- **No history rewrite.** Past commits keep the folders. Purging them would
  rewrite every SHA, need a force-push, and break clones and release tags.
- **No on-disk scrub under `docs/work/completed/`.** Those files leave the
  repository via goal 1; editing them is churn with no effect on what ships.
- **No new config knob.** "Is this path ignored?" is already expressed by
  `.gitignore`; a `work.ignored-statuses` setting would be a second source of
  truth for the same fact.
- **No change to which statuses exist**, and no status-specific code. The fix is
  generic over destinations.

## Design

### 1. Make `git_mv` ignore-aware (`tcw/store/fs.py`)

Add a small predicate and one branch:

```python
def git_ignored(node_root: Path, path: Path) -> bool:
    return subprocess.run(["git", "-C", str(node_root), "check-ignore", "-q",
                           "--", str(path)], capture_output=True).returncode == 0
```

In `git_mv`, when the destination is ignored: untrack the source
(`git rm -rq --cached --ignore-unmatch -- <src>`) and move it with
`shutil.move`, skipping `git mv` entirely. Otherwise, today's path unchanged.

`--ignore-unmatch` covers an item created but never committed, where git has
nothing to remove. `check-ignore` outside a repo exits non-zero, so a non-repo
store falls through to the existing behavior — no new failure mode.

**Litmus test.** "Could a non-filesystem store implement this?" — the operation
is still *effect a transition*; how a store keeps its own bookkeeping tidy is
its business. `check-ignore` and `git rm --cached` are git plumbing that lives
in `git_mv`, an FS-adapter private helper. No store-interface method changes, no
model change. Passes.

### 2. The scoped commit needs no change

`_commit_transition` (`fs.py:2409`) commits scoped to `[src, dst]` via
`git_commit_result`, which filters pathspecs through
`_has_committable_changes` (`fs.py:288`). For an ignored destination
`git status --porcelain -- <dst>` prints nothing, so `dst` is dropped and only
`src` — showing `D` staged deletions — is passed to `git commit`. That filter
exists precisely so a pathspec git has nothing for cannot abort the commit
(`fs.py:340-344`). Verified end to end in a scratch repo: commit succeeds,
records the deletion, and `git status --short` is empty afterwards.

### 3. This repo's `.gitignore` and index

Append `docs/work/completed/` and `docs/work/discarded/`, then
`git rm -r --cached` both. Their `.gitkeep` files go too; that is safe, because
`_item_dirs` (`fs.py:1720`) uses `rglob`, which yields nothing for a missing
directory, and `_effect_transition` (`fs.py:2403`) recreates the status folder
before every move.

### 4. Scrub

Rewrite the four tracked hits with neutral equivalents. Two are prose in
`docs/plan/`; two are quoted repro material in backlog items, where the
placeholder names must stay internally consistent so the repro still reads.

### 5. Documentation

- `docs/changelogs/upcoming.md` — Fixed/Changed entry for the `git_mv` fix.
- `docs/release-notes/upcoming.md` — the user-facing "you can gitignore a
  resolved status folder" note.
- `skills/tcw-work/references/transitions.md` — one line under the
  auto-commit paragraph: an ignored destination is untracked rather than moved.
- README: no change. It documents the CLI surface, which is untouched.

## Acceptance criteria

1. `git check-ignore -q docs/work/completed docs/work/discarded` exits 0.
2. `git ls-files docs/work/completed docs/work/discarded` prints nothing.
3. `docs/work/completed/` and `docs/work/discarded/` still hold their folders on
   disk, and `tcw work list --all` still lists the resolved items.
4. A new test: in a `tmp_path` repo whose `.gitignore` holds `completed/`,
   `complete(slug, "done")` leaves the item at `completed/<slug>` on disk, with
   `git ls-files` showing nothing under `completed/`, `git status --porcelain`
   empty, and the commit count increased by one.
5. `tests/test_work_autocommit.py` passes unchanged — an unignored destination
   still gets a tracked rename.
6. `pytest` is green and `tcw validate` exits 0.
7. A case-insensitive grep for the private name over `git ls-files` output
   returns nothing.
8. `work/keep-resolved-work-out-of-git` reads `Supported`.

## Risks

- **The scoped commit turning out to be a no-op.** If both pathspecs were
  filtered out, the move would land with no commit and no error. Mitigated by
  criterion 4's commit-count assertion.
- **`git rm --cached` on a path with staged sibling edits.** `_effect_transition`
  reads the item before the move, and `complete` writes its state through
  `_stage` beforehand; those staged writes are inside `src` and are dropped from
  the index along with it — which is the intent, since the item is leaving the
  tracked tree.
- **Scrub collateral.** Renaming inside quoted repro text can make the repro
  incoherent. Read each hit in context rather than running a blind `sed`.
- **A future contributor re-adds the folders** with `git add -f`. Accepted; the
  ignore is the signal, not an enforcement mechanism.
