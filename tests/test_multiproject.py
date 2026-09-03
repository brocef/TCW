import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, find_node, init,
)


def _monorepo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for name in ("project-a", "project-b"):
        root = tmp_path / name
        root.mkdir()
        init(["taxonomy", "capabilities"], root, name)
    (tmp_path / "project-b" / "tcw-config.yaml").write_text(
        "id: project-b\nconnected-projects:\n  children:\n"
        "    project-a: ../project-a\n"
    )
    (tmp_path / "project-a" / "tcw-config.yaml").write_text(
        "id: project-a\nconnected-projects:\n  parent:\n"
        "    project-b: ../project-b\n"
    )
    return tmp_path


def _extend_b_onto_a(repo: Path) -> None:
    (repo / "project-b" / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": ["project-a"]}))


def test_extends_resolves_across_sibling_subfolders(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    node = find_node("taxonomy", repo / "project-b")     # detection finds project-b
    assert node == (repo / "project-b").resolve()
    term = FsTaxonomyStore.open(node).get("project-a/account")
    assert term is not None and term.name == "Account"


def test_capabilities_check_resolves_sibling_taxonomy(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    caps = FsCapabilitiesStore.open(repo / "project-b")
    caps.add("orders", "Place an order")
    caps.set("orders", {"Subject": "project-a/account"})
    node = find_node("capabilities", repo / "project-b")
    tax = FsTaxonomyStore.open(node)
    assert FsCapabilitiesStore.open(node).check(taxonomy=tax) == []


# ── a routing node: registered, keeps no board ───────────────────────────────


def _routing_graph(tmp_path):
    """A → B → C where B is registered and keeps no work store.

    A repository root that groups packages owning the boards. Every connection
    is reciprocal and `tcw validate` is clean, so the shape is legal today — the
    defect this guards is behavioral, not a rejected configuration.
    """
    import subprocess
    import yaml
    from tcw.store.fs import init, write_sentinel

    def git(path):
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)

    a = tmp_path / "a"
    b = tmp_path / "a" / "b"
    c = tmp_path / "a" / "b" / "c"
    for d in (a, b, c):
        d.mkdir(parents=True, exist_ok=True)
    git(a)
    init(["work"], a, "a-project")
    write_sentinel(b, "b-project")
    init(["work"], c, "c-project")

    def config(path, doc):
        (path / "tcw-config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))

    a_doc = yaml.safe_load((a / "tcw-config.yaml").read_text())
    a_doc["connected-projects"] = {"children": {"b-project": "b"}}
    config(a, a_doc)
    config(b, {"id": "b-project",
               "connected-projects": {"parent": {"a-project": ".."},
                                      "children": {"c-project": "c"}}})
    c_doc = yaml.safe_load((c / "tcw-config.yaml").read_text())
    c_doc["connected-projects"] = {"parent": {"b-project": ".."}}
    config(c, c_doc)
    return a, b, c


def test_a_routing_node_is_a_legal_graph(tmp_path):
    from tcw.store.project import FsProjectRegistry

    a, b, c = _routing_graph(tmp_path)
    for root in (a, b, c):
        FsProjectRegistry.open(root).require_valid()


def test_an_epic_two_levels_up_resolves_through_a_routing_node(tmp_path):
    from tcw.store.fs import FsWorkStore

    a, b, c = _routing_graph(tmp_path)
    top = FsWorkStore.open(a)
    epic = top.create("Cross-package epic", created="2026-01-01")
    top.set_field(epic.slug, "type", "epic")

    leaf = FsWorkStore.open(c)
    slice_ = leaf.create("A slice", created="2026-01-01")
    leaf.set_field(slice_.slug, "initiative", epic.slug)

    found = FsWorkStore.open(c).initiative_epic(
        FsWorkStore.open(c).get(slice_.slug))
    assert found is not None and found.slug == epic.slug


def test_initiative_children_crosses_a_routing_node(tmp_path):
    from tcw.store.fs import FsWorkStore

    a, b, c = _routing_graph(tmp_path)
    top = FsWorkStore.open(a)
    epic = top.create("Cross-package epic", created="2026-01-01")
    top.set_field(epic.slug, "type", "epic")
    leaf = FsWorkStore.open(c)
    slice_ = leaf.create("A slice", created="2026-01-01")
    leaf.set_field(slice_.slug, "initiative", epic.slug)

    slugs = [i.slug for i in FsWorkStore.open(a).initiative_children(epic.slug)]
    assert slugs == [slice_.slug]


def test_escalate_reaches_the_nearest_board_bearing_ancestor(tmp_path):
    from tcw.store.fs import FsWorkStore
    from tcw.work.recursion import escalate

    a, b, c = _routing_graph(tmp_path)
    escalate(c, "Something for the top")
    inbox = FsWorkStore.open(a).root / "inbox"
    assert [p.name for p in inbox.iterdir() if p.suffix == ".md"]


def test_escalate_with_no_board_bearing_ancestor_says_so(tmp_path):
    """Registered ancestry, none of it keeping a board — not the same as being
    the root, and it used to be reported as if it were."""
    import subprocess
    import pytest as _pytest
    import yaml
    from tcw.store.fs import init, write_sentinel
    from tcw.work.recursion import escalate

    root = tmp_path / "root"
    child = tmp_path / "root" / "child"
    child.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, "root-project")
    init(["work"], child, "child-project")
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(
        {"id": "root-project",
         "connected-projects": {"children": {"child-project": "child"}}},
        sort_keys=False))
    child_doc = yaml.safe_load((child / "tcw-config.yaml").read_text())
    child_doc["connected-projects"] = {"parent": {"root-project": ".."}}
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(child_doc, sort_keys=False))

    with _pytest.raises(ValueError) as excinfo:
        escalate(child, "Nowhere to go")
    message = str(excinfo.value)
    assert "no registered ancestor keeps a work store" in message
    assert "this is the root" not in message


def test_nodes_reports_a_registered_parent_that_keeps_no_board(tmp_path, monkeypatch, capsys):
    from tcw.cli import main

    a, b, c = _routing_graph(tmp_path)
    monkeypatch.chdir(c)
    assert main(["work", "nodes"]) == 0
    out = capsys.readouterr().out
    # Two spaces before the marker, the same spacing the children lines use —
    # the parent branch used to hardcode its own note with one.
    assert "parent: b-project  (no work store)" in out

    monkeypatch.chdir(a)
    assert main(["work", "nodes"]) == 0
    assert "parent: (none — root)" in capsys.readouterr().out


def test_nodes_lists_a_registered_child_that_keeps_no_board(tmp_path, monkeypatch, capsys):
    from tcw.cli import main

    a, b, c = _routing_graph(tmp_path)

    monkeypatch.chdir(a)
    assert main(["work", "nodes"]) == 0
    out = capsys.readouterr().out
    assert "children:" in out
    assert "b-project  (no work store)" in out
    assert "(none — leaf)" not in out

    # `tcw work nodes` is a work subcommand and refuses at a node with no work
    # store, so the routing node itself cannot be queried. Recorded rather than
    # asserted away: it is existing behaviour and out of this item's scope.
    monkeypatch.chdir(b)
    assert main(["work", "nodes"]) == 1

    monkeypatch.chdir(c)
    assert main(["work", "nodes"]) == 0
    assert "children: (none — leaf)" in capsys.readouterr().out


def test_the_parent_marker_says_which_reason_applies(tmp_path, monkeypatch, capsys):
    """A declared-but-unobtained board is not the same as no board at all.

    The children lines have distinguished the two since they were added; the
    parent line hardcoded "no work store" and so reported the wrong reason for a
    parent whose board this machine simply has not fetched.
    """
    import subprocess
    import yaml
    from tcw.cli import main
    from tcw.store.fs import init

    parent = tmp_path / "parent"
    child = tmp_path / "parent" / "child"
    child.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(parent)], check=True)
    subprocess.run(["git", "-C", str(parent), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(parent), "config", "user.name", "t"], check=True)
    init(["work"], parent, "parent-project")
    init(["work"], child, "child-project")

    # The parent's board is declared and not here.
    doc = yaml.safe_load((parent / "tcw-config.yaml").read_text())
    doc["connected-projects"] = {"children": {"child-project": "child"}}
    doc.setdefault("work", {})["path"] = str(tmp_path / "absent")
    doc["work"]["repository"] = {"url": "https://example.invalid/boards.git"}
    (parent / "tcw-config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    child_doc = yaml.safe_load((child / "tcw-config.yaml").read_text())
    child_doc["connected-projects"] = {"parent": {"parent-project": ".."}}
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(child_doc, sort_keys=False))

    monkeypatch.chdir(child)
    assert main(["work", "nodes"]) == 0
    out = capsys.readouterr().out
    assert "parent: parent-project  (work store not provisioned here)" in out
