"""Test TCW capabilities across different folder-structure environments.

Four environments are scaffolded on ``tmp_path``:

1. **Lone project** — one TCW node at the git-repo root (the current
   canonical layout).  No inheritance, no children.

2. **Nested monorepo** — multiple TCW nodes nested inside a single git repo.
   Subprojects inherit from the root project through their ``parents:``
   link, the root placed by a *relative* manifest location.  Parent-child
   node relations derive from nesting.

3. **Sibling nodes with absolute-path inheritance** — two (or more) sibling
   git repos under a common parent directory.  Each inherits from the parent
   through its ``parents:`` link, the parent's folder written from its
   *absolute* path.  Parent-child relations derive from the enclosing git
   worktree.

4. **Linked git worktree** — a node checked out in a linked worktree
   (``git worktree add``) rather than its primary checkout.  A relative
   location in its manifest was authored against the node's primary
   position on disk, so inside the worktree it is off by the worktree's nesting
   depth; the registry re-anchors it against the main worktree root and folds
   the two on-disk copies of the current node into one graph entry.  The
   monorepo-inside-a-worktree and non-git shapes ride along here as the two
   layouts that must **not** change.

Every environment is exercised against all three components (taxonomy,
capabilities, work) plus the node-relation operations (``nodes``,
``reconcile``, ``delegate``, ``escalate``).
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, WorkLocation, init, load_yaml,
)
from tcw.store.project import FsProjectRegistry
from tests.statefiles import write_state, CAPABILITY_STATE, TAXONOMY_STATE


def _parent_folder(root):
    """The folder of the project's first ancestor, or None."""
    ancestors = FsProjectRegistry.open(root).require_valid().ancestors()
    return Path(ancestors[-1].locator) if ancestors else None


def _child_folders(root):
    return [Path(p.locator) for p in FsProjectRegistry.open(root).require_valid().children()]


def _descendant_folders(root):
    return [Path(p.locator)
            for p in FsProjectRegistry.open(root).require_valid().descendants()]


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


from tests.projectfiles import config_file, write_config, write_config_file, write_manifest


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
    init(["taxonomy", "capabilities", "work"], root, "lone")
    return root


def nested_monorepo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (root, child-a, child-b) for a monorepo with nested children.

    Root and children share **one git repo**; each is a node via its own
    ``tcw-config.yaml`` sentinel.  Children inherit from root through their
    ``parents:`` link, which passes every axis.

    NB: cross-node *work* discovery (the registry's children, ``delegate``, ``reconcile``)
    is git-repo-scoped in SP1 — plain subfolders of one repo are valid single
    nodes but are not enumerated as child nodes.  Spanning subfolders is SP2
    (unbuilt); the boundary tests below pin that contract.
    """
    root = tmp_path / "mono"
    root.mkdir()
    _git_init(root)
    init(["taxonomy", "capabilities", "work"], root, "root")
    _commit_all(root)

    child_a = root / "a"
    child_b = root / "b"
    child_a.mkdir()
    child_b.mkdir()
    init(["taxonomy", "capabilities", "work"], child_a, "child-a")
    init(["taxonomy", "capabilities", "work"], child_b, "child-b")

    write_config(root, yaml.safe_dump({
        "id": "root",
        "children": ["child-a", "child-b"],
    }, sort_keys=False))
    write_manifest(root, {"child-a": "a", "child-b": "b"})
    for child, child_id in ((child_a, "child-a"), (child_b, "child-b")):
        write_config(child, yaml.safe_dump({
            "id": child_id,
            "parents": ["root"],
        }, sort_keys=False))
        write_manifest(child, {"root": ".."})

    return root, child_a, child_b


def sibling_nodes(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (parent, left, right) for two sibling repos inheriting from parent.

    Each sibling is its own git repo.  The *parent* is a git repo that
    contains the two sibling repos as subdirectories (and has ``docs/work/``
    so it qualifies as a node for the registry's parents and children).
    Left and right inherit from the parent through their ``parents:`` link,
    its folder written from its *absolute* path.
    """
    parent = tmp_path / "parent"
    parent.mkdir()
    _git_init(parent)
    # parent needs taxonomy (children inherit it) and work (node-relation ops)
    init(["taxonomy", "work"], parent, "parent")
    # NB: don't _commit_all(parent) — untracked nested git repos (left/right)
    # would block the commit. The registry only reads the files.

    left = parent / "left"
    left.mkdir()
    _git_init(left)
    init(["taxonomy", "capabilities", "work"], left, "left")

    right = parent / "right"
    right.mkdir()
    _git_init(right)
    init(["taxonomy", "capabilities", "work"], right, "right")

    # A manifest's locations are relative, so each absolute folder is written
    # relative to the project whose manifest names it.
    write_config(parent, yaml.safe_dump({
        "id": "parent",
        "children": ["left", "right"],
    }, sort_keys=False))
    write_manifest(parent, {"left": os.path.relpath(left.resolve(), parent),
                            "right": os.path.relpath(right.resolve(), parent)})
    for child, child_id in ((left, "left"), (right, "right")):
        write_config(child, yaml.safe_dump({
            "id": child_id,
            "parents": ["parent"],
        }, sort_keys=False))
        write_manifest(child, {"parent": os.path.relpath(parent.resolve(), child)})

    return parent, left, right


def two_node_graph(tmp_path: Path, absolute: bool = False) -> tuple[Path, Path]:
    """Return (workspace, server) — a workspace-root node holding a child node.

    Only the child is a git repo, so the child's ``..`` locator points at a
    directory outside its own repo: the shape a linked worktree displaces.
    Pass ``absolute=True`` to declare both sides of the connection by absolute
    path instead.
    """
    workspace = tmp_path / "example-app"
    server = workspace / "example-server"
    workspace.mkdir()
    server.mkdir()
    init(["taxonomy", "capabilities", "work"], workspace, "example-app")
    init(["taxonomy", "capabilities", "work"], server, "example-server")
    # A manifest's locations are relative: an absolute folder is written
    # relative to the project whose manifest names it.
    up = os.path.relpath(workspace.resolve(), server) if absolute else ".."
    down = os.path.relpath(server.resolve(), workspace) if absolute else "example-server"
    write_config(workspace, yaml.safe_dump({
        "id": "example-app",
        "children": ["example-server"],
    }, sort_keys=False))
    write_manifest(workspace, {"example-server": down})
    write_config(server, yaml.safe_dump({
        "id": "example-server",
        "parents": ["example-app"],
    }, sort_keys=False))
    write_manifest(server, {"example-app": up})
    return workspace, server


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
        assert st.get_view("admin").name == "Admin"
        assert st.get_view("admin/permission").slug == "admin/permission"
        assert {t.slug for t in st.list_all()} == {"admin", "admin/permission", "user"}
        assert {t.slug for t in st.list_all(local_only=True)} == {"admin", "admin/permission", "user"}
        assert st.search("admin")
        assert not st.search("nonexistent")

    def test_taxonomy_rm_local(self, tmp_path):
        root = lone_project(tmp_path)
        st = FsTaxonomyStore.open(root)
        st.add("Temp")
        st.remove("temp")
        assert st.get_view("temp") is None

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
        nope = f"{st.project_id}.taxonomy/nope"
        write_state(d / TAXONOMY_STATE, yaml.safe_dump({"name": "Thing", "relatesTo": [nope]}))
        problems = [str(f) for f in st.check()]
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
        assert st.get_view("routes/home").status == "Supported"

    def test_capabilities_check_clean(self, tmp_path):
        root = lone_project(tmp_path)
        FsCapabilitiesStore.open(root).add("routes/x", status="Supported")
        assert FsCapabilitiesStore.open(root).check() == []


    def test_nodes_leaf(self, tmp_path):
        root = lone_project(tmp_path)
        p = _parent_folder(root)
        c = _child_folders(root)
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
        """Invalid data is written directly, not through `set`: `set` refuses a
        dangling ref at write time now. `check` must still report data that
        predates that rule — which is what keeps an existing bad ref
        repairable rather than stuck."""
        root = lone_project(tmp_path)
        tax = FsTaxonomyStore.open(root)
        caps = FsCapabilitiesStore.open(root)
        caps.add("routes/x", status="Supported")
        meta_path = root / "docs" / "capabilities" / "routes" / "x" / CAPABILITY_STATE
        meta = load_yaml(meta_path)
        meta["Subject"] = [f"{tax.project_id}.taxonomy/ghost"]
        write_state(meta_path,
            yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
        problems = [str(f) for f in caps.check(taxonomy=tax)]
        assert any("dangling" in p for p in problems)


# ────────────────────────────────────────────────────────────────────────
# 2. Nested Monorepo (direct inheritance)
# ────────────────────────────────────────────────────────────────────────


class TestNestedMonorepo:
    """Subprojects inside one repo inherit taxonomy from root through `parents:`."""

    def test_root_taxonomy_visible_to_child(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        st_a = FsTaxonomyStore.open(child_a)
        shared = st_a.get_view("shared")
        assert (shared.name, shared.owner) == ("Shared", "root")

    def test_child_cannot_see_other_child_taxonomy(self, tmp_path):
        root, child_a, child_b = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(child_a).add("LocalA")
        st_b = FsTaxonomyStore.open(child_b)
        assert st_b.get_view("locala") is None
        assert FsTaxonomyStore.open(root).get_view("locala") is None  # not in root either

    def test_child_can_add_local_terms(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        st = FsTaxonomyStore.open(child_a)
        st.add("Plugin")
        assert st.get_view("plugin").origin == "local"
        # Root's terms are in the child's view, owned by root
        assert st.get_view("shared").origin == "root"

    def test_local_wins_bare_ref_in_child(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("Shared")
        # At an inherited path, `add` writes an override, which must differ
        # from what it inherits (TCW-112 Design 4.1).
        FsTaxonomyStore.open(child_a).add("Shared", slug="shared",
                                          description="The child's own meaning.")
        found = FsTaxonomyStore.open(child_a).get_view("shared")
        assert found.origin == "local"
        assert str(found.overrides) == "root.taxonomy/shared"

    def test_child_node_relation_parent(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        assert _parent_folder(child_a).resolve() == root.resolve()

    def test_registered_subfolder_children_are_discovered(self, tmp_path):
        root, child_a, child_b = nested_monorepo(tmp_path)
        found = {p.resolve() for p in _child_folders(root)}
        assert child_a.resolve() in found
        assert child_b.resolve() in found


    def test_capabilities_standalone_in_child(self, tmp_path):
        _, child_a, _ = nested_monorepo(tmp_path)
        caps = FsCapabilitiesStore.open(child_a)
        caps.add("routes/local", status="Supported")
        assert caps.get_view("routes/local").status == "Supported"
        assert caps.check() == []


    def test_child_can_check_capabilities_with_inherited_taxonomy(self, tmp_path):
        root, child_a, _ = nested_monorepo(tmp_path)
        FsTaxonomyStore.open(root).add("User")
        caps = FsCapabilitiesStore.open(child_a)
        caps.add("routes/profile", status="Supported")
        caps.set("routes/profile", {"Subject": "root.taxonomy/user"})
        assert caps.check(taxonomy=FsTaxonomyStore.open(child_a)) == []

    def test_nested_deep_children_found(self, tmp_path):
        root, _, _ = nested_monorepo(tmp_path)
        deep = root / "a" / "deep"
        deep.mkdir(parents=True)
        _git_init(deep)
        init(["work"], deep, "deep")
        child_a = root / "a"
        child_cfg = yaml.safe_load((child_a / ".tcw/tcw-config.yaml").read_text()) or {}
        child_cfg.setdefault("children", []).append("deep")
        write_config(child_a,
            yaml.safe_dump(child_cfg, sort_keys=False)
        )
        write_manifest(child_a, {"deep": "deep"})
        write_config(deep,
            "id: deep\nparents:\n- child-a\n"
        )
        write_manifest(deep, {"child-a": ".."})
        _commit_all(deep)
        found = _descendant_folders(root)
        deep_path = deep.resolve()
        assert any(f.resolve() == deep_path for f in found)


# ────────────────────────────────────────────────────────────────────────
# 3. Sibling Nodes (absolute-path inheritance)
# ────────────────────────────────────────────────────────────────────────


class TestSiblingNodes:
    """Two sibling repos under a common parent, each inheriting from it."""

    def test_sibling_inherits_via_absolute_path(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(parent).add("Platform")
        st = FsTaxonomyStore.open(left)
        platform = st.get_view("platform")
        assert (platform.name, platform.owner) == ("Platform", "parent")

    def test_sibling_standalone_taxonomy(self, tmp_path):
        _, left, _ = sibling_nodes(tmp_path)
        st = FsTaxonomyStore.open(left)
        st.add("Feature")
        assert st.get_view("feature").origin == "local"

    def test_siblings_cannot_see_each_other(self, tmp_path):
        parent, left, right = sibling_nodes(tmp_path)
        FsTaxonomyStore.open(left).add("Leftonly")
        st_right = FsTaxonomyStore.open(right)
        assert st_right.get_view("leftonly") is None
        assert FsTaxonomyStore.open(parent).get_view("leftonly") is None

    def test_child_nodes_finds_siblings(self, tmp_path):
        parent, left, right = sibling_nodes(tmp_path)
        found = _child_folders(parent)
        found_resolved = {p.resolve() for p in found}
        assert left.resolve() in found_resolved
        assert right.resolve() in found_resolved

    def test_parent_node_resolved_through_git(self, tmp_path):
        parent, left, _ = sibling_nodes(tmp_path)
        # the parent is found through the manifests and the search
        p = _parent_folder(left)
        assert p is not None
        # The parent must be a node (has docs/work/) and be reachable
        assert (p / "docs" / "work").is_dir()


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
        caps.set("routes/profile", {"Subject": "parent.taxonomy/user"})
        st = FsTaxonomyStore.open(left)
        assert caps.check(taxonomy=st) == []


# ────────────────────────────────────────────────────────────────────────
# 4. Linked Git Worktree
# ────────────────────────────────────────────────────────────────────────


class TestWorktreeNode:
    """A node operated from a linked worktree rather than its primary checkout."""


    def test_non_git_graph_is_unaffected(self, tmp_path, monkeypatch):
        from tcw.cli import main
        _, server = two_node_graph(tmp_path)          # no _git_init anywhere
        monkeypatch.chdir(server)
        for argv in (["work", "list"], ["validate"], ["projects", "list"]):
            assert main(argv) == 0, argv


# ────────────────────────────────────────────────────────────────────────
# 5. CLI Smoke in Each Environment
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
        assert main(["taxonomy", "list", "--scope", "up"]) == 0
        parent_out = capsys.readouterr().out

        monkeypatch.chdir(left)
        # List from left — should see the inherited term (slug + origin flag)
        assert main(["taxonomy", "list", "--scope", "up"]) == 0
        left_out = capsys.readouterr().out
        assert "parent.taxonomy/platform" in left_out.split()
        assert "parent.taxonomy/platform" in parent_out

    def test_nested_cli_nodes_command(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root, child_a, _ = nested_monorepo(tmp_path)
        monkeypatch.chdir(root)
        assert main(["projects", "list"]) == 0
        out = capsys.readouterr().out.split()
        assert "child-a" in out and "child-b" in out

    def test_lone_cli_nodes_leaf(self, tmp_path, monkeypatch, capsys):
        from tcw.cli import main
        root = lone_project(tmp_path)
        monkeypatch.chdir(root)
        assert main(["projects", "list"]) == 0
        assert len(capsys.readouterr().out.split()) == 1

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

        # The old `capabilities check` is part of `tcw validate` now; the
        # sibling's Subject-free capability checks clean against its store.
        assert FsCapabilitiesStore.open(left).check() == []


# ────────────────────────────────────────────────────────────────────────
# 6. Cross-Environment Property Tests
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
        assert st.get_view("term").name == "Term"
        assert st.search("term")

    def test_capabilities_add_and_query(self, env):
        root, _ = env
        st = FsCapabilitiesStore.open(root)
        st.add("test/cap", status="Supported")
        assert st.get_view("test/cap").status == "Supported"


# ────────────────────────────────────────────────────────────────────────
# 5. A nested node's `work.path` inside a linked worktree
# ────────────────────────────────────────────────────────────────────────


def _resolved(project_root: Path, configured: str | None) -> Path:
    """`_local_root` as the caller invokes it — on an already-resolved node root
    (`tcw/store/fs.py` resolves before calling) — normalized for comparison."""
    return WorkLocation._local_root(project_root.resolve(), configured).resolve()


# ── load_yaml's mapping contract ─────────────────────────────────────────────
# (spec: 2026-08-20-load-yaml-reads-a-falsy-yaml-document-as-an-empty-mapping)

@pytest.mark.parametrize("text,found", [
    ("[]\n", "list"),
    ("false\n", "bool"),
    ("0\n", "int"),
    ("- a\n- b\n", "list"),
    ("hello\n", "str"),
])
def test_load_yaml_refuses_a_document_that_is_not_a_mapping(tmp_path, text, found):
    """`return data or {}` turned the falsy shapes into a mapping and let the
    truthy ones through unchanged, so the annotation and the docstring were both
    untrue. A falsy config was silently overwritten where a truthy one was
    refused, and a truthy state file crashed the board."""
    p = tmp_path / "doc.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(yaml.YAMLError) as caught:
        load_yaml(p)
    assert str(p) in str(caught.value)
    assert found in str(caught.value)


@pytest.mark.parametrize("text", [None, "", "\n", "null\n", "# just a comment\n"])
def test_load_yaml_reads_a_contentless_document_as_empty(tmp_path, text):
    """Absent, empty and explicitly null all mean "no content" and stay `{}`.
    Separating them would need the raw text and no caller wants the difference."""
    p = tmp_path / "doc.yaml"
    if text is not None:
        p.write_text(text, encoding="utf-8")
    assert load_yaml(p) == {}


@pytest.mark.parametrize("text,expected", [
    ("{}\n", {}),
    ("id: demo\n", {"id": "demo"}),
    ("a:\n  b: 1\n", {"a": {"b": 1}}),
])
def test_load_yaml_returns_a_mapping_unchanged(tmp_path, text, expected):
    """A literal `{}` is a mapping someone wrote, not an absent document."""
    p = tmp_path / "doc.yaml"
    p.write_text(text, encoding="utf-8")
    assert load_yaml(p) == expected


# ── and what the contract looks like from the command line ───────────────────

@pytest.mark.parametrize("text", ["[]\n", "false\n", "0\n", "- a\n"])
def test_init_refuses_a_malformed_config_and_leaves_it_alone(
        tmp_path, monkeypatch, capsys, text):
    """The defect that was reported: a *falsy* config read as "no configuration"
    and `init` wrote over it without a word, while the same file holding `- a`
    was refused. Now every shape is refused, the file is untouched, and the user
    gets a message instead of a traceback."""
    import hashlib
    import subprocess

    from tcw.cli import main

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    config = config_file(root)
    write_config_file(config, text, encoding="utf-8")
    before = hashlib.sha256(config.read_bytes()).hexdigest()
    monkeypatch.chdir(root)

    assert main(["init", "--id", "demo"]) == 1
    assert hashlib.sha256(config.read_bytes()).hexdigest() == before
    err = capsys.readouterr().err
    assert "tcw-config.yaml" in err, err
    assert "Traceback" not in err, err


@pytest.mark.parametrize("text", ["[]\n", "- a\n"])
def test_a_corrupt_state_file_does_not_take_the_board_down(
        tmp_path, monkeypatch, capsys, text):
    """`_safe_yaml` promises that "a malformed state file degrades to empty
    rather than crashing the board". It catches `yaml.YAMLError`, and a
    well-formed non-mapping never raised one — so a `- a` state file reached
    `.get` and one corrupt item made the whole board unreadable."""
    import subprocess

    from tcw.cli import main
    from tcw.store.fs import init

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    init(["taxonomy", "capabilities", "work"], root, "demo")
    monkeypatch.chdir(root)
    assert main(["work", "new", "real item"]) == 0
    slug = next(p.name for p in (root / "docs/work/backlog").iterdir() if p.is_dir())
    (root / "docs/work/backlog" / slug / "state.yaml").write_text(text, encoding="utf-8")
    capsys.readouterr()

    assert main(["work", "list"]) == 0
    assert slug in capsys.readouterr().out
    assert main(["work", "show", slug]) == 0


def test_validate_names_a_corrupt_state_file_the_board_tolerated(
        tmp_path, monkeypatch, capsys):
    """Degrading is not reporting. The board is deliberately tolerant, so
    `validate` is the one command that has to say the file is not a state file —
    otherwise a corrupt item reads as healthy everywhere and nothing contradicts
    it."""
    import subprocess

    from tcw.cli import main
    from tcw.store.fs import init

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    init(["taxonomy", "capabilities", "work"], root, "demo")
    monkeypatch.chdir(root)
    assert main(["work", "new", "real item"]) == 0
    slug = next(p.name for p in (root / "docs/work/backlog").iterdir() if p.is_dir())
    (root / "docs/work/backlog" / slug / "state.yaml").write_text("[]\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["validate"]) == 1
    assert "state.yaml" in capsys.readouterr().err
