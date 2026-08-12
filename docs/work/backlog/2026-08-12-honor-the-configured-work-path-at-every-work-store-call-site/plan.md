# Configured Work Path Call-Site Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every work-store reader, writer, and Git operation honor the configured `work.path`, including when the code node and work store belong to different repositories.

**Architecture:** `FsWorkStore.open(node_root)` remains the filesystem adapter's single authority for the configured store root, owning code node, and store Git root. Runtime callers use those resolved values instead of reconstructing `docs/work`; `start --worktree` persists store state and code-repository setup in separate scoped commits before creating the code worktree.

**Tech Stack:** Python 3 with type hints, `pathlib`, subprocess-backed Git operations, PyYAML, pytest `tmp_path` Git repositories, TCW's ABC plus filesystem-adapter pattern, Markdown/YAML lifecycle documents.

## Global Constraints

- Keep the owning code `node_root`, configured work `root`, and `store_git_root` distinct.
- Keep filesystem paths and Git operations out of the abstract `WorkStore` interface.
- Preserve project identity, qualified references, lifecycle-hook ownership, and code-worktree location.
- Preserve default `docs/work` behavior and `work.auto-commit-transitions` on and off.
- Do not move or merge an existing work store; do not change `--force` or `--take-over`.
- Scope every TCW-created commit to intended paths and preserve unrelated staged changes.
- A split-repository worktree start cannot be atomic: stop at the first failed commit, report durable partial progress, and never create the worktree after a persistence failure.
- No taxonomy delta is required; retain the five existing `changed:` capability paths.

---

## File Map

**Runtime**

- `tcw/store/fs.py`: work-store discovery and filesystem/Git ownership helpers.
- `tcw/work/recursion.py`: reconcile, delegate, escalate, and inbox writes.
- `tcw/capabilities/cli.py`: shipped-missing drift lookup.
- `tcw/work/cli.py`: split-repository `start --worktree` persistence.

**Tests**

- `tests/test_external_work_store.py`: configured discovery and split-repository fixtures.
- `tests/test_recursion.py`: external delegate, escalate, inbox failure, and reconcile.
- `tests/test_capabilities.py`: configuration-aware shipped-missing drift.
- `tests/test_work_autocommit.py`: worktree commit scoping, failure ordering, and default compatibility.

**Documentation**

- `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`.
- `skills/tcw-work/SKILL.md`, `skills/tcw-work/references/transitions.md`, `skills/tcw-capabilities/SKILL.md`.
- The five capability descriptions named by this item's `capabilities.yaml`.

---

### Task 1: Make configured-store discovery authoritative

**Files:**

- Modify: `tcw/store/fs.py:125-179`
- Test: `tests/test_external_work_store.py`

**Interfaces:**

- Consumes: `FsWorkStore.open(node_root: Path) -> FsWorkStore` and its `ValueError` contract.
- Produces: `_has_work_store(node_root: Path) -> bool`, true only when the active configured store opens.

- [ ] **Step 1: Write the failing decoy-default test**

Add imports for `shutil`, `_has_work_store`, and `child_nodes`, then add:

```python
def test_has_work_store_does_not_let_default_decoy_shadow_invalid_config(tmp_path):
    code = _repo(tmp_path / "code")
    store_repo = _repo(tmp_path / "store-repo")
    init(["work"], code, "corelib", work_path=store_repo / "work")
    (code / "docs" / "work").mkdir(parents=True)
    shutil.rmtree(store_repo / "work")

    assert _has_work_store(code) is False
```

Also add a registered-child case using a valid external store and assert `child_nodes(parent)` contains the child's code-node path.

- [ ] **Step 2: Run the tests and confirm the fast-path defect**

```bash
python -m pytest -q tests/test_external_work_store.py -k 'decoy or registered_node_discovery'
```

Expected: the decoy case fails because the literal directory returns `True`; valid external discovery remains supported.

- [ ] **Step 3: Replace the fast path with opened-store validation**

```python
def _has_work_store(node_root: Path) -> bool:
    try:
        FsWorkStore.open(node_root)
        return True
    except ValueError:
        return False
```

Catch only `ValueError`; unexpected filesystem and programming errors remain visible.

- [ ] **Step 4: Verify discovery behavior**

```bash
python -m pytest -q tests/test_external_work_store.py tests/test_recursion.py -k 'node or store'
git diff --check
```

Expected: PASS for default, valid external, invalid configured, and registered-node discovery cases.

- [ ] **Step 5: Commit**

```bash
git add tcw/store/fs.py tests/test_external_work_store.py
git commit -m "fix: validate configured work stores during discovery"
```

---

### Task 2: Route cross-node inbox writes through opened stores

**Files:**

- Modify: `tcw/work/recursion.py:215-251`
- Test: `tests/test_recursion.py`

**Interfaces:**

- Consumes: `FsWorkStore.open(target: Path)` and `FsWorkStore.root`.
- Produces: `_inbox_write(store: FsWorkStore, title: str, body: str, origin: str, initiative: str | None) -> Path`.
- Preserves: `delegate(node_root: Path, child_ref: str, title: str,
  body: str = "", initiative: str | None = None) -> Path` and
  `escalate(node_root: Path, title: str, body: str = "",
  initiative: str | None = None) -> Path`.

- [ ] **Step 1: Extend the recursion fixture for an external store**

Give `mk_node` an optional keyword-only `work_repo: Path | None = None`; compute `work_path = work_repo / name / "work"` when supplied and pass it to `init`. Keep the existing Git initialization and registry-wiring body unchanged.

- [ ] **Step 2: Write failing external inbox tests**

```python
def test_delegate_uses_child_configured_inbox(tmp_path):
    stores = mk_node(tmp_path, "stores")
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child", work_repo=stores)

    doc = delegate(parent, "child", "Do a thing")

    assert doc.parent == FsWorkStore.open(child).root / "inbox"
    assert not (child / "docs" / "work").exists()


def test_escalate_uses_parent_configured_inbox(tmp_path):
    stores = mk_node(tmp_path, "stores")
    parent = mk_node(tmp_path, "parent", work_repo=stores)
    child = mk_node(parent, "child")

    doc = escalate(child, "Coordinate it")

    assert doc.parent == FsWorkStore.open(parent).root / "inbox"
    assert not (parent / "docs" / "work").exists()
```

Add a direct `_inbox_write` test that deletes `store.root`, expects `ValueError("work store root does not exist")`, and asserts the root was not recreated.

- [ ] **Step 3: Run the new tests**

```bash
python -m pytest -q tests/test_recursion.py -k 'configured_inbox or missing_store_root'
```

Expected: configured inbox assertions point at phantom defaults, and the missing root is recreated.

- [ ] **Step 4: Pass the opened store into the bounded writer**

```python
def _inbox_write(store: FsWorkStore, title: str, body: str, origin: str,
                 initiative: str | None) -> Path:
    if not store.root.is_dir():
        raise ValueError(f"work store root does not exist: {store.root}")
    inbox = store.root / "inbox"
    inbox.mkdir(exist_ok=True)
    base = f"{date.today().isoformat()}-{slugify(title)}"
    name, n = base, 2
    while (inbox / f"{name}.md").exists():
        name, n = f"{base}-{n}", n + 1
    front = [f"from: {origin}"] + ([f"initiative: {initiative}"] if initiative else [])
    doc = inbox / f"{name}.md"
    doc.write_text("---\n" + "\n".join(front) + "\n---\n\n"
                   f"# {title}\n\n{body}\n", encoding="utf-8")
    return doc
```

Call it with `FsWorkStore.open(children[child_ref])` and `FsWorkStore.open(parent)`.

- [ ] **Step 5: Run the recursion suite**

```bash
python -m pytest -q tests/test_recursion.py
git diff --check
```

Expected: PASS, including collision naming, origin, initiative, and inbox-only boundary tests.

- [ ] **Step 6: Commit**

```bash
git add tcw/work/recursion.py tests/test_recursion.py
git commit -m "fix: route cross-node requests to configured inboxes"
```

---

### Task 3: Commit epic reconciliation in the store repository

**Files:**

- Modify: `tcw/work/recursion.py:170-212`
- Test: `tests/test_recursion.py`

**Interfaces:**

- Consumes: `FsWorkStore.store_git_root`, `FsWorkStore.root`, `git_stage`, and `git_commit`.
- Preserves: `reconcile(node_root: Path, epic_slug: str, commit: bool = False, complete_when_ready: bool = False) -> str`.

- [ ] **Step 1: Write the failing external reconcile test**

Use Task 2's fixture to put the parent work store in a separate repository. Create an epic and child task, commit both repositories, run `reconcile(parent, epic.slug, commit=True)`, then assert:

```python
content = epic_store.path(epic.slug) / "initial-request.md"
changed = subprocess.run(
    ["git", "-C", str(stores), "show", "--name-only", "--format="],
    capture_output=True, text=True, check=True,
).stdout
assert str(content.relative_to(stores)) in changed
assert porcelain(stores) == ""
assert porcelain(parent) == ""
assert not (parent / "docs" / "work").exists()
```

Run reconciliation again and assert the store repository's `rev-list --count HEAD` does not change.

- [ ] **Step 2: Confirm the code-node Git failure**

```bash
python -m pytest -q tests/test_recursion.py::test_reconcile_commits_external_rollup_in_store_repository
```

Expected: FAIL with `CalledProcessError` while staging the external path through the code repository.

- [ ] **Step 3: Route stage and commit through the epic store**

```python
if changed:
    content.write_text(text, encoding="utf-8")
    git_stage(store.store_git_root, content)
if commit and (changed or auto_completed):
    msg = f"auto-complete {epic_slug}" if auto_completed else f"reconcile {epic_slug}"
    work_pathspec = str(store.root.relative_to(store.store_git_root))
    git_commit(store.store_git_root, f"tcw work: {msg}", work_pathspec)
```

Preserve rendering, idempotence, and auto-completion/capability gates.

- [ ] **Step 4: Verify reconcile and epic behavior**

```bash
python -m pytest -q tests/test_recursion.py tests/test_epic_completable.py
git diff --check
```

Expected: PASS; unrelated staged paths stay outside the scoped commit.

- [ ] **Step 5: Commit**

```bash
git add tcw/work/recursion.py tests/test_recursion.py
git commit -m "fix: commit epic rollups in the work store repository"
```

---

### Task 4: Read shipped capability work from the configured store

**Files:**

- Modify: `tcw/capabilities/cli.py:199-220`
- Test: `tests/test_capabilities.py`

**Interfaces:**

- Consumes: `FsWorkStore.open(node: Path) -> FsWorkStore`.
- Preserves: `_shipped_but_missing(node, st) -> list[tuple[str, str]]`, with an empty list for no usable work component.

- [ ] **Step 1: Write the failing parameterized drift test**

Add a helper that initializes capabilities in the code node, initializes `work.path` inside a second Git repository, creates and completes a planning item, and points Missing `auth/login` at its slug. Then add:

```python
@pytest.mark.parametrize("with_decoy", [False, True])
def test_cli_drift_reads_completed_item_from_external_store(
        tmp_path, monkeypatch, capsys, with_decoy):
    root, slug = external_completed_planning_item(tmp_path)
    if with_decoy:
        (root / "docs" / "work").mkdir(parents=True)
    monkeypatch.chdir(root)

    assert main(["capabilities", "drift"]) == 1
    output = capsys.readouterr().out
    assert "shipped-missing" in output
    assert slug in output
```

- [ ] **Step 2: Confirm the no-decoy false negative**

```bash
python -m pytest -q tests/test_capabilities.py::test_cli_drift_reads_completed_item_from_external_store
```

Expected: no-decoy fails with `no capability drift`; decoy passes under the faulty guard.

- [ ] **Step 3: Replace the literal guard**

```python
def _shipped_but_missing(node, st) -> list[tuple[str, str]]:
    from tcw.store.fs import FsWorkStore
    try:
        work = FsWorkStore.open(node)
    except ValueError:
        return []
    out: list[tuple[str, str]] = []
```

Keep the existing capability loop and completed-only test unchanged. Catch only `ValueError`.

- [ ] **Step 4: Verify capability behavior**

```bash
python -m pytest -q tests/test_capabilities.py
tcw capabilities check
git diff --check
```

Expected: PASS for external/default stores, no-work nodes, active items, and discarded items.

- [ ] **Step 5: Commit**

```bash
git add tcw/capabilities/cli.py tests/test_capabilities.py
git commit -m "fix: detect capability drift through configured work stores"
```

---

### Task 5: Split `start --worktree` persistence by repository ownership

**Files:**

- Modify: `tcw/store/fs.py:431-435`
- Modify: `tcw/work/cli.py:500-570`
- Test: `tests/test_work_autocommit.py`
- Test: `tests/test_external_work_store.py`

**Interfaces:**

- Consumes: `FsWorkStore.root`, `store_git_root`, `node_root`, `git_commit_result`, and `add_worktree`.
- Produces: `ensure_worktree_ignored(node_root: Path) -> bool`, reporting whether `.gitignore` changed while retaining staging responsibility.

- [ ] **Step 1: Make ignore change detection explicit**

```python
def ensure_worktree_ignored(node_root: Path) -> bool:
    """Add and stage `.worktrees/`; return whether `.gitignore` changed."""
    changed = ensure_ignored(node_root, f"{WORKTREES_DIR}/")
    if changed:
        git_stage(node_root, node_root / ".gitignore")
    return changed
```

Add a test that calls it twice and asserts `True` then `False`.

- [ ] **Step 2: Verify the helper contract and callers**

```bash
python -m pytest -q tests/test_recursion.py -k ensure_worktree_ignored
rg -n 'ensure_worktree_ignored\(' tcw tests
```

Expected: helper test passes; the CLI is the only production caller.

- [ ] **Step 3: Write failing split-repository success tests**

For both `auto_commit=True` and `False`, create an external-store item, stage unrelated files in both repositories, run:

```python
assert main([
    "work", "start", item.slug, "--worktree", "--owner", "t@t",
]) == 0
active = FsWorkStore.open(code).get(item.slug)
assert active.worktree == f".worktrees/{item.slug}"
assert active.branch == f"work/{item.slug}"
assert "state.yaml" not in porcelain(store_repo)
assert "unrelated.txt" in porcelain(store_repo)
assert "unrelated.txt" in porcelain(code)
```

Also inspect each repository's last commit: the store commit contains the active item path; the code commit contains only `.gitignore` when it changed; the code worktree branch contains no external lifecycle path.

- [ ] **Step 4: Confirm staged external metadata is left behind**

```bash
python -m pytest -q tests/test_external_work_store.py -k worktree_start_commits_each_repository
```

Expected: FAIL because the current code commits hardcoded work paths through the code repository.

- [ ] **Step 5: Commit store-owned state before code-owned setup**

```python
node = st.node_root
ignore_changed = ensure_worktree_ignored(node)
st.set_field(bare, "worktree", f"{WORKTREES_DIR}/{bare}")
st.set_field(bare, "branch", f"work/{bare}")

store_pathspec = str(st.root.relative_to(st.store_git_root))
store_err = git_commit_result(
    st.store_git_root,
    f"tcw work: start {bare} (worktree metadata)",
    store_pathspec,
)
if store_err:
    print(
        f"tcw work start: {bare} is active, but committing worktree metadata "
        f"in {st.store_git_root} failed; no worktree was created:\n{store_err}",
        file=sys.stderr,
    )
    return 1

if ignore_changed:
    code_err = git_commit_result(
        node, f"tcw work: start {bare} (worktree ignore)", ".gitignore",
    )
    if code_err:
        print(
            f"tcw work start: {bare} metadata was committed in {st.store_git_root}, "
            f"but committing .gitignore in {node} failed; no worktree was created:\n"
            f"{code_err}",
            file=sys.stderr,
        )
        return 1
```

Call `add_worktree(node, bare)` only after both required commits succeed.

- [ ] **Step 6: Write failure-ordering tests**

Monkeypatch `tcw.work.cli.git_commit_result` to return `"store refused"` on the first call and assert exit 1, `"no worktree was created"`, and that a monkeypatched `add_worktree` is never called. In a second test return `None` then `"code refused"`; assert the error says metadata was committed and `add_worktree` is not called.

- [ ] **Step 7: Verify worktree and transition behavior**

```bash
python -m pytest -q tests/test_work_autocommit.py tests/test_external_work_store.py tests/test_recursion.py
git diff --check
```

Expected: PASS for default/external stores, auto-commit on/off, unrelated staged edits, both failure boundaries, and creation ordering.

- [ ] **Step 8: Commit**

```bash
git add tcw/store/fs.py tcw/work/cli.py \
  tests/test_work_autocommit.py tests/test_external_work_store.py tests/test_recursion.py
git commit -m "fix: persist worktree setup in owning repositories"
```

---

### Task 6: Close the runtime call-site class

**Files:**

- Inspect and modify if required: `tcw/**/*.py`
- Test: `tests/test_validate.py`
- Test: `tests/test_validate_target.py`

**Interfaces:**

- Consumes: opened-store routing established in Tasks 1-5.
- Produces: no active-store operation reconstructing `docs/work` or staging a resolved store path through `node_root`.

- [ ] **Step 1: Run deterministic scans**

```bash
rg -n 'docs/work|"docs"\s*/\s*"work"|git_stage|git_commit|git_commit_result' tcw --glob '*.py'
```

Retain only the default path in `FsWorkStore.open`, initialization/ignore defaults, malformed-node validation fallbacks, docstrings, and Git calls whose repository owns every supplied path.

- [ ] **Step 2: Test each additional live bypass before fixing it**

For every unclassified runtime match, add a two-repository regression beside its existing test family. Assert the resolved target and both repositories' porcelain status, then run the exact new test and record its failure.

- [ ] **Step 3: Route confirmed bypasses through opened-store values**

Use `FsWorkStore.open(node).root` for store paths and `store.store_git_root` for Git operations. Do not add an abstract-store method or rewrite intentional defaults.

- [ ] **Step 4: Run the integrated focused suite**

```bash
python -m pytest -q \
  tests/test_external_work_store.py tests/test_recursion.py \
  tests/test_capabilities.py tests/test_work_autocommit.py \
  tests/test_validate.py tests/test_validate_target.py
tcw taxonomy check
tcw capabilities check
tcw validate --no-recurse
git diff --check
```

Expected: all commands exit 0. If no additional live bypass exists, create no empty commit.

- [ ] **Step 5: Commit only actual audit repairs**

Stage the exact runtime and regression-test files changed in Steps 2-3, then:

```bash
git commit -m "fix: route remaining work store call sites through configuration"
```

Skip this step when the audit produces no diff.

---

## Documentation Sync Block

Complete Tasks 7-11 only after the runtime diff and focused suite are settled, then commit them together as one documentation pass.

### Task 7: Update `README.md`

**Files:**

- Modify: `README.md:199-207`
- Modify: `README.md:873-925`
- Test: `tests/test_documented_cli_surface.py`

- [ ] Explain that delegate/escalate, reconcile, drift lookup, transitions, and web edits follow `work.path`.
- [ ] Explain that store artifacts commit in the store repository, while `.gitignore`, code branches, and linked worktrees remain in the code repository.
- [ ] State that a code branch cannot contain lifecycle files owned by a different repository.
- [ ] Run:

```bash
python -m pytest -q tests/test_documented_cli_surface.py
rg -n 'work.path|delegate|escalate|reconcile|start .*--worktree' README.md
```

Expected: PASS and no wording that promises cross-repository lifecycle files on the code branch.

### Task 8: Update upcoming release notes

**Files:**

- Modify: `docs/release-notes/upcoming.md`

- [ ] Add a plain-language bug-fix entry: configured-store requests arrive, epic rollups commit, capability drift sees completed planning work, and worktree setup leaves intended state persisted.
- [ ] Avoid module/function names and cross-repository atomicity claims.
- [ ] Inspect with `sed -n '1,220p' docs/release-notes/upcoming.md` and run `git diff --check`.

### Task 9: Update the developer changelog

**Files:**

- Modify: `docs/changelogs/upcoming.md`

- [ ] Add a `Fixed` entry naming configuration-aware discovery, target-store inbox routing, `store_git_root` reconciliation, configured drift lookup, and split worktree commits.
- [ ] Inspect with `sed -n '1,240p' docs/changelogs/upcoming.md` and run `git diff --check`.

### Task 10: Update the driving skills

**Files:**

- Modify: `skills/tcw-work/SKILL.md`
- Modify: `skills/tcw-work/references/transitions.md`
- Modify: `skills/tcw-capabilities/SKILL.md`
- Test: `tests/test_skill_lifecycle_parity.py`
- Test: `tests/test_documented_cli_surface.py`

- [ ] Add the always-relevant configured-store rule tersely to `tcw-work/SKILL.md`.
- [ ] Put split-repository worktree and partial-failure recovery detail under `start` in `references/transitions.md`.
- [ ] State in `tcw-capabilities/SKILL.md` that drift resolves completed planning items through the configured work store and degrades only when no usable work component exists.
- [ ] Run:

```bash
python -m pytest -q tests/test_skill_lifecycle_parity.py tests/test_documented_cli_surface.py
git diff --check
```

Expected: PASS; the router remains thin and conditional detail is linked.

### Task 11: Reconcile the capability ledger and commit docs

**Files:**

- Modify: `docs/capabilities/work/configure-the-work-store-location/description.md`
- Modify: `docs/capabilities/work/manage-the-work-inbox/description.md`
- Modify: `docs/capabilities/work/start-a-work-item/description.md`
- Modify: `docs/capabilities/work/complete-a-work-item/description.md`
- Modify: `docs/capabilities/capabilities/detect-capability-drift/description.md`

- [ ] Update all five descriptions for the final configuration-aware behavior and unavoidable cross-repository worktree limitation.
- [ ] Preserve existing IDs, statuses, subjects, features, and planning pointers.
- [ ] Run:

```bash
tcw capabilities check
tcw capabilities drift
tcw validate --no-recurse
git diff --check
```

Expected: structural checks pass. If drift reports unrelated existing findings, record exact output and confirm none of the five paths became inconsistent.

- [ ] Commit the entire Documentation Sync block:

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md \
  skills/tcw-work/SKILL.md skills/tcw-work/references/transitions.md \
  skills/tcw-capabilities/SKILL.md \
  docs/capabilities/work/configure-the-work-store-location/description.md \
  docs/capabilities/work/manage-the-work-inbox/description.md \
  docs/capabilities/work/start-a-work-item/description.md \
  docs/capabilities/work/complete-a-work-item/description.md \
  docs/capabilities/capabilities/detect-capability-drift/description.md
git commit -m "docs: explain configured work store routing"
```

---

### Task 12: Final verification and implementation evidence

**Files:**

- Create during the TCW implement stage: `docs/work/active/2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site/outcome.md`

- [ ] **Step 1: Run the full Python suite**

```bash
python -m pytest -q
```

Expected: all tests pass; record exact passed/skipped counts.

- [ ] **Step 2: Run frontend/static checks**

```bash
pnpm exec tsc --noEmit
pnpm run lint
pnpm run test
pnpm run build
pnpm run check:build
```

Expected: all exit 0. Do not use a Prettier failure as authorization to format unrelated files.

- [ ] **Step 3: Run TCW validation**

```bash
tcw taxonomy check
tcw capabilities check
tcw validate
git diff --check
git status --short
```

Expected: all checks pass and status contains only intentional lifecycle evidence.

- [ ] **Step 4: Inspect a two-repository smoke fixture**

Run `git status --short` and `git show --stat --oneline HEAD` separately in the concrete store and code repositories. Confirm no phantom code-node `docs/work`, no staged work metadata, `.gitignore` only in the code repository, work state only in the store repository, and no unrelated file in either TCW commit.

- [ ] **Step 5: Repeat the semantic scan**

```bash
rg -n 'docs/work|"docs"\s*/\s*"work"|git_stage|git_commit|git_commit_result' tcw --glob '*.py'
```

Record every retained match's classification in `outcome.md`; tests cannot prove that a literal is only a default or validation fallback.

- [ ] **Step 6: Write and checkpoint `outcome.md`**

Run `tcw work lifecycle --stage implement`, write exact commands/results and checkpoint commit IDs, inspect the diff, and commit `outcome.md` separately. Do not submit, complete, publish, or cut a version without the later lifecycle gates and explicit user authorization.

## Verification Beyond the Suite

- The literal/Git-call scan requires semantic classification.
- Cross-repository worktree persistence is not atomic; review failure messages against the durable partial state.
- Manually confirm that docs never promise external lifecycle files appear on a code worktree branch.
- Inspect exact commit ownership and exclusion of unrelated staged files in both repositories.
