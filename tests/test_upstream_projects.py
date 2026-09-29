"""An upstream project: one a node reads from, that does not name the node back
(spec: 2026-09-29-let-a-project-read-taxonomy-and-capabilities-from-a-connected-
project-that-does-not-name-it-back).

Every fixture writes each project's `connected-projects` in full. None defaults
a relation, a path or a repository entry: the relation is exactly the axis the
code under test branches on."""

from pathlib import Path

from tcw.store.project import FsProjectRegistry


def config(root: Path, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(text, encoding="utf-8")


# ── loading ──────────────────────────────────────────────────────────────────

def test_a_bare_path_upstream_loads_without_naming_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None
    assert Path(registry.get("core").locator) == (tmp_path / "core").resolve()
    assert registry.declared_upstream_ids() == ["core"]


def test_a_mapping_upstream_loads_by_its_path(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core:\n      path: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_the_override_variable_wins_for_an_upstream(tmp_path, monkeypatch):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    config(tmp_path / "elsewhere", "id: core\n")
    monkeypatch.setenv("TCW_PROJECT_CORE", str(tmp_path / "elsewhere"))
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert Path(registry.get("core").locator) == (tmp_path / "elsewhere").resolve()


def test_an_absent_upstream_is_unreachable_not_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.check() == []
    assert "core" in [u.id for u in registry.unreachable()]


def test_nothing_beyond_an_upstream_is_loaded(tmp_path):
    """The upstream's own connections are not the reader's to load, check or
    write: a project reachable only beyond it never enters the reader's graph."""
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\nconnected-projects:\n  children:\n"
                               "    x: x\n")
    config(tmp_path / "core" / "x", "id: x\nconnected-projects:\n  parent:\n"
                                    "    core: ..\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.get("core") is not None
    assert registry.get("x") is None
    assert registry.check() == []


def test_a_broken_graph_beyond_an_upstream_does_not_block_the_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\nconnected-projects:\n  children:\n"
                               "    x: x\n  bogus: 1\n")
    config(tmp_path / "core" / "x", "id: x\n")            # names no parent
    assert FsProjectRegistry.open(tmp_path / "app").check() == []


def test_the_upstream_does_not_see_its_reader(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    core: ../core\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "core")
    assert registry.check() == []
    assert registry.get("app") is None


def test_an_upstream_reached_through_a_parent_is_found(tmp_path):
    """The proposit-app shape: a package reaches core through its parent."""
    config(tmp_path / "repo", "id: repo\nconnected-projects:\n  children:\n"
                               "    pkg: pkg\n  upstream:\n    core: ../core\n")
    config(tmp_path / "repo" / "pkg", "id: pkg\nconnected-projects:\n  parent:\n"
                                       "    repo: ..\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "repo" / "pkg")
    assert registry.check() == []
    assert registry.get("core") is not None


def test_checkout_of_finds_an_upstream_by_its_repository(tmp_path):
    url = "https://example.invalid/core.git"
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              f"    core:\n      path: ../core\n      repository:\n"
                              f"        url: {url}\n        ref: main\n")
    config(tmp_path / "core", "id: core\n")
    registry = FsProjectRegistry.open(tmp_path / "app")
    assert registry.checkout_of(url) == (tmp_path / "core").resolve()


# ── the write rule ───────────────────────────────────────────────────────────

def _family(tmp_path: Path) -> Path:
    """Root `r` with children `a` and `b`; `a` declares `core` upstream."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    a: a\n    b: b\n")
    config(tmp_path / "r" / "a", "id: a\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n  upstream:\n    core: ../../core\n")
    config(tmp_path / "r" / "b", "id: b\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n")
    config(tmp_path / "core", "id: core\n")
    return tmp_path / "r"


def test_an_upstream_is_read_only_from_its_declarer(tmp_path):
    root = _family(tmp_path)
    registry = FsProjectRegistry.open(root / "a")
    reason = registry.read_only_reason("core")
    assert reason is not None and "read-only" in reason and "'a'" in reason


def test_an_upstream_is_read_only_from_the_declarers_sibling_and_parent(tmp_path):
    """A narrower rule — "an upstream of this node or an ancestor" — lets both
    of these write into it."""
    root = _family(tmp_path)
    for node in (root / "b", root):
        registry = FsProjectRegistry.open(node)
        assert registry.check() == [], registry.check()
        assert registry.read_only_reason("core") is not None, node


def test_family_members_stay_writable(tmp_path):
    root = _family(tmp_path)
    registry = FsProjectRegistry.open(root / "b")
    for project_id in ("b", "r", "a"):
        assert registry.read_only_reason(project_id) is None, project_id


def test_the_upstream_writes_to_itself_from_its_own_checkout(tmp_path):
    _family(tmp_path)
    assert FsProjectRegistry.open(tmp_path / "core").read_only_reason("core") is None


# ── graph rules ──────────────────────────────────────────────────────────────

def test_a_self_upstream_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  upstream:\n"
                              "    app: .\n")
    assert any("own upstream" in p
               for p in FsProjectRegistry.open(tmp_path / "app").check())


def test_an_upstream_that_is_also_a_child_is_a_problem(tmp_path):
    config(tmp_path / "app", "id: app\nconnected-projects:\n  children:\n"
                              "    core: core\n  upstream:\n    core: core\n")
    config(tmp_path / "app" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                       "    app: ..\n")
    problems = FsProjectRegistry.open(tmp_path / "app").check()
    assert any("declared upstream" in p and "core" in p for p in problems), problems


def test_an_upstream_that_is_also_a_sibling_is_a_problem(tmp_path):
    """The migration's forbidden middle state: a package's parent declares core
    upstream while the root still lists core as a child."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    a: a\n    core: core\n")
    config(tmp_path / "r" / "a", "id: a\nconnected-projects:\n  parent:\n"
                                  "    r: ..\n  upstream:\n    core: ../core\n")
    config(tmp_path / "r" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                     "    r: ..\n")
    problems = FsProjectRegistry.open(tmp_path / "r" / "a").check()
    assert any("declared upstream" in p and "core" in p for p in problems), problems


def test_an_upstream_that_is_also_a_grandparent_is_a_problem(tmp_path):
    config(tmp_path / "gp", "id: gp\nconnected-projects:\n  children:\n    mid: mid\n")
    config(tmp_path / "gp" / "mid", "id: mid\nconnected-projects:\n  parent:\n"
                                     "    gp: ..\n  children:\n    kid: kid\n")
    config(tmp_path / "gp" / "mid" / "kid", "id: kid\nconnected-projects:\n"
                                             "  parent:\n    mid: ..\n"
                                             "  upstream:\n    gp: ../..\n")
    problems = FsProjectRegistry.open(tmp_path / "gp" / "mid" / "kid").check()
    assert any("declared upstream" in p and "'gp'" in p for p in problems), problems


def test_two_declarers_of_one_folder_are_one_project(tmp_path):
    root = _family(tmp_path)
    config(root / "b", "id: b\nconnected-projects:\n  parent:\n"
                        "    r: ..\n  upstream:\n    core: ../../core\n")
    assert FsProjectRegistry.open(root).check() == []


def test_two_declarers_of_different_folders_name_both(tmp_path):
    root = _family(tmp_path)
    config(tmp_path / "core2", "id: core\n")
    config(root / "b", "id: b\nconnected-projects:\n  parent:\n"
                        "    r: ..\n  upstream:\n    core: ../../core2\n")
    problems = FsProjectRegistry.open(root).check()
    duplicate = [p for p in problems if "duplicate project id 'core'" in p]
    assert duplicate and "'a'" in duplicate[0] and "'b'" in duplicate[0], problems


# ── migration ────────────────────────────────────────────────────────────────

def _moved_root(tmp_path: Path) -> Path:
    """Step 1 done: the root reads core as upstream; core still names it parent."""
    config(tmp_path / "r", "id: r\nconnected-projects:\n  upstream:\n"
                            "    core: core\n")
    config(tmp_path / "r" / "core", "id: core\nconnected-projects:\n  parent:\n"
                                     "    r: ..\n")
    return tmp_path / "r"


def test_a_parent_claim_answered_by_an_upstream_declaration_is_a_warning(tmp_path):
    root = _moved_root(tmp_path)
    for node in (root, root / "core"):
        registry = FsProjectRegistry.open(node)
        assert registry.check() == [], (node, registry.check())
        assert any("core" in w and "upstream" in w and "parent" in w
                   for w in registry.warnings()), (node, registry.warnings())


def test_the_reverse_migration_order_still_fails(tmp_path):
    config(tmp_path / "r", "id: r\nconnected-projects:\n  children:\n"
                            "    core: core\n")
    config(tmp_path / "r" / "core", "id: core\n")
    assert any("nonreciprocal connection" in p
               for p in FsProjectRegistry.open(tmp_path / "r").check())
