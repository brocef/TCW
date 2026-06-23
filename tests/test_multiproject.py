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
        init(["taxonomy", "capabilities"], root)     # writes sentinel + docs/
    return tmp_path


def _extend_b_onto_a(repo: Path) -> None:
    (repo / "project-b" / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"base": "../project-a"}}))


def test_extends_resolves_across_sibling_subfolders(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    node = find_node("taxonomy", repo / "project-b")     # detection finds project-b
    assert node == (repo / "project-b").resolve()
    term = FsTaxonomyStore.open(node).get("base/account")
    assert term is not None and term.name == "Account"


def test_capabilities_check_resolves_sibling_taxonomy(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    caps = FsCapabilitiesStore.open(repo / "project-b")
    caps.add("orders", "Place an order")
    caps.set("orders", {"Subject": "base/account"})
    node = find_node("capabilities", repo / "project-b")
    tax = FsTaxonomyStore.open(node)
    assert FsCapabilitiesStore.open(node).check(taxonomy=tax) == []
