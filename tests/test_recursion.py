"""Cross-node recursion layer (work Spec 2): topology, epics, reconcile,
the inbox channel, and worktrees. pytest over nested tmp_path git repos."""

import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

# Imports grow per task — start with Task 1's, add each task's symbols when you
# write that task's test (Task 3: reconcile; Task 4: delegate, escalate;
# Task 5: add_worktree, ensure_worktree_ignored, git_commit, remove_worktree).
from tcw.store.fs import (
    FsWorkStore, add_worktree, child_nodes, ensure_worktree_ignored, git_commit,
    init, merge_worktree, parent_node, remove_worktree,
)
from tcw.work.recursion import _inbox_write, delegate, escalate, reconcile


def mk_node(base: Path, name: str, *, work_repo: Path | None = None) -> Path:
    """A git repo with docs/work/ initialized, at base/name.

    With `work_repo`, the node's work store is configured into that *other* git
    repository instead (`<work_repo>/<name>/work`) — the split-repository layout.
    """
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower(),
         work_path=None if work_repo is None else work_repo / name / "work")
    search = root.parent
    while search != search.parent and not (search / "tcw-config.yaml").is_file():
        search = search.parent
    if (search / "tcw-config.yaml").is_file():
        parent_cfg = yaml.safe_load((search / "tcw-config.yaml").read_text()) or {}
        parent_id = parent_cfg["id"]
        child_id = name.lower()
        parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
            child_id
        ] = str(root.resolve())
        (search / "tcw-config.yaml").write_text(
            yaml.safe_dump(parent_cfg, sort_keys=False)
        )
        child_cfg = yaml.safe_load((root / "tcw-config.yaml").read_text()) or {}
        child_cfg["connected-projects"] = {
            "parent": {parent_id: str(search.resolve())}
        }
        (root / "tcw-config.yaml").write_text(
            yaml.safe_dump(child_cfg, sort_keys=False)
        )
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


def test_child_nodes_prunes_node_modules_and_dotdirs(tmp_path, monkeypatch):
    # Regression: child_nodes walked the whole tree spawning git_root() per dir,
    # hanging on node_modules. It must skip node_modules and dot-dirs entirely.
    import tcw.store.fs as fs
    parent = mk_node(tmp_path, "parent")
    subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)
    subprocess.run(["git", "-C", str(parent), "commit", "-qm", "init"], check=True)
    real = mk_node(parent, "child")                        # genuine child node
    buried = parent / "node_modules" / "pkg" / "buried"
    hidden = parent / ".cache" / "hidden"
    for path, project_id in ((buried, "buried"), (hidden, "hidden")):
        path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        init(["work"], path, project_id)                   # valid but unregistered

    seen = []
    orig = fs.git_root
    monkeypatch.setattr(fs, "git_root", lambda p: (seen.append(str(p)), orig(p))[1])

    found = {str(p.resolve()) for p in fs.child_nodes(parent)}
    assert str(real.resolve()) in found
    assert not any("node_modules" in p or "/.cache" in p for p in found)  # pruned
    assert not any("node_modules" in p for p in seen)      # no git spawn under node_modules


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


def test_cli_initiative_child_start_gate_prints_error(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    epic_store = FsWorkStore.open(parent)
    epic = epic_store.create("Epic", created="2026-01-01")
    epic_store.set_field(epic.slug, "type", "epic")
    task_store = FsWorkStore.open(child)
    task = task_store.create("Slice", created="2026-01-02")
    task_store.set_field(task.slug, "initiative", epic.slug)

    monkeypatch.chdir(child)
    assert main(["work", "start", task.slug]) == 1
    err = capsys.readouterr().err
    assert f"Cannot start work item {task.slug} before epic {epic.slug} is active" in err


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


def test_cli_epic_complete_gate_prints_error(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
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

    monkeypatch.chdir(parent)
    assert main(["work", "complete", epic.slug, "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert f"Cannot complete epic {epic.slug}; initiative children are still open: {task.slug}" in err


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
    content = FsWorkStore.open(parent).read_sidecar(epic.slug, "rollup.md").content
    assert content.count("<!-- tcw:rollup -->") == 1      # no duplicate block


def porcelain(root: Path) -> str:
    return subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                          capture_output=True, text=True, check=True).stdout


def _commits(root: Path) -> int:
    return int(subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                              capture_output=True, text=True, check=True).stdout)


def test_reconcile_commits_external_rollup_in_store_repository(tmp_path):
    stores = mk_node(tmp_path, "stores")
    parent = mk_node(tmp_path, "parent", work_repo=stores)
    child = mk_node(parent, "child")
    epic_store = FsWorkStore.open(parent)
    epic = epic_store.create("Redesign", created="2026-01-01")
    _child_task(child, epic.slug)
    commit_all(child)
    commit_all(stores)
    (stores / "unrelated.txt").write_text("keep me staged\n")
    subprocess.run(["git", "-C", str(stores), "add", "unrelated.txt"], check=True)

    reconcile(parent, epic.slug, commit=True)

    content = epic_store.path(epic.slug) / "rollup.md"
    changed = subprocess.run(
        ["git", "-C", str(stores), "show", "--name-only", "--format="],
        capture_output=True, text=True, check=True,
    ).stdout
    assert str(content.relative_to(stores)) in changed
    assert "unrelated.txt" not in changed                  # scoped to the work store
    assert porcelain(stores) == "A  unrelated.txt\n"       # and left staged
    assert not (parent / "docs" / "work").exists()

    before = _commits(stores)
    reconcile(parent, epic.slug, commit=True)              # unchanged rollup: no-op
    assert _commits(stores) == before


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


def test_refusing_hook_fixture_actually_blocks_a_commit(tmp_path):
    """The fixture below is load-bearing, so it gets its own test. If hook
    execution ever goes inert in CI, this fails first and names why — rather
    than the reconcile tests passing because the commit failed for some
    unrelated reason."""
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    _refuse_commits(root)
    (root / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(root), "add", "f.txt"], check=True)

    r = subprocess.run(["git", "-C", str(root), "commit", "-m", "nope"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "policy: no" in r.stderr


def _epic_with_a_slice(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("Redesign", created="2026-01-01")
    child = mk_node(parent, "child")
    _child_task(child, epic.slug)
    commit_all(child)
    commit_all(parent)
    return parent, epic.slug


def test_cli_reconcile_reports_a_refused_commit(tmp_path, monkeypatch, capsys):
    """`git_commit` raises `CalledProcessError`, which is not in `_ERRORS`, so a
    refused commit escaped `main` as a traceback through TCW internals."""
    from tcw.cli import main
    parent, epic = _epic_with_a_slice(tmp_path)
    _refuse_commits(parent)
    monkeypatch.chdir(parent)

    assert main(["work", "reconcile", epic, "--commit"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("tcw work reconcile:")
    assert "policy: no" in err                     # git's own words reached the user
    assert "staged" in err                         # the rollup is in the index, not lost

    content = FsWorkStore.open(parent).read_sidecar(epic, "rollup.md").content
    assert "<!-- tcw:rollup -->" in content        # written...
    assert "rollup.md" in porcelain(parent)             # ...and staged


def test_reconcile_without_commit_ignores_a_refusing_hook(tmp_path, monkeypatch, capsys):
    """Only `--commit` touches git, so a refusing hook is irrelevant without it."""
    from tcw.cli import main
    parent, epic = _epic_with_a_slice(tmp_path)
    _refuse_commits(parent)
    monkeypatch.chdir(parent)

    assert main(["work", "reconcile", epic]) == 0


def test_reconcile_commit_recovers_once_the_hook_is_removed(tmp_path, monkeypatch, capsys):
    """The rollup was staged, not lost, so the retry is just re-running it — and
    a second unchanged run stays a no-op rather than making an empty commit."""
    from tcw.cli import main
    parent, epic = _epic_with_a_slice(tmp_path)
    _refuse_commits(parent)
    monkeypatch.chdir(parent)
    assert main(["work", "reconcile", epic, "--commit"]) == 1
    capsys.readouterr()

    (parent / ".git" / "hooks" / "pre-commit").unlink()
    before = _commits(parent)
    assert main(["work", "reconcile", epic, "--commit"]) == 0
    assert _commits(parent) == before + 1
    assert main(["work", "reconcile", epic, "--commit"]) == 0
    assert _commits(parent) == before + 1          # unchanged rollup: still a no-op


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


def test_reconcile_surfaces_canonical_capability_deltas(tmp_path):
    """The rollup reads the same schema the gate does.

    The defect this pins: a sidecar written per the documented canonical shape —
    which `capabilities check` and the `complete` gate both accept — used to be
    reported as "present but not a list", i.e. malformed when it was correct.
    """
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug, caps="new:\n  - a/b\nchanged:\n  - c/d\n")
    block = reconcile(parent, epic.slug)
    assert "a/b" in block and "c/d" in block
    assert "skipped" not in block.lower()


def test_reconcile_honors_added_alias(tmp_path):
    """`added:` is a deprecated alias of `new:` in declared_capabilities, so the
    rollup inherits it for free — which is the point of sharing one reader."""
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug, caps="added:\n  - a/b\n")
    block = reconcile(parent, epic.slug)
    assert "new a/b" in block
    assert "skipped" not in block.lower()


def test_reconcile_tolerates_unreadable_capabilities(tmp_path):
    """One child node's broken sidecar must not take down an epic-wide rollup.

    The gate wants SidecarError to propagate and fail closed; this is a display
    surface, so it degrades to a row instead.
    """
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug, caps="new:\n  - [unclosed\n")   # invalid YAML
    block = reconcile(parent, epic.slug)                      # must not raise
    assert "unreadable" in block.lower() and "skipped" in block.lower()


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
    assert "from: parent" in text
    assert "initiative: 2026-01-01-epic" in text
    assert "details" in text
    assert _no_items(child)                                # boundary: never touches backlog/active/completed


def test_delegate_resolves_the_project_id_not_the_directory_name(tmp_path):
    """`delegate` matches the canonical project ID, never a filesystem path.

    Deliberately breaks the coincidence `mk_node` creates — it derives the
    project ID from the directory name, so ID and directory always match and
    this distinction is invisible to every other test in this file.
    """
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "sub-dir-name")
    for root, cfg in ((parent, "parent"), (child, "sub-dir-name")):
        c = yaml.safe_load((root / "tcw-config.yaml").read_text())
        if root is child:
            c["id"] = "canonical-id"
        else:
            c["connected-projects"]["children"] = {"canonical-id": str(child.resolve())}
        (root / "tcw-config.yaml").write_text(yaml.safe_dump(c, sort_keys=False))
    c = yaml.safe_load((child / "tcw-config.yaml").read_text())
    c["connected-projects"] = {"parent": {"parent": str(parent.resolve())}}
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(c, sort_keys=False))

    with pytest.raises(ValueError, match="no child node 'sub-dir-name'"):
        delegate(parent, "sub-dir-name", "by directory name")
    doc = delegate(parent, "canonical-id", "by project id")
    assert doc.parent == FsWorkStore.open(child).root / "inbox"


def test_delegate_help_names_the_project_id(capsys):
    """The defect this pins is documentation, not behavior: the help string used
    to promise a path, which is the one thing that does not resolve."""
    from tcw.cli import main
    with pytest.raises(SystemExit):
        main(["work", "delegate", "--help"])
    text = capsys.readouterr().out.lower()
    assert "project id" in text
    assert "path" not in text


def test_delegate_unknown_child_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    mk_node(parent, "child")
    with pytest.raises(ValueError):
        delegate(parent, "nope", "x")


@pytest.mark.parametrize("title,expected_title,expected_body", [
    ("Ship the exporter", "Ship the exporter", "ship-the-exporter"),
    ("Fix auth\nurgently", "Fix auth", "fix-auth"),      # `# {title}` keeps line one
    ("東京", "東京", "untitled"),                          # nothing to slugify
    ("!!! ???", "!!! ???", "untitled"),
])
def test_delegated_titles_round_trip_through_inbox_accept(tmp_path, title,
                                                          expected_title, expected_body):
    """The whole point of the item, end to end through the real `delegate`.

    `_inbox_write` names its entry `<date>-<slugified-title>.md`, so a title with
    nothing to slugify produces a bare `<date>-.md` — the shape that put the date
    in the accepted slug twice. Approximating these entries by hand is what let
    that case through the first time.
    """
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    delegate(parent, "child", title, body="details")

    st = FsWorkStore.open(child)
    entry, = st.inbox_list()
    item = st.inbox_accept(entry.ref)
    assert item.title == expected_title
    assert item.slug == f"{date.today().isoformat()}-{expected_body}"


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


def test_inbox_write_refuses_to_manufacture_a_missing_store_root(tmp_path):
    node = mk_node(tmp_path, "node")
    store = FsWorkStore.open(node)
    shutil.rmtree(store.root)

    with pytest.raises(ValueError, match="work store root does not exist"):
        _inbox_write(store, "Lost request", "body", "node", None)
    assert not store.root.exists()


def test_cli_delegate_to_a_broken_child_store_fails_loudly(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    stores = mk_node(tmp_path, "stores")
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child", work_repo=stores)
    shutil.rmtree(FsWorkStore.open(child).root)
    monkeypatch.chdir(parent)

    assert main(["work", "delegate", "child", "Do a thing"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "tcw work delegate:" in captured.err
    assert not (child / "docs" / "work").exists()


def test_inbox_write_restores_a_missing_inbox_leaf(tmp_path):
    node = mk_node(tmp_path, "node")
    store = FsWorkStore.open(node)
    shutil.rmtree(store.root / "inbox")

    doc = _inbox_write(store, "Still lands", "body", "node", None)
    assert doc.parent == store.root / "inbox"


# ── Task 5: worktrees ────────────────────────────────────────────────────────

def test_ensure_worktree_ignored_reports_whether_it_changed(tmp_path):
    """The return value is what tells a split-repository caller whether the code
    node still owes a `.gitignore` commit."""
    root = mk_node(tmp_path, "repo")
    assert ensure_worktree_ignored(root) is True
    assert ensure_worktree_ignored(root) is False

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
    (wt / "docs" / "work" / "active" / slug / "initial-request.md").write_text("worktree edit\n")
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


def _submit_then_complete_a_worktree_item(root: Path, capsys) -> tuple[str, str]:
    """Drive the flow that straddles a transition rename: start `--worktree`, ADD
    a file inside the item folder on the branch, `submit` (which renames that
    folder on the primary checkout), then `complete`.

    The addition is the load-bearing detail. Directory-rename confirmation fires
    on files *added* inside a renamed directory, so a test that only modifies an
    already-tracked file passes against the unfixed code — which is why the two
    older merge-back tests miss this.

    Returns (slug, implementation commit sha).
    """
    from tcw.cli import main
    commit_all(root)                                      # caller has already chdir'd
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug

    (wt / "docs" / "work" / "active" / slug / "outcome.md").write_text("shipped\n")
    (wt / "feature.py").write_text("x = 1\n")             # code, outside the renamed dir
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "impl"], check=True)
    impl = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

    assert main(["work", "submit", slug]) == 0            # renames active/ → review/
    capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    capsys.readouterr()
    return slug, impl


def test_complete_merges_across_a_transition_rename(tmp_path, monkeypatch, capsys):
    """`submit` renames `active/<slug>/` on the primary checkout while the branch
    keeps committing under the old path. Git knows where the branch's new file
    belongs and stages it there, but stops for confirmation — which TCW used to
    read as a failed merge, refusing to complete a perfectly mergeable item."""
    root = mk_node(tmp_path, "repo")
    monkeypatch.chdir(root)

    slug, impl = _submit_then_complete_a_worktree_item(root, capsys)

    work = root / "docs" / "work"
    assert (work / "completed" / slug / "outcome.md").read_text() == "shipped\n"
    assert not (work / "active" / slug).exists()
    assert not (work / "review" / slug).exists()
    assert subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                           impl, "HEAD"]).returncode == 0          # no data loss
    assert (root / "feature.py").read_text() == "x = 1\n"
    assert not (root / ".worktrees" / slug).exists()
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches == ""
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_merges_across_a_rename_despite_local_git_config(tmp_path, monkeypatch,
                                                                  capsys):
    """The merge-back is TCW's decision, not an ambient preference. A repository
    that explicitly asks for the stopping behavior still completes, and TCW does
    not rewrite that setting to get there."""
    root = mk_node(tmp_path, "repo")
    subprocess.run(["git", "-C", str(root), "config",
                    "merge.directoryRenames", "conflict"], check=True)
    monkeypatch.chdir(root)

    slug, _impl = _submit_then_complete_a_worktree_item(root, capsys)

    assert FsWorkStore.open(root).get(slug).status == "completed"
    value = subprocess.run(["git", "-C", str(root), "config", "--get",
                            "merge.directoryRenames"], capture_output=True, text=True)
    assert value.stdout.strip() == "conflict"             # left exactly as the user set it


def test_merge_worktree_is_a_quiet_no_op_without_the_branch(tmp_path):
    """A recovery re-run, or an external flow that already cleaned up. Returning
    None (rather than running `git merge` against a branch that isn't there and
    reporting its error) is what makes `complete` re-runnable."""
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    assert merge_worktree(root, "work/never-existed") is None


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
    item_doc = ["docs", "work", "active", slug, "initial-request.md"]
    # Diverging content at the SAME path → conflicting merge. `add -A` rather
    # than `commit -am`: `work new` no longer leaves a request behind, so this
    # file is new on both sides (an add/add conflict, which merges just as badly).
    (wt.joinpath(*item_doc)).write_text("worktree side\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "wt"], check=True)
    (root.joinpath(*item_doc)).write_text("main side\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "main"], check=True)

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


def test_reconcile_counts_a_discarded_child_as_resolved(tmp_path):
    """The rollup asks "is this still open?", so a discarded child is done being
    worked on and must not hold its epic open forever."""
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    epic_store = FsWorkStore.open(parent)
    epic = epic_store.create("Epic", created="2026-01-01")
    epic_store.set_field(epic.slug, "type", "epic")
    epic_store.start(epic.slug)
    task_store = FsWorkStore.open(child)
    task = task_store.create("Slice", created="2026-01-02")
    task_store.set_field(task.slug, "initiative", epic.slug)

    with pytest.raises(ValueError, match="initiative children are still open"):
        epic_store.complete(epic.slug, "done", [])

    task_store.complete(task.slug, "wontfix", [])            # abandoned, not shipped
    assert FsWorkStore.open(child).get(task.slug).status == "discarded"
    block = reconcile(parent, epic.slug)
    assert "ready-to-close" in block or "ready to close" in block.lower()
    assert epic_store.complete(epic.slug, "done", []).status == "completed"


# ── the rollup is a sidecar, not the request ─────────────────────────────────

def test_reconcile_writes_a_sidecar_and_never_the_request(tmp_path):
    """Reconciling is not the `request` stage. A machine writing a table into
    `initial-request.md` lit `R` on the board for an item nobody wrote up."""
    parent, epic = _epic_with_a_slice(tmp_path)
    store = FsWorkStore.open(parent)

    block = reconcile(parent, epic)

    # Listed, not probed: the point is that nothing else was created either.
    assert {p.name for p in store.path(epic).iterdir()} == {
        "state.yaml", "rollup.md"}
    assert block in store.read_sidecar(epic, "rollup.md").content
    # The board letter follows from the artifact's absence, so absence is what
    # gets asserted. An earlier version of this line looked for "R" among the
    # names `artifacts()` yields, which are `initial-request`, `spec`, … — a set
    # that cannot contain a board letter, so the check passed either way.
    assert store.read_artifact(epic, "initial-request") is None


def test_reconcile_migrates_a_legacy_rollup_out_of_the_request(tmp_path):
    """Every epic reconciled before this wrote its rollup into the request."""
    parent, epic = _epic_with_a_slice(tmp_path)
    store = FsWorkStore.open(parent)
    reconcile(parent, epic)
    legacy = store.read_sidecar(epic, "rollup.md").content
    store._rm(store.path(epic) / "rollup.md")
    store.write_artifact(epic, "initial-request",
                         f"# Redesign\n\nWhat a human wrote.\n\n{legacy}")

    reconcile(parent, epic)

    request = store.read_artifact(epic, "initial-request").content
    assert "What a human wrote." in request                # prose survives
    assert "<!-- tcw:rollup -->" not in request            # the block does not
    assert "<!-- tcw:rollup -->" in store.read_sidecar(epic, "rollup.md").content


def test_reconcile_migration_leaves_no_empty_request(tmp_path):
    """A request holding only the rollup was never a request. Stripping it must
    remove the file, not leave a husk that reads as a written-up item."""
    parent, epic = _epic_with_a_slice(tmp_path)
    store = FsWorkStore.open(parent)
    reconcile(parent, epic)
    legacy = store.read_sidecar(epic, "rollup.md").content
    store._rm(store.path(epic) / "rollup.md")
    store.write_artifact(epic, "initial-request", f"\n\n{legacy}\n")

    reconcile(parent, epic)

    assert not (store.path(epic) / "initial-request.md").exists()
    assert store.read_artifact(epic, "initial-request") is None


def test_reconcile_stages_nothing_when_the_rollup_is_unchanged(tmp_path):
    """Idempotence is load-bearing: an unchanged rollup that still staged would
    make every `--commit` reconcile a no-op commit attempt."""
    parent, epic = _epic_with_a_slice(tmp_path)
    reconcile(parent, epic, commit=True)
    assert porcelain(parent) == ""

    reconcile(parent, epic)

    assert porcelain(parent) == ""


def test_an_unresolvable_epic_names_the_missing_projects(tmp_path):
    """A partial graph makes an epic unresolvable, and that is not "not active"."""
    import subprocess
    import yaml
    from tcw.store.fs import FsWorkStore, init

    root = tmp_path / "child"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "child-project")
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg["connected-projects"] = {"parent": {"away-project": str(tmp_path / "away")}}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    store = FsWorkStore.open(root)
    task = store.create("A slice of an epic we cannot see")
    store.set_field(task.slug, "initiative", "an-epic-somewhere-else")
    with pytest.raises(ValueError) as excinfo:
        store.start(task.slug)
    message = str(excinfo.value)
    assert "Cannot resolve epic an-epic-somewhere-else" in message
    assert "away-project" in message
