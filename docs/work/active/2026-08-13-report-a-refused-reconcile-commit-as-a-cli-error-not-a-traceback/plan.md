# Reconcile Commit Error Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A refused reconcile commit exits non-zero with a message naming the failure and quoting Git, instead of raising `subprocess.CalledProcessError` out of `main`.

**Architecture:** `reconcile` moves onto `git_commit_result`, the non-raising commit helper every other commit path in the codebase already uses, and converts its error string into a `ValueError` — already in `tcw/work/cli.py`'s `_ERRORS`, so the existing handler reports it. No new error type, no change to `_ERRORS`, no change to the deliberately-pinned `git_mv` raise-through.

**Tech Stack:** Python 3 with type hints, `subprocess`-backed Git, pytest over `tmp_path` git repos.

## Global Constraints

- `_ERRORS` (`tcw/work/cli.py:34`) stays byte-identical. Widening it would apply to all 16 `except _ERRORS` sites and silently swallow the `git_mv` raise-through that `tests/test_work_autocommit.py:311` exists to protect.
- `tests/test_work_autocommit.py::test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has` must pass unmodified.
- Never report a successful reconcile when the rollup was not committed.
- Preserve `reconcile`'s idempotent no-op, its auto-completion and capability gates, and its scoped pathspec.
- **No `capabilities.yaml`** — the spec established there is no capability to point at.

---

## File Map

**Runtime**

- `tcw/work/recursion.py` — `reconcile`'s commit call and the error it raises.

**Tests**

- `tests/test_recursion.py` — the reconcile section (`── Task 3: reconcile ──`).

**Documentation**

- `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`.

---

### Task 1: Build the refusing-hook fixture and reproduce

**Files:**

- Test: `tests/test_recursion.py`

**Interfaces:**

- Consumes: `mk_node`, `commit_all`, `FsWorkStore`, `reconcile`, `porcelain` — all already in the file.
- Produces: a `_refuse_commits(root: Path) -> None` helper.

- [ ] **Step 1: Write the hook helper**

The spec names this the sharp edge, so it gets its own helper with the assertion built in:

```python
def _refuse_commits(root: Path, message: str = "policy: no") -> None:
    """Install a pre-commit hook that rejects every commit in `root`.

    Written into the repository's own `.git/hooks/`, so it does not depend on
    `core.hooksPath` or on whatever `git init` templated in.
    """
    hooks = root / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho '{message}' >&2\nexit 1\n")
    hook.chmod(0o755)
```

- [ ] **Step 2: Assert the fixture actually bites**

Before relying on it, prove the hook fires — otherwise a later test could pass
because the commit failed for an unrelated reason:

```python
def test_refusing_hook_fixture_actually_blocks_a_commit(tmp_path):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    _refuse_commits(root)
    (root / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(root), "add", "f.txt"], check=True)
    r = subprocess.run(["git", "-C", str(root), "commit", "-m", "nope"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "policy: no" in r.stderr
```

A fixture this load-bearing is worth one test of its own; if `git init`
configuration ever makes hooks inert in CI, this fails first and names why.

- [ ] **Step 3: Write the failing CLI test**

```python
def test_cli_reconcile_reports_a_refused_commit(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("Redesign", created="2026-01-01")
    child = mk_node(parent, "child")
    _child_task(child, epic.slug)
    commit_all(child)
    commit_all(parent)
    _refuse_commits(parent)
    monkeypatch.chdir(parent)

    assert main(["work", "reconcile", epic.slug, "--commit"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("tcw work reconcile:")
    assert "policy: no" in err                     # git's own words reached the user
    assert "staged" in err                         # the rollup is in the index, not lost

    content = (FsWorkStore.open(parent).path(epic.slug) / "initial-request.md").read_text()
    assert "<!-- tcw:rollup -->" in content        # written...
    assert "initial-request.md" in porcelain(parent)   # ...and staged
```

Covers criteria 1-4.

- [ ] **Step 4: Confirm the reproduction**

```bash
python -m pytest -q tests/test_recursion.py -k 'refusing_hook or reports_a_refused_commit'
```

Expected: the fixture test PASSES; `test_cli_reconcile_reports_a_refused_commit`
FAILS with an uncaught `subprocess.CalledProcessError`. **If it fails any other
way, stop** — the reproduction is not the reported defect.

- [ ] **Step 5: Add the two guard tests**

```python
def test_reconcile_without_commit_ignores_a_refusing_hook(tmp_path, monkeypatch, capsys):
    ...  # same setup; assert main([... "reconcile", epic.slug]) == 0   (criterion 5)
```

and, for criterion 6, a test that removes the hook after a refused run, re-runs
`--commit` (expect 0 and one commit), then re-runs again unchanged and asserts
`rev-list --count HEAD` did not move.

- [ ] **Step 6: Commit the tests**

```bash
git add tests/test_recursion.py
git commit -m "test: pin reconcile's reporting of a refused commit"
```

---

### Task 2: Route the commit through the non-raising helper

**Files:**

- Modify: `tcw/work/recursion.py` (the import at `:178` and the commit at `:208-210`)
- Test: `tests/test_recursion.py`

**Interfaces:**

- Preserves: `reconcile(node_root, epic_slug, commit=False, complete_when_ready=False) -> str`.

- [ ] **Step 1: Swap the helper and raise the message**

Change the local import from `git_commit` to `git_commit_result`, then:

```python
    if commit and (changed or auto_completed):
        msg = f"auto-complete {epic_slug}" if auto_completed else f"reconcile {epic_slug}"
        work_pathspec = str(store.root.relative_to(store.store_git_root))
        err = git_commit_result(store.store_git_root, f"tcw work: {msg}", work_pathspec)
        if err:
            raise ValueError(
                f"reconciled {epic_slug} and staged the rollup, but committing it "
                f"failed:\n{err}")
```

`ValueError` is already in `_ERRORS`, so `_reconcile` reports it with the
`tcw work reconcile:` prefix and returns 1 — no CLI change needed.

The wording is load-bearing (spec criterion 3 and its second risk): the rollup
*was* written and staged at `recursion.py:205-206` before the commit was tried.
"reconciled … and staged the rollup, but committing it failed" tells the user the
change is in their index. Do not shorten this to "commit failed".

- [ ] **Step 2: Keep the `changed or auto_completed` guard**

It no longer prevents a crash — `git_commit_result` returns `None` for an empty
commit where `git_commit` raised — but it still avoids pointless work, and
criterion 6 pins the no-op. Leave it, and do not "simplify" it away.

- [ ] **Step 3: Verify both directions**

```bash
python -m pytest -q tests/test_recursion.py tests/test_epic_completable.py tests/test_work_autocommit.py
git diff HEAD -- tests/test_work_autocommit.py     # expect empty (criterion 8)
```

- [ ] **Step 4: Confirm the invariants the spec fixed on**

```bash
git diff HEAD -- tcw/work/cli.py          # expect empty (criterion 7: _ERRORS untouched)
rg -n 'git_commit\(' tcw --glob '*.py'    # expect the definition only (criterion 9)
```

- [ ] **Step 5: Commit**

```bash
git add tcw/work/recursion.py
git commit -m "fix: report a refused reconcile commit instead of raising"
```

---

## Documentation Sync Block

Evaluated against `CLAUDE.md`. Two entries fire; `README.md` does not (it documents
`reconcile --commit`'s purpose, not its failure mode, and gains nothing from this).
`skills/<component>/SKILL.md` does not: no CLI surface, model, lifecycle, or
guardrail changes — the command's contract is unchanged, only its manners. Record
that both were evaluated and skipped, so a reviewer sees a decision rather than an
omission.

### Task 3: Update the changelog and release notes, then commit

**Files:**

- Modify: `docs/changelogs/upcoming.md`
- Modify: `docs/release-notes/upcoming.md`

- [ ] Changelog `Fixed` entry: `reconcile` moves from `git_commit` to
  `git_commit_result` and raises `ValueError`; `_ERRORS` deliberately unchanged and
  why; the empty-commit behavior shifts from raise to quiet `None`.
- [ ] Changelog note that **`git_commit` now has no production caller** and is kept
  as a test helper (`tests/test_recursion.py:15`) — the spec's fourth risk is that
  someone later deletes it as dead code and breaks the suite.
- [ ] Release-note line, plain language: reconciling an epic now tells you when the
  commit was refused instead of showing an internal error, and says the rollup is
  staged so you know where it went.
- [ ] Run `git diff --check`, then:

```bash
git add docs/changelogs/upcoming.md docs/release-notes/upcoming.md
git commit -m "docs: note reconcile's commit error reporting"
```

---

### Task 4: Final verification and implementation evidence

**Files:**

- Create during the TCW implement stage: `outcome.md` in the item folder.

- [ ] **Step 1: Full suite** — `python -m pytest -q`; record exact counts.
- [ ] **Step 2: Frontend gate** — untouched by this change, but unconditional:
  `pnpm exec tsc --noEmit && pnpm run lint && pnpm run test && pnpm run build && pnpm run check:build`.
- [ ] **Step 3: TCW validation** — `tcw taxonomy check && tcw capabilities check && tcw validate`, then `git diff --check && git status --short`. Covers criterion 10.
- [ ] **Step 4: Write and commit `outcome.md` separately.** Record the Step 4 reproduction output beside the passing result. Do not submit, complete, or cut a version without the later lifecycle gates and explicit user authorization.

## Verification Beyond the Suite

- **Confirm the hook fixture is doing the work.** Temporarily revert Task 2 and check that `test_cli_reconcile_reports_a_refused_commit` fails with `CalledProcessError` specifically, not with an assertion about wording. A test that would pass against a different bug is not a regression test for this one.
- **Read the error message as a user would.** Criteria 2 and 3 can be satisfied by a string that technically contains "staged" while still reading as though nothing happened. Judge the rendered stderr, not the substring assertions.
- Confirm by inspection that `tcw/work/cli.py` is absent from the final diff — the whole design rests on not touching it.

## Notes

- Sequenced tests-before-fix because the reproduction *is* the evidence here: the defect is a missing `except`, and a fix committed without a red test first would be indistinguishable from a no-op.
- The ledger gap the spec recorded — no capability anywhere for `reconcile`, `delegate`, `escalate`, or epics — is not addressed by this plan and needs its own item.
