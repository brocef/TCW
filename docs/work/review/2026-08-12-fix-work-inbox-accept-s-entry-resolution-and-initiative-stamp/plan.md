# Fix Work Inbox Accept Entry Resolution and Initiative Stamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every identifier printed by `work inbox list` usable by show/accept and preserve delegated initiative metadata.

**Architecture:** Keep identifier flexibility private to `FsWorkStore`, where filesystem references are realized, and route both read and consume operations through one deterministic resolver. Parse only the closed `initiative` frontmatter field into abstract work-item state.

**Tech Stack:** Python 3.11+, PyYAML, pathlib, pytest, Git-backed `FsWorkStore` fixtures.

---

### Task 1: Specify relaxed inbox entry resolution with failing tests

**Files:**
- Modify: `tests/test_work.py:119-220`

- [ ] **Step 1: Add store tests for bare Markdown title resolution**

Add `test_inbox_show_and_accept_resolve_listed_file_title` that writes `inbox/example.md`, asserts `inbox_list()` exposes `ref="example.md", title="example"`, calls `inbox_show("example")`, then accepts a fresh equivalent entry by `"example"` and asserts the resulting slug and source removal.

- [ ] **Step 2: Add collision tests**

Create both `inbox/example.md` and `inbox/example/INDEX.md`; assert `inbox_accept("example")` raises `ValueError` containing `ambiguous inbox entry`, neither source is consumed, and exact `example.md` remains accepted.

- [ ] **Step 3: Run the focused tests and confirm the red state**

Run: `pytest tests/test_work.py -k 'inbox and (listed_file_title or collision)' -v`

Expected: FAIL because `_inbox_path("example")` does not resolve the Markdown file and does not diagnose title collisions.

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/test_work.py
git commit -m "test: define inbox entry alias resolution"
```

### Task 2: Add one deterministic adapter resolver

**Files:**
- Modify: `tcw/store/fs.py:2680-2735`
- Test: `tests/test_work.py`

- [ ] **Step 1: Implement `_resolve_inbox_ref`**

Add a private method returning the canonical `InboxEntry.ref`. Probe the exact safe path first, then `<ref>.md` for extensionless input, then collect `inbox_list()` entries whose `title == ref`. Deduplicate candidates, return one, and raise `ValueError` with sorted refs for multiple candidates.

- [ ] **Step 2: Route both operations through the resolver**

Have `inbox_show` resolve before `_inbox_detail`; in `inbox_accept`, resolve once and use that canonical ref for both `_inbox_path` and `_inbox_detail`. Do not change the abstract `WorkStore` signatures.

- [ ] **Step 3: Run the inbox suite**

Run: `pytest tests/test_work.py -k inbox -v`

Expected: PASS, including exact file, folder, binary, traversal, alias, and collision cases.

- [ ] **Step 4: Commit the resolver**

```bash
git add tcw/store/fs.py tests/test_work.py
git commit -m "fix: resolve listed inbox entry identifiers"
```

### Task 3: Preserve delegated initiative frontmatter

**Files:**
- Modify: `tests/test_work.py:119-220`
- Modify: `tcw/store/fs.py:2737-2825`

- [ ] **Step 1: Write initiative acceptance tests**

Add cases for `initiative: epic-one`, absent/blank initiative, and `initiative: [bad]`. Assert the first appears on `st.get(item.slug).initiative`, blank stays empty, and structured input raises before item creation or source removal.

- [ ] **Step 2: Verify the initiative test fails**

Run: `pytest tests/test_work.py -k 'inbox_accept and initiative' -v`

Expected: FAIL because acceptance currently writes only slug/title/created/resolution.

- [ ] **Step 3: Extract and validate frontmatter metadata**

Reuse the repository's YAML/frontmatter helper if available; otherwise add a focused private parser beside inbox ingestion. Accept only a scalar initiative, strip whitespace, and pass the value into the state assembled atomically in the temporary item directory.

- [ ] **Step 4: Run work and recursion tests**

Run: `pytest tests/test_work.py tests/test_recursion.py -q`

Expected: PASS.

- [ ] **Step 5: Commit initiative propagation**

```bash
git add tcw/store/fs.py tests/test_work.py
git commit -m "fix: preserve delegated inbox initiatives"
```

### Task 3b: Correct `delegate`'s argument help (folded in 2026-08-13)

**Files:**
- Modify: `tests/test_recursion.py`
- Modify: `tcw/work/cli.py` (the `pdg.add_argument("child", …)` help string)

- [ ] **Step 1: Write the failing test**

The fixture must break the coincidence `mk_node` creates, or it proves nothing — `mk_node` derives the project ID from the directory name, so ID and directory always match and the defect is invisible. Build a child whose directory name and project ID differ, then assert both directions:

```python
def test_delegate_resolves_the_project_id_not_the_directory_name(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "sub-dir-name")
    # Re-id the child, and re-register it under that id, so the directory name
    # and the canonical project id genuinely differ.
    ...
    with pytest.raises(ValueError, match="no child node 'sub-dir-name'"):
        delegate(parent, "sub-dir-name", "by directory name")
    doc = delegate(parent, "canonical-id", "by project id")
    assert doc.parent == FsWorkStore.open(child).root / "inbox"
```

Run it and confirm it fails only on the *help string* assertion below — the behavioral half should already pass, because the code is correct.

- [ ] **Step 2: Assert the documented form**

```python
def test_delegate_help_names_the_project_id(capsys):
    ...  # parse `tcw work delegate --help`; assert "project id" appears and "path" does not
```

Expected: FAIL — the current text reads `child node path (relative to this node)`.

- [ ] **Step 3: Fix the help string**

Name the canonical project ID and point at `tcw work nodes` as the way to list valid values. Do **not** change `delegate`'s resolution logic: IDs are identity, paths are adapter locators, and accepting a path here would be the actual defect.

- [ ] **Step 4: Commit**

```bash
git add tcw/work/cli.py tests/test_recursion.py
git commit -m "fix: name the project id in delegate's argument help"
```

### Task 4: Documentation Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`
- Modify: `skills/tcw-work/SKILL.md` or `skills/tcw-work/references/commands.md`

- [ ] **Step 1: Update public usage guidance**

Document that `inbox accept` accepts either the listed filename/ref or bare listed title and that delegated initiatives survive acceptance. Also correct any prose that describes `delegate`'s argument as a path — `README.md` and `skills/tcw-work/references/commands.md` both mention the command; check each rather than assuming.

- [ ] **Step 2: Add user and developer notes**

Add plain-language release notes and a technical Fixed changelog entry covering resolution ordering, ambiguity behavior, and initiative propagation.

- [ ] **Step 3: Update the driving skill**

Keep the thin router concise; put exact accepted forms in `references/commands.md` if the detail is conditional.

- [ ] **Step 4: Commit documentation together**

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md skills/tcw-work
git commit -m "docs: describe reliable inbox acceptance"
```

### Task 5: Final verification

- [ ] **Step 1: Run the complete suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 2: Validate TCW data**

Run: `python -c 'from tcw.cli import main; raise SystemExit(main(["validate"]))'`

Expected: exit 0 with no new work-document problems.

- [ ] **Step 3: Inspect scope**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intended implementation-stage files are present.

## Verification

No manual-only behavior remains. Automated tests cover resolution precedence, ambiguity, metadata validation, atomic failure, cross-node initiative round-trip, and (folded in) `delegate`'s identifier form in both behavior and help text.

The one judgment a test cannot make: whether the corrected help string actually reads as "canonical project id" to someone who has not just read the source. Read the rendered `--help` output, not the diff.
