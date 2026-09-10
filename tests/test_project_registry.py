from pathlib import Path

import pytest

from tcw.store.base import ProjectOverride
from tcw.store.fs import init, write_sentinel
from tcw.store.project import (
    FsProjectRegistry,
    override_variable,
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
    ["Upper", "two_words", "-leading", "trailing-", "two--hyphens", "local", "active",
     # `a_b` and `A-b` are here for a second reason, and it is the one that
     # would be missed if they were ever pruned as duplicates of `two_words`
     # and `Upper`. `override_variable` maps an id to an environment variable by
     # uppercasing it and turning `-` into `_`, and that mapping is injective
     # only because an id can contain neither an underscore nor an uppercase
     # letter. Admit `a_b` and it collides with `a-b`; admit `A-b` and it
     # collides with `a-b`. The id pattern is what keeps two distinct projects
     # from claiming one variable, so it is tested as that guarantee.
     "a_b", "A-b"],
)
def test_invalid_or_reserved_project_ids(value):
    with pytest.raises(ValueError):
        validate_project_id(value)


def test_the_override_variable_name_follows_the_id():
    """The id, uppercased with `-` as `_` — node ids, never repository names.

    The distinction costs an hour when the two are crossed, which they are in
    the workspace that prompted this: the directory `proposit-orchestration`
    holds the node `proposit-app`, and the directory `proposit-app` holds the
    node `proposit-app-repo`.
    """
    assert override_variable("proposit-core") == "TCW_PROJECT_PROPOSIT_CORE"
    assert override_variable("proposit-app") == "TCW_PROJECT_PROPOSIT_APP"
    assert override_variable("proposit-app-repo") == "TCW_PROJECT_PROPOSIT_APP_REPO"
    assert override_variable("a") == "TCW_PROJECT_A"


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


# ── a declared relation this checkout does not have ─────────────────────────

def test_a_declared_parent_that_is_absent_is_still_a_declared_parent(tmp_path):
    """`parent()` answers with a Project, so it can only answer for a project
    this checkout has — which made "declared but not here" indistinguishable from
    "never declared", the one thing `UnreachableProject` exists to prevent."""
    child = tmp_path / "child"
    config(child, "id: child-project\nconnected-projects:\n  parent:\n"
                  f"    away-project: {tmp_path / 'away'}\n")
    registry = FsProjectRegistry.open(child).require_valid()
    assert registry.parent() is None
    assert registry.declared_parent_id() == "away-project"
    assert [u.id for u in registry.unreachable()] == ["away-project"]


def test_a_declared_child_that_is_absent_is_still_a_declared_child(tmp_path):
    parent = tmp_path / "parent"
    config(parent, "id: parent-project\nconnected-projects:\n  children:\n"
                   f"    away-project: {tmp_path / 'away'}\n")
    registry = FsProjectRegistry.open(parent).require_valid()
    assert registry.children() == []
    assert registry.declared_child_ids() == ["away-project"]


def test_a_locator_that_misses_a_project_the_graph_has_is_reported(tmp_path):
    """The typo nothing reported: reciprocity abstains on an absent target, and
    `unreachable()` filters the entry out because the project is in the graph
    via the other route. It is equally the shape of a locator that is right for
    another machine, so it is reported and not called a problem."""
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    config(parent, "id: parent-project\nconnected-projects:\n  children:\n"
                   f"    child-project: {child}\n")
    config(child, "id: child-project\nconnected-projects:\n  parent:\n"
                  f"    parent-project: {tmp_path / 'TYPO-parent'}\n")

    registry = FsProjectRegistry.open(parent)
    assert registry.check() == []                 # not a problem, deliberately
    assert registry.unreachable() == []           # the project is here
    misdirected = registry.misdirected()
    assert [entry.id for entry in misdirected] == ["parent-project"]
    assert str(misdirected[0].locator).endswith("TYPO-parent")


def test_a_locator_that_resolves_is_never_misdirected(tmp_path):
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    reciprocal(parent, "parent-project", child, "child-project")
    assert FsProjectRegistry.open(parent).misdirected() == []
    assert FsProjectRegistry.open(child).misdirected() == []


def test_a_graph_with_no_override_reports_none(tmp_path):
    """`overrides()` answers, and answers empty, without any adapter opting in.

    The default on `ProjectRegistry` is concrete rather than abstract precisely
    so this holds for a store that has no override mechanism at all — a caller
    may always ask, and no existing adapter had to change to be asked.
    """
    parent, child = tmp_path / "orchestrator", tmp_path / "child"
    reciprocal(parent, "root-project", child, "child-project")
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert registry.overrides() == []


# --- Rule 0: the environment says where a project is on this machine ----------
#
# Each test below sets the variable explicitly and builds its own layout. There
# is no helper defaulting a rung, deliberately: the resolution ladder is exactly
# what these tests branch on, and a fixture that quietly fixed one axis is how
# the store-provisioning epic left cells no test could reach.


def _decoy_layout(tmp_path):
    """A parent whose declared locator resolves to a *different existing node*.

    The motivating case, and the one no lower rung can fix: the locator is not
    absent, it is wrong, and it lands on a real node with another id.

    Returns `(parent, real, decoy)`.
    """
    parent, real, decoy = tmp_path / "orchestrator", tmp_path / "real", tmp_path / "decoy"
    config(
        parent,
        "id: root-project\nconnected-projects:\n  children:\n"
        "    child-project: ../decoy\n",
    )
    config(decoy, "id: decoy-project\n")
    config(
        real,
        "id: child-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {parent}\n",
    )
    return parent, real, decoy


def test_without_an_override_a_locator_on_the_wrong_node_is_an_error(tmp_path):
    """The state the override exists to correct — asserted so the next test
    cannot pass by resolving something that was never broken."""
    parent, _real, _decoy = _decoy_layout(tmp_path)
    registry = FsProjectRegistry.open(parent)
    assert any("does not match target id 'decoy-project'" in p
               for p in registry.check())
    assert registry.get("child-project") is None


def test_an_override_beats_a_locator_that_resolves_elsewhere(tmp_path, monkeypatch):
    """Rule 0 beats rule 1, not merely rule 2 (criterion 1).

    An override that only won where the locator was absent would leave the
    motivating case exactly as broken as it was.
    """
    parent, real, _decoy = _decoy_layout(tmp_path)
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", str(real))
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert Path(registry.get("child-project").locator) == real.resolve()
    assert [c.id for c in registry.children()] == ["child-project"]
    assert registry.overrides() == [
        ProjectOverride(id="child-project", source="TCW_PROJECT_CHILD_PROJECT",
                        locator=real.resolve()),
    ]


def test_an_override_at_an_absent_path_falls_through_to_the_declaration(
        tmp_path, monkeypatch):
    """Absent is not wrong (criterion 4).

    This is what lets one set of variables be configured once for an
    environment and used by sessions holding different subsets of the graph: a
    variable naming a project this machine does not have must behave exactly as
    no variable at all.
    """
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
        "    child-project:\n      path: ../child\n      repository:\n"
        "        url: https://example.invalid/child.git\n        ref: main\n",
    )
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", str(tmp_path / "not-here"))
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert registry.check() == []
    assert [c.id for c in registry.children()] == ["child-project"]
    assert registry.unreachable() == []
    # Nothing took effect, so nothing is listed — which is what makes a
    # mistyped variable conspicuous by its absence from `tcw validate`.
    assert registry.overrides() == []


def test_an_override_at_a_directory_that_is_not_a_node_is_a_problem(
        tmp_path, monkeypatch):
    """Present and wrong fails loudly, and does not fall through (criterion 5).

    The fail-open shape this refuses: a mistyped variable landing on a real
    directory, silently ignored, produces "my override does nothing" with
    nothing to read.
    """
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
        "    child-project:\n      path: ../child\n      repository:\n"
        "        url: https://example.invalid/child.git\n        ref: main\n",
    )
    not_a_node = tmp_path / "empty"
    not_a_node.mkdir()
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", str(not_a_node))
    registry = FsProjectRegistry.open(parent)
    problems = registry.check()
    assert len(problems) == 1
    assert "TCW_PROJECT_CHILD_PROJECT" in problems[0]
    assert str(not_a_node.resolve()) in problems[0]
    with pytest.raises(ValueError):
        registry.require_valid()
    # It does NOT fall through: the provisioned copy is right there and is not
    # used. Refusing and then quietly using the declaration anyway would make
    # the message a lie.
    assert registry.get("child-project") is None


def test_an_override_naming_the_wrong_node_names_both_ids(tmp_path, monkeypatch):
    """Criterion 6 — the likely mistake is the wrong sibling in a workspace of
    similar directories, so the message has to say which one it found."""
    parent, _real, decoy = _decoy_layout(tmp_path)
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", str(decoy))
    registry = FsProjectRegistry.open(parent)
    problems = registry.check()
    assert any("child-project" in p and "decoy-project" in p for p in problems)
    with pytest.raises(ValueError):
        registry.require_valid()
    # Listed even though it is wrong, so `tcw validate` can print the override
    # beside the mismatch. Otherwise the error names a path the reader cannot
    # find in any config.
    assert [o.source for o in registry.overrides()] == ["TCW_PROJECT_CHILD_PROJECT"]


@pytest.mark.parametrize("value", ["", "   "])
def test_an_empty_override_variable_does_not_adopt_the_working_directory(
        tmp_path, monkeypatch, value):
    """`FOO=` names no path, and must not be read as one.

    The failure this guards is specific and silent. `Path("")` is `Path(".")`,
    so an unguarded empty value resolves to the process's working directory —
    and if the command happens to be run from a directory that *is* a node with
    the right id, the override silently takes effect from a variable the user
    deliberately blanked. So the test runs from exactly such a directory: if the
    guard goes, `overrides()` is no longer empty.
    """
    parent, real, _decoy = _decoy_layout(tmp_path)
    monkeypatch.chdir(real)                       # a real node for this very id
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", value)
    registry = FsProjectRegistry.open(parent)
    assert registry.overrides() == []
    assert any("does not match target id 'decoy-project'" in p
               for p in registry.check())


def test_an_override_value_survives_stray_surrounding_whitespace(
        tmp_path, monkeypatch):
    """A path exported with a trailing space is the path, not a missing one.

    The same strip as the guard above, in the direction where dropping it fails
    open rather than closed: the value would name a directory that is not there,
    and absent-is-not-wrong would silently carry on to the declaration.
    """
    parent, real, _decoy = _decoy_layout(tmp_path)
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", f"  {real}  ")
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert Path(registry.get("child-project").locator) == real.resolve()


def test_the_override_is_probed_once_per_project(tmp_path, monkeypatch):
    """The reciprocity walk re-enters `_target_path` for every edge.

    Without memoisation each pass re-probes the disk and re-appends to the
    override list, so `overrides()` grows with the graph's edge count. That
    fails silently — the graph still resolves — which is why it is asserted
    rather than left to review.
    """
    import tcw.store.project as project_module

    parent, real, _decoy = _decoy_layout(tmp_path)
    monkeypatch.setenv("TCW_PROJECT_CHILD_PROJECT", str(real))
    calls: list[str] = []
    real_mapping = project_module.override_variable

    def counting(project_id: str) -> str:
        calls.append(project_id)
        return real_mapping(project_id)

    monkeypatch.setattr(project_module, "override_variable", counting)
    registry = FsProjectRegistry.open(parent)
    registry.require_valid()
    assert calls.count("child-project") == 1
    assert len(registry.overrides()) == 1


# ── locating a project by the repository it comes from ───────────────────────
#
# The question the store-resolution ladder asks when its configured path does
# not resolve: *is a checkout of this repository already on this disk?* The
# registry is the only thing that knows, because it is the only thing that has
# consulted `TCW_PROJECT_<ID>`.


def _workspace(tmp_path: Path, url: str, *, parent_at: str = "orchestration") -> tuple[Path, Path]:
    """A child declaring its parent, and naming the repository the parent is a
    checkout of. Returns `(child_root, parent_root)`.

    Every axis the lookup branches on is written here rather than defaulted:
    the declared locator, the repository url, and where the parent actually is.
    """
    parent = tmp_path / parent_at
    child = tmp_path / "core"
    config(parent, f"id: orchestration\nconnected-projects:\n  children:\n    core: {child}\n")
    config(
        child,
        "id: core\n"
        "connected-projects:\n"
        "  parent:\n"
        "    orchestration:\n"
        f"      path: {parent}\n"
        "      repository:\n"
        f"        url: {url}\n"
        "        ref: main\n",
    )
    return child, parent


def test_checkout_of_finds_a_project_declared_from_that_repository(tmp_path):
    url = "https://github.invalid/acme/orchestration.git"
    child, parent = _workspace(tmp_path, url)

    registry = FsProjectRegistry.open(child)

    assert registry.checkout_of(url) == parent.resolve()


@pytest.mark.parametrize("asked", [
    "https://github.invalid/acme/orchestration",
    "https://github.invalid/acme/orchestration/",
    "git@github.invalid:acme/orchestration.git",
])
def test_checkout_of_matches_across_url_spellings(tmp_path, asked):
    """The two sides of a connection are written at different times by
    different people, so one spelling is not a safe assumption."""
    child, parent = _workspace(tmp_path, "https://github.invalid/acme/orchestration.git")

    assert FsProjectRegistry.open(child).checkout_of(asked) == parent.resolve()


def test_checkout_of_returns_none_for_an_unrelated_repository(tmp_path):
    child, _parent = _workspace(tmp_path, "https://github.invalid/acme/orchestration.git")

    registry = FsProjectRegistry.open(child)

    assert registry.checkout_of("https://github.invalid/acme/something-else.git") is None


def test_checkout_of_follows_an_override(tmp_path, monkeypatch):
    """The whole point of the item this exists for.

    The declared locator is right for the nested layout and wrong here; the
    environment says where the parent actually is. A lookup that read the
    declaration instead of the resolved project would answer with a directory
    this machine does not have.
    """
    url = "https://github.invalid/acme/orchestration.git"
    child, declared = _workspace(tmp_path, url)
    elsewhere = tmp_path / "flat" / "orchestration"
    config(elsewhere, f"id: orchestration\nconnected-projects:\n  children:\n    core: {child}\n")
    monkeypatch.setenv("TCW_PROJECT_ORCHESTRATION", str(elsewhere))

    found = FsProjectRegistry.open(child).checkout_of(url)

    assert found == elsewhere.resolve()
    assert found != declared.resolve(), "the declared locator must not win over the override"


def test_checkout_of_ignores_a_project_the_graph_does_not_hold(tmp_path):
    """A declaration whose target is not on this machine names a repository but
    no location. Answering with a path that is not there would send the store
    ladder somewhere worse than nowhere."""
    url = "https://github.invalid/acme/orchestration.git"
    child = tmp_path / "core"
    config(
        child,
        "id: core\n"
        "connected-projects:\n"
        "  parent:\n"
        "    orchestration:\n"
        f"      path: {tmp_path / 'not-here'}\n"
        "      repository:\n"
        f"        url: {url}\n"
        "        ref: main\n",
    )

    assert FsProjectRegistry.open(child).checkout_of(url) is None
