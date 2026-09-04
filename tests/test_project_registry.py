from pathlib import Path

import pytest

from tcw.store.fs import init, write_sentinel
from tcw.store.project import (
    FsProjectRegistry,
    validate_project_id,
    worktree_anchors,
)


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


# ── worktree anchors probe ───────────────────────────────────────────────


def _repo(path: Path) -> Path:
    import subprocess
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "seed"], check=True)
    return path


def test_worktree_anchors_inside_linked_worktree(tmp_path):
    import subprocess
    main = _repo(tmp_path / "main")
    wt = tmp_path / "wt"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", "-b", "f", str(wt)],
                   check=True)
    assert worktree_anchors(wt) == (wt.resolve(), main.resolve())


def test_worktree_anchors_handles_a_space_in_the_repo_path(tmp_path):
    """A path containing a space must not disable worktree resolution.

    `git rev-parse` emits one path per line, so the two lines must be split on
    newlines. Splitting on whitespace yields four tokens for `my repo`, trips the
    two-value guard, and returns None — silently reverting every command inside
    that worktree to the pre-fix failure. `~/My Drive`, `~/Google Drive` and
    `~/Library/Mobile Documents` all hit this, and no `tmp_path` fixture can see
    it because pytest's temp dirs never contain spaces.
    """
    import subprocess
    main = _repo(tmp_path / "my repo")
    wt = tmp_path / "my repo" / "a worktree"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", "-b", "f", str(wt)],
                   check=True)
    assert worktree_anchors(wt) == (wt.resolve(), main.resolve())


def test_worktree_anchors_primary_checkout_is_none(tmp_path):
    assert worktree_anchors(_repo(tmp_path / "main")) is None


def test_worktree_anchors_non_git_is_none(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert worktree_anchors(plain) is None


def test_worktree_anchors_bare_main_repo_is_none(tmp_path):
    import subprocess
    main = _repo(tmp_path / "main")
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(main), str(bare)], check=True)
    wt = tmp_path / "bare-wt"
    subprocess.run(["git", "-C", str(bare), "worktree", "add", "-q", str(wt), "main"],
                   check=True)
    assert worktree_anchors(wt) is None


def test_worktree_anchors_survives_missing_git(tmp_path, monkeypatch):
    import tcw.store.project as project_module

    def boom(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(project_module.subprocess, "run", boom)
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    assert worktree_anchors(nowhere) is None


def test_a_fresh_registry_reports_nothing_unreachable(tmp_path):
    root = tmp_path / "root"
    child = tmp_path / "child"
    reciprocal(root, "root-project", child, "child-project")
    registry = FsProjectRegistry.open(root)
    assert registry.unreachable() == []
    registry.require_valid()


def test_a_malformed_target_is_an_error_not_an_unreachable_edge(tmp_path):
    root = tmp_path / "root"
    child = tmp_path / "child"
    config(
        root,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    config(child, "id: child-project\nid: duplicate\n")
    registry = FsProjectRegistry.open(root)
    assert registry.unreachable() == []
    with pytest.raises(ValueError):
        registry.require_valid()


def test_an_absent_target_is_unreachable_not_a_problem(tmp_path):
    root = tmp_path / "root"
    config(
        root,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    registry = FsProjectRegistry.open(root)
    registry.require_valid()
    assert registry.check() == []
    assert [u.id for u in registry.unreachable()] == ["child-project"]
    assert registry.unreachable()[0].locator == (tmp_path / "child").resolve()
    assert registry.unreachable()[0].declared_in == (root / "tcw-config.yaml").resolve()
    assert registry.get("child-project") is None
    assert registry.children() == []


def test_an_absent_parent_leaves_the_child_usable(tmp_path):
    child = tmp_path / "a" / "b" / "child"
    config(
        child,
        "id: child-project\nconnected-projects:\n  parent:\n"
        "    root-project: ../../..\n",
    )
    registry = FsProjectRegistry.open(child)
    registry.require_valid()
    assert registry.current.id == "child-project"
    assert registry.parent() is None
    assert registry.unreachable_project("root-project") is not None
    assert registry.unreachable_project("nobody") is None


def test_an_absent_counterpart_does_not_disprove_reciprocity(tmp_path):
    """The parent is here and names its child at a path only another machine has."""
    parent = tmp_path / "orchestrator"
    child = tmp_path / "child"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: nested/child\n",
    )
    config(
        child,
        f"id: child-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {parent}\n",
    )
    registry = FsProjectRegistry.open(child)
    registry.require_valid()
    assert registry.parent().id == "root-project"


def test_a_present_counterpart_pointing_elsewhere_still_fails(tmp_path):
    parent = tmp_path / "orchestrator"
    child = tmp_path / "child"
    decoy = tmp_path / "decoy"
    config(decoy, "id: decoy-project\n")
    config(
        parent,
        f"id: root-project\nconnected-projects:\n  children:\n"
        f"    child-project: {decoy}\n",
    )
    config(
        child,
        f"id: child-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {parent}\n",
    )
    problems = FsProjectRegistry.open(child).check()
    assert any("does not point back to" in p for p in problems)


def test_a_correct_pair_still_validates(tmp_path):
    parent = tmp_path / "orchestrator"
    child = tmp_path / "child"
    reciprocal(parent, "root-project", child, "child-project")
    FsProjectRegistry.open(child).require_valid()
    FsProjectRegistry.open(parent).require_valid()


# ── connected-project repository declarations ────────────────────────────────


def test_a_mapping_entry_with_a_path_matches_the_bare_string_form(tmp_path):
    for style in ("bare", "mapping"):
        base = tmp_path / style
        parent, child = base / "orchestrator", base / "child"
        locator = "path: ../child" if style == "mapping" else "../child"
        entry = f"    child-project:\n      {locator}\n" if style == "mapping" \
            else f"    child-project: {locator}\n"
        config(parent, f"id: root-project\nconnected-projects:\n  children:\n{entry}")
        config(
            child,
            "id: child-project\nconnected-projects:\n  parent:\n"
            "    root-project: ../orchestrator\n",
        )
        registry = FsProjectRegistry.open(parent)
        registry.require_valid()
        assert [c.id for c in registry.children()] == ["child-project"]


def test_a_present_locator_wins_over_a_declaration(tmp_path, monkeypatch):
    """The declaration must not be consulted at all — its url is unreachable."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    parent, child = tmp_path / "orchestrator", tmp_path / "child"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project:\n      path: ../child\n"
        "      repository:\n        url: https://example.invalid/nope.git\n",
    )
    config(
        child,
        "id: child-project\nconnected-projects:\n  parent:\n"
        "    root-project: ../orchestrator\n",
    )
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert [c.id for c in registry.children()] == ["child-project"]


def test_a_declaration_answers_when_the_locator_does_not(tmp_path, monkeypatch):
    from tcw.store.base import RepositoryDeclaration
    from tcw.store.checkouts import provisioned_root

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    parent = tmp_path / "orchestrator"
    declaration = RepositoryDeclaration(url="https://example.invalid/child.git",
                                        ref="main")
    obtained = provisioned_root(parent, declaration)
    config(
        obtained,
        "id: child-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {parent}\n",
    )
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project:\n      path: ../child\n"
        "      repository:\n"
        "        url: https://example.invalid/child.git\n        ref: main\n",
    )
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert [c.id for c in registry.children()] == ["child-project"]
    assert registry.unreachable() == []


def test_an_unprovisioned_declaration_is_unreachable_at_its_locator(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    parent = tmp_path / "orchestrator"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project:\n      path: ../child\n"
        "      repository:\n        url: https://example.invalid/child.git\n",
    )
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    absent = registry.unreachable_project("child-project")
    assert absent is not None
    assert absent.locator == (tmp_path / "child").resolve()


@pytest.mark.parametrize(
    "entry, expected",
    [
        ("      nonsense: 1\n", "unknown key"),
        ("      path: ''\n", "expected a non-empty string"),
        ("      repository:\n        ref: main\n", "url: expected a non-empty string"),
        ("      repository:\n        url: u\n        path: /abs\n",
         "must be relative to the repository root"),
        ("      {}\n", "needs 'path', 'repository', or both"),
    ],
)
def test_a_malformed_entry_is_an_error_naming_the_line(tmp_path, entry, expected):
    parent = tmp_path / "orchestrator"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        f"    child-project:\n{entry}",
    )
    problems = FsProjectRegistry.open(parent).check()
    assert any(expected in problem for problem in problems), problems
    assert FsProjectRegistry.open(parent).unreachable() == []


def test_a_declared_project_says_to_provision_it(tmp_path, monkeypatch):
    from tcw.store.fs import unreachable_project_note

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    parent = tmp_path / "orchestrator"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project:\n      path: ../child\n"
        "      repository:\n        url: https://example.invalid/child.git\n",
    )
    registry = FsProjectRegistry.open(parent)
    note = unreachable_project_note(registry, "child-project")
    assert "https://example.invalid/child.git" in note
    assert "tcw provision" in note


def test_an_undeclared_absent_project_does_not_say_to_provision(tmp_path):
    from tcw.store.fs import unreachable_project_note

    parent = tmp_path / "orchestrator"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../child\n",
    )
    note = unreachable_project_note(FsProjectRegistry.open(parent), "child-project")
    assert "not reachable in this checkout" in note
    assert "tcw provision" not in note


def test_a_project_another_route_resolved_is_not_reported_unreachable(tmp_path):
    """Both sides declare the connection; only one side's locator resolves here.

    Routine in a multi-repository workspace, where the two configs were written
    against different machines. The project is in the graph, so nothing about it
    is unreachable.
    """
    parent = tmp_path / "orchestrator"
    child = tmp_path / "child"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: nested/child\n",          # not here
    )
    config(
        child,
        f"id: child-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {parent}\n",              # here
    )
    registry = FsProjectRegistry.open(child)
    registry.require_valid()
    assert registry.parent().id == "root-project"
    assert registry.unreachable() == []
    assert registry.unreachable_project("child-project") is None


def test_a_project_no_route_resolves_is_still_reported(tmp_path):
    child = tmp_path / "child"
    config(
        child,
        "id: child-project\nconnected-projects:\n  parent:\n"
        "    root-project: ../nowhere\n",
    )
    registry = FsProjectRegistry.open(child)
    registry.require_valid()
    assert [u.id for u in registry.unreachable()] == ["root-project"]
    assert registry.unreachable_project("root-project") is not None


def test_a_directory_that_is_not_a_node_is_still_refused(tmp_path):
    """The fail-open is argued for declared *targets*, not for the root.

    Recording nothing for a directory with no sentinel made `require_valid()`
    accept anything on the disk, and every helper built on it answer "no parent,
    no children, valid".
    """
    plain = tmp_path / "not-a-node"
    plain.mkdir()
    registry = FsProjectRegistry.open(plain)
    assert registry.check(), "a directory with no sentinel validated"
    with pytest.raises(ValueError):
        registry.require_valid()
