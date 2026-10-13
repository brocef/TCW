import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, find_node, init,
)


from nodeconfig import declare_extends


def _monorepo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for name in ("project-a", "project-b"):
        root = tmp_path / name
        root.mkdir()
        init(["taxonomy", "capabilities"], root, name)
    (tmp_path / "project-b" / "tcw-config.yaml").write_text(
        "id: project-b\nprojects:\n  children:\n"
        "    project-a: ../project-a\n"
    )
    (tmp_path / "project-a" / "tcw-config.yaml").write_text(
        "id: project-a\nprojects:\n  parent:\n"
        "    project-b: ../project-b\n"
    )
    return tmp_path


def _extend_b_onto_a(repo: Path) -> None:
    declare_extends(repo / "project-b", "taxonomy",
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
    a_doc["projects"] = {"children": {"b-project": "b"}}
    config(a, a_doc)
    config(b, {"id": "b-project",
               "projects": {"parent": {"a-project": ".."},
                                      "children": {"c-project": "c"}}})
    c_doc = yaml.safe_load((c / "tcw-config.yaml").read_text())
    c_doc["projects"] = {"parent": {"b-project": ".."}}
    config(c, c_doc)
    return a, b, c


def test_a_routing_node_is_a_legal_graph(tmp_path):
    from tcw.store.project import FsProjectRegistry

    a, b, c = _routing_graph(tmp_path)
    for root in (a, b, c):
        FsProjectRegistry.open(root).require_valid()


def _projects(monkeypatch, capsys, where):
    """`tcw projects list --json` run in `where`, as `{id: relation}`."""
    import json
    from tcw.cli import main

    monkeypatch.chdir(where)
    assert main(["projects", "list", "--json"]) == 0
    return {p["id"]: p["relation"] for p in json.loads(capsys.readouterr().out)["projects"]}


def test_a_registered_parent_that_keeps_no_board_is_listed(tmp_path, monkeypatch, capsys):
    a, b, c = _routing_graph(tmp_path)
    assert _projects(monkeypatch, capsys, c)["b-project"] == "parent"
    assert "parent" not in _projects(monkeypatch, capsys, a).values()


def test_a_registered_child_that_keeps_no_board_is_listed(tmp_path, monkeypatch, capsys):
    a, b, c = _routing_graph(tmp_path)
    assert _projects(monkeypatch, capsys, a)["b-project"] == "child"
    # Unlike 2.8's `tcw work nodes`, the routing project itself can be asked.
    assert _projects(monkeypatch, capsys, b)["c-project"] == "child"
    assert "child" not in _projects(monkeypatch, capsys, c).values()


# ── an unreachable relation is named, never erased ──────────────────────────

def _child_missing_its_parent(tmp_path):
    """A checkout holding only the child, whose config names an absent parent."""
    import subprocess
    import yaml
    from tcw.store.fs import init

    child = tmp_path / "child"
    child.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(child)], check=True)
    subprocess.run(["git", "-C", str(child), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(child), "config", "user.name", "t"], check=True)
    init(["work"], child, "child-project")
    doc = yaml.safe_load((child / "tcw-config.yaml").read_text())
    doc["projects"] = {"parent": {"away-project": str(tmp_path / "away")}}
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return child


def test_nodes_names_a_parent_this_checkout_does_not_have(tmp_path, monkeypatch,
                                                          capsys):
    """It printed `(none — root)` for a config that plainly names a parent —
    the confusion `child_nodes`' own comment forbids and README promises against."""
    from tcw.cli import main

    child = _child_missing_its_parent(tmp_path)
    assert _projects(monkeypatch, capsys, child)["away-project"] == "parent"


def test_nodes_names_a_child_this_checkout_does_not_have(tmp_path, monkeypatch,
                                                         capsys):
    import subprocess
    import yaml
    from tcw.cli import main
    from tcw.store.fs import init

    parent = tmp_path / "parent"
    parent.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(parent)], check=True)
    subprocess.run(["git", "-C", str(parent), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(parent), "config", "user.name", "t"], check=True)
    init(["work"], parent, "parent-project")
    doc = yaml.safe_load((parent / "tcw-config.yaml").read_text())
    doc["projects"] = {"children": {"away-project": str(tmp_path / "away")}}
    (parent / "tcw-config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))

    assert _projects(monkeypatch, capsys, parent)["away-project"] == "child"


