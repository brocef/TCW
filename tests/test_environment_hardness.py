"""Test TCW capabilities across different folder-structure environments.

Three environments are scaffolded on ``tmp_path``:

1. **Lone project** — one TCW node at the git-repo root (the current
   canonical layout).  No inheritance, no children.

2. **Nested monorepo** — multiple TCW nodes nested inside a single git repo.
   Subprojects inherit taxonomy from the root project via *relative* paths in
   ``extends``.  Parent-child node relations derive from nesting.

3. **Sibling nodes with absolute-path inheritance** — two (or more) sibling
   git repos under a common parent directory.  Inheritance is declared with
   *absolute* paths.  Parent-child relations derive from the enclosing git
   worktree.

Every environment is exercised against all three components (taxonomy,
capabilities, work) plus the node-relation operations (``nodes``,
``reconcile``, ``delegate``, ``escalate``).
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import (
    FsCapabilitiesStore,
    FsTaxonomyStore,
    FsWorkStore,
    child_nodes,
    init,
    parent_node,
    write_sentinel,
)
from tcw.work.recursion import delegate, escalate, reconcile


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _commit_all(root: Path, msg: str = "init") -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    r = subprocess.run(["git", "-C", str(root), "commit", "-qm", msg],
                       capture_output=True, text=True)
    # "nothing to commit" is fine — init is idempotent (message can be stdout or stderr)
    output = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and "nothing to commit" not in output:
        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)


# ────────────────────────────────────────────────────────────────────────
# Environment factories
# ────────────────────────────────────────────────────────────────────────


def lone_project(tmp_path: Path) -> Path:
    """Return the git-repo root of a single TCW project at the repo root."""
    root = tmp_path / "lone"
    root.mkdir()
    _git_init(root)
    init(["taxonomy", "capabilities", "work"], root)
    return root


def nested_monorepo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (root, child-a, child-b) for a monorepo with nested children.

    Root and children share **one git repo**; each is a node via its own
    ``tcw-config.yaml`` sentinel.  Children inherit taxonomy from root via
    *relative* paths in ``extends``.

    NB: cross-node *work* discovery (``child_nodes``/``delegate``/``reconcile``)
    is git-repo-scoped in SP1 — plain subfolders of one repo are valid single
    nodes but are not enumerated as child nodes.  Spanning subfolders is SP2
    (unbuilt); the boundary tests below pin that contract.
    """
    root = tmp_path / "mono"
    root.mkdir()
    _git_init(root)
    init(["taxonomy", "capabilities", "work"], root)   # root is a node + extends target
    _commit_all(root)

    child_a = root / "a"
    child_b = root / "b"
    child_a.mkdir()
    child_b.mkdir()
    init(["taxonomy", "capabilities", "work"], child_a)
    init(["taxonomy", "capabilities", "work"], child_b)

    # Both children extend the root via relative paths
    (child_a / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"root": ".."}}))
    (child_b / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"root": ".."}}))

    return root, child_a, child_b


def sibling_nodes(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (parent, left, right) for two sibling repos with absolute-path extends.

    Each sibling is its own git repo.  The *parent* is a git repo that
    contains the two sibling repos as subdirectories (and has ``docs/work/``
    so it qualifies as a node for ``parent_node`` / ``child_nodes``).
    Left and right extend the parent via *absolute* paths.
    """
    parent = tmp_path / "parent"
    parent.mkdir()
    _git_init(parent)
    # parent needs taxonomy (children extend it) and work (node-relation ops)
    init(["taxonomy", "work"], parent)
    # NB: don't _commit_all(parent) — untracked nested git repos (left/right)
    # would block the commit. child_nodes only walks the filesystem.

    left = parent / "left"
    left.mkdir()
    _git_init(left)
    init(["taxonomy", "capabilities", "work"], left)

    right = parent / "right"
    right.mkdir()
    _git_init(right)
    init(["taxonomy", "capabilities", "work"], right)

    # Both siblings extend parent using *absolute* paths
    (left / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"parent": str(parent.resolve())}}))
    (right / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"parent": str(parent.resolve())}}))

    return parent, left, right


# ────────────────────────────────────────────────────────────────────────
# 1. Lone Project Environment
# ────────────────────────────────────────────────────────────────────────


class TestLoneProject:
    """All TCW capabilities in a single project at the repo root."""

    def test_taxonomy_add_list_show_search(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsTaxonomyStore.open(root)
        st.add("Admin")
        st.add("Permission", parent="admin")
        st.add("User")
        assert st.get("admin").name == "Admin"
        assert st.get("admin/permission").slug == "admin/permission"
        assert {t.slug for t in st.list_all()} == {"admin", "admin/permission", "user"}
        assert {t.slug for t in st.list_all(local_only=True)} == {"admin", "admin/permission", "user"}
        assert st.search("admin")
        assert not st.search("nonexistent")

    def test_taxonomy_rm_local(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsTaxonomyStore.open(root)
        st.add("Temp")
        st.remove("temp")
        assert st.get("temp") is None

    def test_taxonomy_check_clean(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsTaxonomyStore.open(root)
        st.add("Admin")
        assert st.check() == []

    def test_taxonomy_check_dangling(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsTaxonomyStore.open(root)
        st.add("Thing")
        d = root / "docs" / "taxonomy" / "thing"
        (d / "meta.yaml").write_text(yaml.safe_dump({"name": "Thing", "relatesTo": ["nope"]}))
        problems = st.check()
        assert any("dangling" in p for p in problems)

    def test_capabilities_add_list_search(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsCapabilitiesStore.open(root)
        st.add("routes/login", name="Sign in")
        st.add("api/auth", name="Auth")
        assert {c.path for c in st.list_all()} == {"routes/login", "api/auth"}
        assert any(c.name == "Sign in" for c in st.search("sign"))

    def test_capabilities_set_status(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsCapabilitiesStore.open(root)
        st.add("routes/home")
        st.set("routes/home", {"Status": "Supported"})
        assert st.get("routes/home").status == "Supported"

    def test_capabilities_check_clean(self, tmp_path):
        root = lone_project(tmp_path)
        FsCapabilitiesStore.open(root).add("routes/x", status="Supported")
        assert FsCapabilitiesStore.open(root).check() == []

    def test_work_create_transition_lifecycle(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsWorkStore.open(root)
        item = st.create("Build thing", created="2026-01-01")
        assert item.status == "backlog"
        st.start(item.slug)
        assert st.get(item.slug).status == "active"
        st.complete(item.slug, "done", ["acked"])
        assert st.get(item.slug).status == "completed"

    def test_work_blocker_gating(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsWorkStore.open(root)
        blocker = st.create("Blocker", created="2026-01-01")
        target = st.create("Target", created="2026-01-02")
        st.add_blocker(target.slug, blocker.slug)
        with pytest.raises(ValueError):
            st.start(target.slug)
        st.start(blocker.slug)
        st.complete(blocker.slug, "done", [])
        st.start(target.slug)  # now gated is clear

    def test_work_priority_board_order(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsWorkStore.open(root)
        st.create("Low", created="2026-01-01")
        st.create("High", created="2026-01-02", priority=10)
        ordered = [i.slug for i in st.board()]
        assert ordered[0].startswith("2026-01-02-high")

    def test_work_drop(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsWorkStore.open(root)
        item = st.create("To drop", created="2026-01-01")
        st.drop(item.slug)
        assert st.get(item.slug) is None

    def test_work_parent_child_nesting(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsWorkStore.open(root)
        parent = st.create("Epic", created="2026-01-01")
        child = st.create("Task", created="2026-01-02", parent=parent.slug)
        assert child.parent == parent.slug
        st.start(parent.slug)
        assert st.get(child.slug).status == "active"

    def test_nodes_leaf(self, tmp_path):
        root = lone_project(tmp_path)
        p = parent_node(root)
        c = child_nodes(root)
        assert p is None
        assert c == []

    def test_capability_check_with_subject_ref(self, tmp_path):
        root = lone_project(tmp_path)
        tax = FsTaxonomyStore.open(root)
        tax.add("User")
        caps = FsCapabilitiesStore.open(root)
        caps.add("routes/profile", status="Supported")
        caps.set("routes/profile", {"Subject": "user"})
        assert caps.check(taxonomy=tax) == []

    def test_capability_check_dangling_subject(self, tmp_path):
        root = lone_project(tmp_path)
        tax = FsTaxonomyStore.open(root)
        caps = FsCapabilitiesStore.open(root)
        caps.add("routes/x", status="Supported")
        caps.set("routes/x", {"Subject": "ghost"})
        problems = caps.check(taxonomy=tax)
        assert any("dangling" in p for p in problems)


# ────────────────────────────────────────────────────────────────────────
# 2. Nested Monorepo (direct inheritance)
# ────────────────────────────────────────────────────────────────────────


class TestNestedMonorepo:
    """Subprojects inside one repo inherit taxonomy from root via relative paths."""

    def test_root_taxonomy_visible_to_child(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        st_a = FsTaxonomyStore.open(child_a)
        assert st_a.get("root/shared").name == "Shared"

    def test_child_cannot_see_other_child_taxonomy(self, tmp_path):
        root, child_a, child_b = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(child_a).add("LocalA")
        st_b = FsTaxonomyStore.open(child_b)
        assert st_b.get("locala") is None
        assert st_b.get("root/locala") is None  # not in root either

    def test_child_can_add_local_terms(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        st = FsTaxonomyStore.open(child_a)
        st.add("Plugin")
        assert st.get("plugin").origin == "local"
        # Root's terms are visible through the inherited namespace
        assert st.get("root/shared").origin == "root"

    def test_local_wins_bare_ref_in_child(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        FsTaxonomyStore.open(child_a).add("Shared", slug="shared")
        assert FsTaxonomyStore.open(child_a).get("shared").origin == "local"

    def test_child_node_relation_parent(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        assert parent_node(child_a).resolve() == root.resolve()

    def test_subfolder_children_not_discovered_sp2_boundary(self, tmp_path):
        # SP1 boundary: cross-node child discovery is git-repo-scoped, so plain
        # subfolders of one repo are valid single nodes but are NOT enumerated as
        # child nodes. SP2 will span subfolders; this pins the current contract.
        # (A genuinely separate nested repo IS found — see test_nested_deep_children_found.)
        root, child_a, child_b = nested_monorepo(tmp_path)
        found = {p.resolve() for p in child_nodes(root)}
        assert child_a.resolve() not in found
        assert child_b.resolve() not in found

    def test_escalate_from_child_to_parent(self, tmp_path):
        # Escalation UP works in a monorepo: parent_node climbs the git ancestry
        # and finds the enclosing root node (asymmetric with child discovery).
        root, child_a, _ = nested_monorepo(tmp_path)
        doc = escalate(child_a, "Need help")
        assert doc.parent == root / "docs" / "work" / "inbox"
        assert "from: a" in doc.read_text()

    def test_delegate_to_subfolder_child_unsupported_sp2_boundary(self, tmp_path):
        # SP1 boundary: delegate targets a *discovered* child node; plain
        # subfolders aren't discovered, so delegating down is unsupported until
        # SP2 (escalation UP works — see test_escalate_from_child_to_parent).
        root, _, _ = nested_monorepo(tmp_path)
        with pytest.raises(ValueError):
            delegate(root, "a", "Build this", body="details")

    def test_reconcile_excludes_subfolder_tasks_sp2_boundary(self, tmp_path):
        # SP1 boundary: reconcile scans this node + its *discovered* child nodes.
        # Subfolder tasks live in undiscovered nodes, so they don't roll up yet.
        root, child_a, child_b = nested_monorepo(tmp_path)
        epic = FsWorkStore.open(root).create("Epic", created="2026-01-01")
        for child in (child_a, child_b):
            task = FsWorkStore.open(child).create("Slice", created="2026-01-01")
            FsWorkStore.open(child).set_field(task.slug, "initiative", epic.slug)
        block = reconcile(root, epic.slug)
        assert "2026-01-01-slice" not in block
        assert "No tasks reference this initiative" in block

    def test_capabilities_standalone_in_child(self, tmp_path):
        _, child_a, _ = nested_monorepo(tmp_path)
        caps = FsCapabilitiesStore.open(child_a)
        caps.add("routes/local", status="Supported")
        assert caps.get("routes/local").status == "Supported"
        assert caps.check() == []

    def test_work_standalone_in_child(self, tmp_path):
        _, child_a, _ = nested_monorepo(tmp_path)
        st = FsWorkStore.open(child_a)
        item = st.create("Child task", created="2026-01-01")
        assert item.status == "backlog"
        st.start(item.slug)
        assert st.get(item.slug).status == "active"

    def test_child_can_check_capabilities_with_inherited_taxonomy(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("User")
        caps = FsCapabilitiesStore.open(child_a)
        caps.add("routes/profile", status="Supported")
        caps.set("routes/profile", {"Subject": "root/user"})
        assert caps.check(taxonomy=FsTaxonomyStore.open(child_a)) == []

    def test_nested_deep_children_found(self, tmp_path):
        root, _, _ = nested_monorepo(tmp_path)
        deep = root / "a" / "deep"
        deep.mkdir(parents=True)
        _git_init(deep)
        init(["work"], deep)
        _commit_all(deep)
        found = child_nodes(root)
        deep_path = deep.resolve()
        assert any(f.resolve() == deep_path for f in found)


# ────────────────────────────────────────────────────────────────────────
# 3. Sibling Nodes (absolute-path inheritance)
# ────────────────────────────────────────────────────────────────────────


class TestSiblingNodes:
    """Two sibling repos under a common parent with absolute-path extends."""

    def test_sibling_inherits_via_absolute_path(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(parent).add("Platform")
        st = FsTaxonomyStore.open(left)
        assert st.get("parent/platform").name == "Platform"

    def test_sibling_standalone_taxonomy(self, tmp_path):
        _, left, _ = sibling_nodes(tmp_path)
        st = FsTaxonomyStore.open(left)
        st.add("Feature")
        assert st.get("feature").origin == "local"

    def test_siblings_cannot_see_each_other(self, tmp_path):
        parent, left, right = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(left).add("Leftonly")
        st_right = FsTaxonomyStore.open(right)
        assert st_right.get("leftonly") is None
        assert st_right.get("parent/leftonly") is None

    def test_child_nodes_finds_siblings(self, tmp_path):
        parent, left, right = sibling_nodes(tmp_path)
        found = child_nodes(parent)
        found_resolved = {p.resolve() for p in found}
        assert left.resolve() in found_resolved
        assert right.resolve() in found_resolved

    def test_parent_node_resolved_through_git(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        # parent_node walks up through git worktree ancestry
        p = parent_node(left)
        assert p is not None
        # The parent must be a node (has docs/work/) and be reachable
        assert (p / "docs" / "work").is_dir()

    def test_delegate_parent_to_sibling_fails(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        # delegate expects a child of the *current* node
        with pytest.raises(ValueError):
            delegate(left, "left", "x")  # left is not a child of left

    def test_work_standalone_sibling(self, tmp_path):
        _, left, _ = sibling_nodes(tmp_path)
        st = FsWorkStore.open(left)
        item = st.create("Left task", created="2026-01-01")
        st.start(item.slug)
        st.complete(item.slug, "done", ["acked"])
        assert st.get(item.slug).status == "completed"

    def test_capabilities_standalone_sibling(self, tmp_path):
        _, left, _ = sibling_nodes(tmp_path)
        caps = FsCapabilitiesStore.open(left)
        caps.add("api/sibling", status="Supported")
        assert caps.check() == []

    def test_sibling_check_inherited_taxonomy(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(parent).add("User")
        caps = FsCapabilitiesStore.open(left)
        caps.add("routes/profile", status="Supported")
        caps.set("routes/profile", {"Subject": "parent/user"})
        st = FsTaxonomyStore.open(left)
        assert caps.check(taxonomy=st) == []

    def test_sibling_escalate_to_parent(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        doc = escalate(left, "Cross-sibling request")
        assert doc.parent == parent / "docs" / "work" / "inbox"
        text = doc.read_text()
        assert "from: left" in text

    def test_delegate_parent_to_sibling_succeeds(self, tmp_path):
        # Cross-node delegation DOWN works across separate repos (discovered as
        # child nodes) — the success path the monorepo can't take until SP2.
        parent, left, _ = sibling_nodes(tmp_path)
        doc = delegate(parent, "left", "Build this", body="details")
        assert doc.parent == left / "docs" / "work" / "inbox"
        assert "from: ." in doc.read_text()

    def test_reconcile_scans_sibling_children(self, tmp_path):
        # reconcile rolls up tasks from discovered child repos.
        parent, left, right = sibling_nodes(tmp_path)
        epic = FsWorkStore.open(parent).create("Epic", created="2026-01-01")
        for child in (left, right):
            task = FsWorkStore.open(child).create("Slice", created="2026-01-01")
            FsWorkStore.open(child).set_field(task.slug, "initiative", epic.slug)
        block = reconcile(parent, epic.slug)
        assert "left" in block
        assert "right" in block
        assert "2026-01-01-slice" in block


# ────────────────────────────────────────────────────────────────────────
# 4. CLI Smoke in Each Environment
# ────────────────────────────────────────────────────────────────────────


class TestCLISmoke:
    """End-to-end CLI smoke tests in each environment."""

    def test_lone_project_cli_work_flow(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root = lone_project(tmp_path)
        monkeypatch.chdir(root)
        assert main(["work", "new", "Implement login"]) == 0
        slug = capsys.readouterr().out.strip()
        assert main(["work", "list"]) == 0
        assert slug in capsys.readouterr().out
        assert main(["work", "start", slug]) == 0
        assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0

    def test_nested_monorepo_cli_child_work(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        _, child_a, _ = nested_monorepo(tmp_path)
        monkeypatch.chdir(child_a)
        assert main(["work", "new", "Child task"]) == 0
        slug = capsys.readouterr().out.strip()
        assert main(["work", "start", slug]) == 0
        assert main(["work", "show", slug]) == 0
        assert "active" in capsys.readouterr().out

    def test_sibling_cli_taxonomy_inheritance(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        parent, left, _ = sibling_nodes(tmp_path)
        # Add a term in parent
        subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(parent), "commit", "-qm", "parent init"], check=True)
        subprocess.run(["git", "-C", str(left), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(left), "commit", "-qm", "left init"], check=True)

        monkeypatch.chdir(parent)
        assert main(["taxonomy", "add", "Platform"]) == 0
        # List from parent — should see local
        assert main(["taxonomy", "list"]) == 0
        parent_out = capsys.readouterr().out

        monkeypatch.chdir(left)
        # List from left — should see the inherited term (slug + origin flag)
        assert main(["taxonomy", "list"]) == 0
        left_out = capsys.readouterr().out
        assert "platform" in left_out
        assert "(parent)" in left_out
        assert "platform" in parent_out

    def test_nested_cli_nodes_command(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root, child_a, _ = nested_monorepo(tmp_path)
        monkeypatch.chdir(root)
        assert main(["work", "nodes"]) == 0
        out = capsys.readouterr().out
        # SP1 boundary: subfolder children aren't discovered, so the monorepo
        # root reports no children yet (SP2 will list them).
        assert "leaf" in out

    def test_lone_cli_nodes_leaf(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root = lone_project(tmp_path)
        monkeypatch.chdir(root)
        assert main(["work", "nodes"]) == 0
        out = capsys.readouterr().out
        assert "leaf" in out

    def test_nested_cli_delegate_subfolder_unsupported_sp2_boundary(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root, child_a, _ = nested_monorepo(tmp_path)
        monkeypatch.chdir(root)
        assert main(["work", "new", "Epic", "--epic", "--initiative", "2026-epic"]) == 0
        # SP1 boundary: delegating to a subfolder child is unsupported until SP2
        # (child discovery is git-repo-scoped). The CLI reports the error → rc 1.
        assert main(["work", "delegate", "a", "Implement epic slice"]) != 0

    def test_sibling_cli_check_capabilities(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        parent, left, _ = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(parent).add("User")
        FsCapabilitiesStore.open(left).add("routes/x", status="Supported")
        subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(parent), "commit", "-qm", "p"], check=True)
        subprocess.run(["git", "-C", str(left), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(left), "commit", "-qm", "l"], check=True)

        monkeypatch.chdir(left)
        assert main(["capabilities", "check"]) == 0
        assert "capabilities OK" in capsys.readouterr().out


# ────────────────────────────────────────────────────────────────────────
# 5. Cross-Environment Property Tests
# ────────────────────────────────────────────────────────────────────────


class TestCrossEnvironment:
    """Properties that should hold in all three environments."""

    @pytest.fixture(params=["lone", "nested", "sibling"])
    def env(self, request, tmp_path):
        """Yields (root, extra) where extra is None/child_a/parent."""
        if request.param == "lone":
            return lone_project(tmp_path), None
        _, child_a, _ = nested_monorepo(tmp_path)
        if request.param == "nested":
            return child_a, child_a
        _, left, _ = sibling_nodes(tmp_path)
        return left, left

    def test_taxonomy_add_and_query(self, env):
        root, _ = env
        st = FsTaxonomyStore.open(root)
        st.add("Term")
        assert st.get("term").name == "Term"
        assert st.search("term")

    def test_capabilities_add_and_query(self, env):
        root, _ = env
        st = FsCapabilitiesStore.open(root)
        st.add("test/cap", status="Supported")
        assert st.get("test/cap").status == "Supported"

    def test_work_create_and_transition(self, env):
        root, _ = env
        st = FsWorkStore.open(root)
        item = st.create("Test task", created="2026-01-01")
        st.start(item.slug)
        st.complete(item.slug, "done", ["done"])
        assert st.get(item.slug).resolution == "done"

    def test_check_clean_all_components(self, env):
        root, _ = env
        # Seed minimal valid data
        FsTaxonomyStore.open(root).add("Base")
        FsCapabilitiesStore.open(root).add("x", status="Supported")
        FsWorkStore.open(root).create("Task", created="2026-01-01")
        assert FsTaxonomyStore.open(root).check() == []
        assert FsCapabilitiesStore.open(root).check(taxonomy=FsTaxonomyStore.open(root)) == []
