"""Cross-node recursion layer (work Spec 2): topology, epics, reconcile,
the inbox channel, and worktrees. pytest over nested tmp_path git repos."""

import subprocess
from pathlib import Path

import pytest

# Imports grow per task — start with Task 1's, add each task's symbols when you
# write that task's test (Task 3: reconcile; Task 4: delegate, escalate;
# Task 5: add_worktree, ensure_worktree_ignored, git_commit, remove_worktree).
from tcw.store.fs import (
    FsWorkStore, add_worktree, child_nodes, ensure_worktree_ignored, git_commit,
    init, parent_node, remove_worktree,
)
from tcw.work.recursion import delegate, escalate, reconcile


def mk_node(base: Path, name: str) -> Path:
    """A git repo with docs/work/ initialized, at base/name."""
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def commit_all(root: Path, msg: str = "init") -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", msg], check=True)


# ── Task 1: topology ─────────────────────────────────────────────────────────

def test_child_nodes_finds_children_excludes_own_worktree_keeps_nested_repo(tmp_path):
    parent = mk_node(tmp_path, "parent")
    subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)   # commit parent's
    subprocess.run(["git", "-C", str(parent), "commit", "-qm", "init"], check=True)  # OWN files
    child = mk_node(parent, "child")                       # direct child node
    deep = mk_node(parent / "group", "deep")              # under a non-node folder
    plain_repo = parent / "lib"                            # a git repo WITHOUT docs/work
    plain_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(plain_repo)], check=True)
    # NB: never `git add -A` the parent now — it holds uncommitted nested repos
    # (child/deep/lib) and git would abort ("does not have a commit checked out").
    subprocess.run(["git", "-C", str(parent), "worktree", "add", "-q",
                    "-b", "work/x", str(parent / ".worktrees" / "x")], check=True)

    found = {p.resolve() for p in child_nodes(parent)}
    assert child.resolve() in found
    assert deep.resolve() in found                         # skips intermediate non-node folder
    assert (parent / ".worktrees" / "x").resolve() not in found   # own worktree excluded
    assert plain_repo.resolve() not in found               # repo without docs/work is not a node


def test_parent_node(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    assert parent_node(child).resolve() == parent.resolve()
    assert parent_node(parent) is None                     # root has no parent node


# ── Task 2: epic / initiative fields ─────────────────────────────────────────

def test_new_epic_and_initiative_fields(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    monkeypatch.chdir(root)
    from tcw.cli import main
    assert main(["work", "new", "Build it", "--epic", "--initiative", "2026-01-01-epic"]) == 0
    slug = capsys.readouterr().out.strip()
    item = FsWorkStore.open(root).get(slug)
    assert item.type == "epic"
    assert item.initiative == "2026-01-01-epic"
    assert main(["work", "show", slug]) == 0
    out = capsys.readouterr().out
    assert "type: epic" in out
    assert "initiative: 2026-01-01-epic" in out


def test_edit_sets_and_clears_initiative(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path, "repo"))
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "initiative", "2026-01-01-epic")
    assert st.get(item.slug).initiative == "2026-01-01-epic"
    st.set_field(item.slug, "initiative", "")
    assert st.get(item.slug).initiative == ""


def test_initiative_child_cannot_start_before_epic_active(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    epic_store = FsWorkStore.open(parent)
    epic = epic_store.create("Epic", created="2026-01-01")
    epic_store.set_field(epic.slug, "type", "epic")
    task_store = FsWorkStore.open(child)
    task = task_store.create("Slice", created="2026-01-02")
    task_store.set_field(task.slug, "initiative", epic.slug)

    with pytest.raises(ValueError, match=f"Cannot start work item {task.slug} before epic {epic.slug} is active"):
        task_store.start(task.slug)

    epic_store.start(epic.slug)
    assert task_store.start(task.slug).status == "active"


def test_epic_cannot_complete_with_open_initiative_children(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    epic_store = FsWorkStore.open(parent)
    epic = epic_store.create("Epic", created="2026-01-01")
    epic_store.set_field(epic.slug, "type", "epic")
    epic_store.start(epic.slug)
    task_store = FsWorkStore.open(child)
    task = task_store.create("Slice", created="2026-01-02")
    task_store.set_field(task.slug, "initiative", epic.slug)
    task_store.start(task.slug)

    with pytest.raises(ValueError, match=f"Cannot complete epic {epic.slug}; initiative children are still open: {task.slug}"):
        epic_store.complete(epic.slug, "done", [])

    task_store.complete(task.slug, "done", [])
    assert epic_store.complete(epic.slug, "done", []).status == "completed"


# ── Task 3: reconcile ────────────────────────────────────────────────────────

def _child_task(child, initiative, title="Slice", caps=None):
    s = FsWorkStore.open(child)
    t = s.create(title, created="2026-01-01")
    s.set_field(t.slug, "initiative", initiative)
    if caps is not None:
        (s.path(t.slug) / "capabilities.yaml").write_text(caps, encoding="utf-8")
    return t.slug


def test_reconcile_rollup_keys_by_node_and_is_idempotent(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("Redesign", created="2026-01-01")
    a, b = mk_node(parent, "child-a"), mk_node(parent, "child-b")
    _child_task(a, epic.slug)
    _child_task(b, epic.slug)                              # same slug as child-a's task
    block = reconcile(parent, epic.slug)
    assert "child-a" in block and "child-b" in block
    # both colliding slugs appear, disambiguated by node in the table rows
    # (assert rows, not a raw count — the slug also recurs in the **Next:** line)
    assert "| child-a | 2026-01-01-slice |" in block
    assert "| child-b | 2026-01-01-slice |" in block
    assert reconcile(parent, epic.slug) == block          # idempotent
    content = (FsWorkStore.open(parent).path(epic.slug) / "content.md").read_text()
    assert content.count("<!-- tcw:rollup -->") == 1      # no duplicate block


def test_reconcile_unknown_epic_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    with pytest.raises(ValueError):
        reconcile(parent, "2026-01-01-nope")


def test_reconcile_surfaces_capability_deltas(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug,
                caps="- file: routes/login\n  heading: sso\n  from: Missing\n  to: Supported\n")
    block = reconcile(parent, epic.slug)
    assert "routes/login#sso" in block
    assert "Missing" in block and "Supported" in block


def test_reconcile_tolerates_malformed_capabilities(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug, caps="just: a-mapping\n")   # not a list
    block = reconcile(parent, epic.slug)                   # must not raise
    assert "skipped" in block.lower()


# ── Task 4: inbox channel ────────────────────────────────────────────────────

def _no_items(node: Path) -> bool:
    work = node / "docs" / "work"
    return all(not [d for d in (work / s).iterdir() if d.is_dir()]
               for s in ("backlog", "active", "completed"))


def test_delegate_writes_child_inbox_only(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    doc = delegate(parent, "child", "Do a thing", body="details", initiative="2026-01-01-epic")
    assert doc.parent == (child / "docs" / "work" / "inbox")
    text = doc.read_text()
    assert "from: ." in text and "initiative: 2026-01-01-epic" in text and "details" in text
    assert _no_items(child)                                # boundary: never touches backlog/active/completed


def test_delegate_unknown_child_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    mk_node(parent, "child")
    with pytest.raises(ValueError):
        delegate(parent, "nope", "x")


def test_delegate_filename_collision_suffix(tmp_path):
    parent = mk_node(tmp_path, "parent")
    mk_node(parent, "child")
    d1 = delegate(parent, "child", "Same title")
    d2 = delegate(parent, "child", "Same title")
    assert d1 != d2


def test_escalate_writes_parent_inbox_and_root_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    doc = escalate(child, "Cross-repo scope")
    assert doc.parent == (parent / "docs" / "work" / "inbox")
    assert "from: child" in doc.read_text()
    with pytest.raises(ValueError):
        escalate(parent, "x")                              # parent is the root


# ── Task 5: worktrees ────────────────────────────────────────────────────────

def test_start_worktree_places_item_in_worktree(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Build it"]); slug = capsys.readouterr().out.strip()
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()
    wt = root / ".worktrees" / slug
    assert (wt / "docs" / "work" / "active" / slug / "state.yaml").is_file()  # item IS in the worktree
    item = FsWorkStore.open(root).get(slug)
    assert item.status == "active" and item.branch == f"work/{slug}"
    assert ".worktrees/" in (root / ".gitignore").read_text()


def test_worktree_edit_merges_back_clean(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Feature"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug
    monkeypatch.chdir(wt)                                  # work on the branch
    main(["work", "edit", slug, "--blocked-by", "external: upstream"])
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-am", "edit"], check=True)
    subprocess.run(["git", "-C", str(root), "merge", "-q", "--no-edit", f"work/{slug}"],
                   check=True)                             # clean merge — single-owner invariant
    item = FsWorkStore.open(root).get(slug)
    assert any("upstream" in b.get("external", "") for b in item.blocked_by)


def test_complete_tears_down_worktree(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert not (root / ".worktrees" / slug).exists()
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches == ""
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_merges_worktree_branch_before_teardown(tmp_path, monkeypatch, capsys):
    """Regression: complete must merge the work branch into the primary checkout
    before deleting it — committed worktree work must land on the integration
    branch, not become a dangling object (the data-loss bug)."""
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug
    # implementation commit I on work/<slug>: modify the tracked item doc AND add code
    (wt / "docs" / "work" / "active" / slug / "content.md").write_text("worktree edit\n")
    (wt / "feature.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "impl"], check=True)
    impl = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0

    # the implementation commit is reachable on the primary branch
    assert subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                           impl, "HEAD"]).returncode == 0
    assert (root / "feature.py").read_text() == "x = 1\n"          # code integrated
    assert not wt.exists()                                          # worktree torn down
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches == ""                                          # branch deleted (post-merge)
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_aborts_on_merge_conflict(tmp_path, monkeypatch, capsys):
    """Fail closed: an unmergeable work branch must leave branch + worktree
    intact, keep the item active, and not report completion."""
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug
    item_doc = ["docs", "work", "active", slug, "content.md"]
    # diverging edits to the SAME tracked file → conflicting merge
    (wt.joinpath(*item_doc)).write_text("worktree side\n")
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-am", "wt"], check=True)
    (root.joinpath(*item_doc)).write_text("main side\n")
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-am", "main"], check=True)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "merge" in err and slug in err
    # everything intact for manual resolution
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches != ""
    assert wt.exists()
    assert FsWorkStore.open(root).get(slug).status == "active"
    assert not (root / ".git" / "MERGE_HEAD").exists()            # half-merge aborted
