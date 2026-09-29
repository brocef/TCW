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

