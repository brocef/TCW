# Worktree Merge-Back Rename Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tcw work complete` finishes a `--worktree` item whose branch added files inside a directory an earlier transition renamed on the primary checkout, while a genuine content conflict still fails closed.

**Architecture:** One change, in one function. `merge_worktree` (`tcw/store/fs.py:447-465`) passes `merge.directoryRenames=true` on the `git merge` invocation with `-c`, so the merge-back's behavior is decided by TCW rather than inherited from ambient Git configuration. Nothing else about the function — the branch-existence guard, the abort-on-failure, the error text, the `None`-on-success contract — changes.

**Tech Stack:** Python 3 with type hints, `subprocess`-backed Git, pytest over `tmp_path` git repos.

## Global Constraints

- `tests/test_recursion.py::test_complete_aborts_on_merge_conflict` must pass **byte-identical**. It is the only guard proving genuine conflicts still fail closed; editing it to accommodate the fix dissolves the guarantee.
- `-c` only. Never read, write, or migrate the user's Git configuration.
- `git merge` is the only invocation that gains an override. No other `git -C` call site in `tcw/` may acquire one.
- Do not reorder lifecycle transitions, rebase, or touch `add_worktree` / `remove_worktree` / `--already-integrated`.
- One capability delta: `changed: work/complete-a-work-item`. No new or removed capability, no taxonomy change.

---

## File Map

**Runtime**

- `tcw/store/fs.py` — `merge_worktree`: the invocation and its stale docstring premise.

**Tests**

- `tests/test_recursion.py` — the worktree section (§ Task 5), beside the existing merge-back tests.

**Documentation**

- `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`.
- `skills/tcw-work/references/transitions.md` (the `complete` section).
- `docs/capabilities/work/complete-a-work-item/description.md`.

---

### Task 1: Reproduce the stop as a failing test

**Files:**

- Test: `tests/test_recursion.py`

**Interfaces:**

- Consumes: `mk_node`, `commit_all`, `FsWorkStore`, and `tcw.cli.main`, all already in the file.
- Produces: no production change.

- [ ] **Step 1: Write the regression test**

Add to the `── Task 5: worktrees ──` section, after `test_complete_merges_worktree_branch_before_teardown`:

```python
def test_complete_merges_across_a_transition_rename(tmp_path, monkeypatch, capsys):
    """The gap the existing merge-back tests leave open.

    `submit` renames `active/<slug>/` → `review/<slug>/` on the primary checkout
    while the branch keeps committing under `active/<slug>/`. Git detects the
    directory rename and knows where the branch's new file belongs, but stops for
    confirmation — which TCW used to read as a failed merge.
    """
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug

    # An ADDED file inside the item folder, plus code outside it. The addition is
    # what triggers directory-rename confirmation; a modification would not, which
    # is why the existing tests miss this.
    (wt / "docs" / "work" / "active" / slug / "outcome.md").write_text("shipped\n")
    (wt / "feature.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "impl"], check=True)
    impl = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

    assert main(["work", "submit", slug]) == 0          # renames the dir on main
    capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    capsys.readouterr()

    item_root = root / "docs" / "work"
    assert (item_root / "completed" / slug / "outcome.md").read_text() == "shipped\n"
    assert not (item_root / "active" / slug).exists()
    assert not (item_root / "review" / slug).exists()
    assert subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                           impl, "HEAD"]).returncode == 0
    assert (root / "feature.py").read_text() == "x = 1\n"
    assert not wt.exists()
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches == ""
```

Covers acceptance criteria 1-4.

- [ ] **Step 2: Confirm it reproduces the reported stop**

```bash
python -m pytest -q tests/test_recursion.py::test_complete_merges_across_a_transition_rename
```

Expected: FAIL at the `complete` assertion with exit 1, and stderr containing
"merge of work/&lt;slug&gt; into the primary checkout failed". **If it fails for any
other reason, stop** — the test is not reproducing the defect and fixing the flag
would be fixing something else.

- [ ] **Step 3: Add the ambient-config test**

Covers criterion 6 — TCW's merge-back must not be steerable by repository config:

```python
def test_complete_merges_across_a_rename_despite_local_git_config(tmp_path, monkeypatch,
                                                                  capsys):
    root = mk_node(tmp_path, "repo")
    subprocess.run(["git", "-C", str(root), "config",
                    "merge.directoryRenames", "conflict"], check=True)
    ...  # same body as above, from commit_all(root) onwards
    value = subprocess.run(["git", "-C", str(root), "config", "--get",
                            "merge.directoryRenames"], capture_output=True, text=True)
    assert value.stdout.strip() == "conflict"           # TCW did not rewrite it
```

Factor the shared body into a module-level helper rather than duplicating it;
keep the two assertions blocks distinct.

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/test_recursion.py
git commit -m "test: pin the worktree merge-back across a transition rename"
```

Committing red is deliberate here: the reproduction is the evidence, and Task 2's
diff is two lines that would otherwise be unreviewable on their own.

---

### Task 2: Decide the merge's rename behavior at the invocation

**Files:**

- Modify: `tcw/store/fs.py:447-465`
- Test: `tests/test_recursion.py`

**Interfaces:**

- Preserves: `merge_worktree(node_root: Path, branch: str) -> str | None` — signature, `None` on success, error string on failure, quiet `None` when the branch is absent.

- [ ] **Step 1: Pass the setting per-invocation**

```python
    r = subprocess.run(["git", "-C", str(node_root),
                        "-c", "merge.directoryRenames=true",
                        "merge", "--no-edit", branch],
                       capture_output=True, text=True)
```

`-c` scopes it to this command: it neither reads nor writes the user's config, so
the merge-back behaves identically on every machine. `true` rather than `false` —
`false` disables rename detection entirely and would strand the branch's file at
the removed `active/<slug>/` path, resurrecting a directory the transition
deleted.

- [ ] **Step 2: Correct the stale docstring premise**

`fs.py:449-451` currently claims the ordering means "no rename/modify overlap".
That holds only for `complete`'s own rename. Replace with the true statement: the
merge runs before the `active→completed` rename, but may still meet a rename an
**earlier** transition (`submit`) left on the primary checkout, which is why the
rename setting is pinned rather than inherited. Covers criterion 9.

- [ ] **Step 3: Verify both directions**

```bash
python -m pytest -q tests/test_recursion.py
git diff tests/test_recursion.py::  # expect no diff to test_complete_aborts_on_merge_conflict
```

Expected: PASS, including `test_complete_aborts_on_merge_conflict`,
`test_complete_merges_worktree_branch_before_teardown`, and
`test_worktree_edit_merges_back_clean` — all unmodified. Covers criteria 5 and 7
(the branch-absent path is already covered by the existing recovery test).

- [ ] **Step 4: Confirm the override is the only one**

```bash
rg -n '"git", "-C"' tcw --glob '*.py'
rg -n '"-c",' tcw --glob '*.py'
```

Expected: exactly one `-c` occurrence, in `merge_worktree`. Covers criterion 8.

- [ ] **Step 5: Commit**

```bash
git add tcw/store/fs.py
git commit -m "fix: confirm directory renames during the worktree merge-back"
```

---

## Documentation Sync Block

Evaluated against `CLAUDE.md`'s Documentation Sync section. Four entries fire;
complete Tasks 3-6 only after Task 2's diff is settled and the suite is green,
then commit them together as one documentation pass.

### Task 3: Update `README.md`

**Files:**

- Modify: `README.md` (the `--worktree` paragraph under "Cross-node recursion", which currently reads "…and if the merge conflicts it stops with the branch and worktree left intact")

- [ ] Say that the merge-back completes even when a transition has moved the item's folder since the branch was created, and that only a genuine content conflict stops it.
- [ ] Do not promise atomicity or describe internal function names.
- [ ] Run `rg -n 'merges that branch back|merge conflicts' README.md` and `git diff --check`.

### Task 4: Update upcoming release notes

**Files:**

- Modify: `docs/release-notes/upcoming.md`

- [ ] Plain-language bug-fix entry: completing a worktree item no longer reports a merge failure when the item's folder moved during its lifecycle.
- [ ] **Also state the widened behavior**, per the spec's first risk: the merge-back now lets files added on the work branch follow *any* directory renamed on the main branch, code included — not only the lifecycle folder. This is a behavior change users should read, not only a fix.

### Task 5: Update the developer changelog

**Files:**

- Modify: `docs/changelogs/upcoming.md`

- [ ] `Fixed` entry naming `merge_worktree`, the inherited `merge.directoryRenames=conflict` default, the `-c` scoping, and the `submit`-then-`complete` trigger.
- [ ] Note the corrected docstring premise under `Internal` or in the same entry.

### Task 6: Update the driving skill and the capability, then commit the block

**Files:**

- Modify: `skills/tcw-work/references/transitions.md` (the `complete` section, the bullet at `:71-72`)
- Modify: `docs/capabilities/work/complete-a-work-item/description.md`
- Test: `tests/test_skill_lifecycle_parity.py`, `tests/test_documented_cli_surface.py`

- [ ] In `transitions.md`, refine "a merge conflict fails closed" to distinguish a genuine content conflict (still fails closed) from a folder that moved mid-lifecycle (now merged through). **Do not add lines to `skills/tcw-work/SKILL.md`** — its body is at the 60-line budget that `test_the_router_stays_within_its_line_budget` enforces, and this detail is conditional, so it belongs in the reference.
- [ ] In the capability description, extend the existing merge-back paragraph; preserve the id, status, subject, and any planning pointer.
- [ ] Run:

```bash
python -m pytest -q tests/test_skill_lifecycle_parity.py tests/test_documented_cli_surface.py
tcw capabilities check
tcw capabilities drift
git diff --check
```

- [ ] Commit the whole block:

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md \
  skills/tcw-work/references/transitions.md \
  docs/capabilities/work/complete-a-work-item/description.md
git commit -m "docs: explain the worktree merge-back across a rename"
```

---

### Task 7: Final verification and implementation evidence

**Files:**

- Create during the TCW implement stage: `outcome.md` in the item folder.

- [ ] **Step 1: Full suite**

```bash
python -m pytest -q
```

Expected: all pass; record exact counts.

- [ ] **Step 2: Frontend/static checks** — untouched by this change, but the gate is unconditional. A fresh linked worktree needs `pnpm install --frozen-lockfile` first.

```bash
pnpm exec tsc --noEmit && pnpm run lint && pnpm run test && pnpm run build && pnpm run check:build
```

- [ ] **Step 3: TCW validation**

```bash
tcw taxonomy check && tcw capabilities check && tcw validate
git diff --check && git status --short
```

Covers criterion 10.

- [ ] **Step 4: Write and commit `outcome.md` separately.** Record the exact reproduction output from Task 1 Step 2 alongside the passing result, since that pair is the whole evidence for this item. Do not submit, complete, or cut a version without the later lifecycle gates and explicit user authorization.

## Verification Beyond the Suite

- **The widened rename behavior is not provable by this item's tests.** They only exercise the lifecycle folder. Before closeout, manually confirm on a scratch fixture that a code directory renamed on the main branch also absorbs a branch-added file, so the release-note wording in Task 4 describes what actually happens rather than what was inferred.
- Confirm by inspection that `test_complete_aborts_on_merge_conflict` is untouched in the final diff — a passing test proves nothing if the fix edited it.
- Confirm the merge-back still produces an ordinary, inspectable merge commit (not a squash or fast-forward that hides the branch), since the spec's last risk accepts losing the confirmation prompt on the grounds that the merge stays reviewable.

## Notes

- Blocked on `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`: that item's branch has unmerged edits to `tcw/store/fs.py` (`_has_work_store` at ~172, `ensure_worktree_ignored` at ~432). Different regions from `merge_worktree`, so a conflict is unlikely, but sequencing behind it removes the question entirely. Recorded as a blocker, not prose, so `start` enforces it.
- This item is the reason that one needs a manual merge at closeout; the two are the same defect seen from opposite ends.
