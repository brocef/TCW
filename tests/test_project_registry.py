from pathlib import Path

import pytest

from tcw.store.fs import init, write_sentinel
from tcw.store.project import FsProjectRegistry, validate_project_id


def config(root: Path, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(text, encoding="utf-8")


def reciprocal(parent: Path, parent_id: str, child: Path, child_id: str) -> None:
    config(
        parent,
        f"id: {parent_id}\nconnected-projects:\n  children:\n"
        f"    {child_id}: {child}\n",
    )
    config(
        child,
        f"id: {child_id}\nconnected-projects:\n  parent:\n"
        f"    {parent_id}: {parent}\n",
    )


@pytest.mark.parametrize(
    "value",
    ["Upper", "two_words", "-leading", "trailing-", "two--hyphens", "local", "active"],
)
def test_invalid_or_reserved_project_ids(value):
    with pytest.raises(ValueError):
        validate_project_id(value)


def test_arbitrary_absolute_layout_and_lookup(tmp_path):
    parent = tmp_path / "left" / "parent"
    child = tmp_path / "elsewhere" / "child"
    reciprocal(parent, "parent-project", child, "child-project")
    registry = FsProjectRegistry.open(parent).require_valid()
    assert registry.current.id == "parent-project"
    assert [p.id for p in registry.children()] == ["child-project"]
    assert registry.get("child-project").locator == child.resolve()


def test_relative_layout_and_transitive_descendants(tmp_path):
    root = tmp_path / "root"
    child = tmp_path / "child"
    deep = tmp_path / "deep"
    config(
        root,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    config(
        child,
        "id: child-project\nconnected-projects:\n"
        "  parent:\n    root-project: ../root\n"
        "  children:\n    deep-project: ../deep\n",
    )
    config(
        deep,
        "id: deep-project\nconnected-projects:\n  parent:\n"
        "    child-project: ../child\n",
    )
    registry = FsProjectRegistry.open(root).require_valid()
    assert [p.id for p in registry.descendants()] == [
        "child-project",
        "deep-project",
    ]
    assert [p.id for p in registry.ancestors("deep-project")] == [
        "child-project",
        "root-project",
    ]


@pytest.mark.parametrize(
    "target, expected",
    [
        ("id: child-wrong\n", "does not match target id"),
        ("", "missing project id"),
        ("id: child-project\nconnected-projects: []\n", "must be a mapping"),
    ],
)
def test_invalid_target_fails_closed(tmp_path, target, expected):
    root = tmp_path / "root"
    child = tmp_path / "child"
    config(
        root,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    config(child, target)
    problems = FsProjectRegistry.open(root).check()
    assert any(expected in problem for problem in problems)


def test_nonreciprocal_connection_fails(tmp_path):
    root = tmp_path / "root"
    child = tmp_path / "child"
    config(
        root,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    config(child, "id: child-project\n")
    assert any(
        "nonreciprocal connection" in problem
        for problem in FsProjectRegistry.open(root).check()
    )


def test_duplicate_yaml_key_fails(tmp_path):
    root = tmp_path / "root"
    config(root, "id: root-project\nid: duplicate\n")
    assert any("duplicate key" in p for p in FsProjectRegistry.open(root).check())


def test_unregistered_node_is_never_loaded(tmp_path, monkeypatch):
    root = tmp_path / "root"
    child = tmp_path / "child"
    decoy = tmp_path / "huge" / "decoy"
    reciprocal(root, "root-project", child, "child-project")
    config(decoy, "id: decoy-project\n")
    reads: list[Path] = []
    original = Path.read_text

    def tracked(path: Path, *args, **kwargs):
        if path.name == "tcw-config.yaml":
            reads.append(path.resolve())
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked)
    registry = FsProjectRegistry.open(root).require_valid()
    assert [p.id for p in registry.descendants()] == ["child-project"]
    assert decoy.resolve() / "tcw-config.yaml" not in reads
    assert reads.count(root.resolve() / "tcw-config.yaml") == 1
    assert reads.count(child.resolve() / "tcw-config.yaml") == 1


def test_init_backfills_and_preserves_config(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "tcw-config.yaml").write_text("work:\n  tags:\n    - docs\n")
    init(["work"], root, "repo-project")
    text = (root / "tcw-config.yaml").read_text()
    assert "id: repo-project" in text
    assert "tags:" in text and "- docs" in text


def test_conflicting_init_id_rejected(tmp_path):
    write_sentinel(tmp_path, "first-project")
    with pytest.raises(ValueError, match="conflicting"):
        init(["work"], tmp_path, "second-project")
