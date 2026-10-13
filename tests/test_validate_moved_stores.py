"""`tcw validate` finds a taxonomy or capabilities store where it really is
(spec: 2026-09-21-make-tcw-validate-check-taxonomy-and-capabilities-stores-moved-by-their-path-setting)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tcw.validate import validate
from nodeconfig import set_component_key


def repo(root: Path, name: str = "node") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)
    return root


def term(store: Path, slug: str, **meta) -> None:
    d = store / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.yaml").write_text(yaml.safe_dump({"name": slug, "relatesTo": [], **meta}))
    (d / "description.md").write_text("")


def cap(store: Path, path: str, **meta) -> None:
    d = store / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.yaml").write_text(yaml.safe_dump(
        {"id": "cap-" + path.replace("/", "-"), "name": path, **meta}))
    (d / "description.md").write_text("")


def moved(tmp_path: Path, component: str, folder: str = "moved") -> tuple[Path, Path]:
    """A node whose `component` store lives at `<node>/<folder>` and nowhere else."""
    root = repo(tmp_path / "node")
    store = root / folder
    store.mkdir()
    (store / ".gitkeep").touch()
    set_component_key(root, component, "path", folder)
    return root, store


def check_lines(findings, component: str, root: Path) -> list[str]:
    """The error findings `component` is answerable for, as text: its store
    could not open or its `path` is wrong (the message names the component),
    or the finding is about a file inside the store wherever it resolved."""
    from tcw.store.fs import STORE_CLASSES
    try:
        store = STORE_CLASSES[component].open(root).root.resolve()
    except ValueError:
        store = None
    mine = []
    for f in findings:
        named = f.message.startswith((f"{component}:", f"{component}.path:"))
        inside = store is not None and (root / f.where).resolve().is_relative_to(store)
        if f.severity == "error" and (named or inside):
            mine.append(str(f))
    return mine


# ── criteria 1-3: a moved store is checked and scanned ───────────────────────

def test_a_moved_taxonomy_is_checked(tmp_path):
    root, store = moved(tmp_path, "taxonomy")
    term(store, "payment", relatesTo=["invoice"])            # dangling
    lines = check_lines(validate(root), "taxonomy", root)
    assert any("invoice" in p for p in lines), lines


def test_a_moved_taxonomy_is_scanned_for_yaml(tmp_path):
    root, store = moved(tmp_path, "taxonomy")
    (store / "broken").mkdir()
    (store / "broken" / "meta.yaml").write_text("name: [unclosed\n")
    problems = validate(root)
    assert any(p.where == "moved/broken/meta.yaml" for p in problems), problems


def test_a_moved_capabilities_store_is_checked(tmp_path):
    root, store = moved(tmp_path, "capabilities")
    cap(store, "x", Status="Bogus")
    lines = check_lines(validate(root), "capabilities", root)
    assert any("Bogus" in p for p in lines), lines


# ── criterion 4: capabilities see a moved taxonomy ──────────────────────────

def test_a_capability_subject_is_checked_against_a_moved_taxonomy(tmp_path, monkeypatch, capsys):
    root, tax = moved(tmp_path, "taxonomy", "tax")
    term(tax, "user")
    caps = root / "docs" / "capabilities"
    cap(caps, "x", Status="Supported", Subject=["user", "ghost"])

    problems = [p.message for p in FsCapabilitiesStore.open(root).check()]
    assert any("Subject" in p and "ghost" in p for p in problems), problems
    assert any("ghost" in p for p in check_lines(validate(root), "capabilities", root))

    monkeypatch.chdir(root)
    assert main(["capabilities", "set", "x", "--field", "Subject=nobody"]) == 2
    assert "nobody" in capsys.readouterr().err


# ── criterion 5: a broken taxonomy.path is a problem, not a traceback ────────

def test_a_missing_taxonomy_path_is_listed_not_raised(tmp_path):
    root = repo(tmp_path / "node")
    for tree in ("taxonomy", "capabilities"):
        (root / "docs" / tree).mkdir(parents=True)
    set_component_key(root, "taxonomy", "path", "nowhere")
    cap(root / "docs" / "capabilities", "x", Status="Supported", Subject=["user"])
    problems = validate(root)                      # raised StoreLocationUnusable
    assert any("nowhere" in p for p in check_lines(problems, "taxonomy", root)), problems
    assert any("nowhere" in p for p in check_lines(problems, "capabilities", root)), problems


# ── criterion 6: nodes without a tree store are untouched ────────────────────

@pytest.mark.parametrize("config", [
    {},                                             # nothing configured, no folders
    {"taxonomy": {"extends": []}},                  # extends only
])
def test_a_node_without_tree_stores_reports_nothing_new(tmp_path, config):
    root = repo(tmp_path / "node")
    for component, section in config.items():
        for key, value in section.items():
            set_component_key(root, component, key, value)
    assert validate(root) == []


# ── criterion 8: a shared store is reported by each project ──────────────────

def test_a_store_shared_by_two_projects_is_reported_by_each(tmp_path, monkeypatch, capsys):
    """Each project's own run reports the shared store's problem (TCW-73
    Design 6: `validate` checks the current project only)."""
    parent = repo(tmp_path / "parent", "parent")
    child = repo(tmp_path / "child", "child")
    (parent / "tcw-config.yaml").write_text(
        "id: parent\nconnected-projects:\n  children:\n    child: ../child\n")
    (child / "tcw-config.yaml").write_text(
        "id: child\nconnected-projects:\n  parent:\n    parent: ../parent\n")
    shared = tmp_path / "shared"
    shared.mkdir()
    term(shared, "payment", relatesTo=["invoice"])
    for root in (parent, child):
        set_component_key(root, "taxonomy", "path", str(shared))
    for root in (parent, child):
        monkeypatch.chdir(root)
        assert main(["validate"]) == 1
        out = capsys.readouterr().out
        reported = [line for line in out.splitlines() if "invoice" in line]
        assert len(reported) == 1, out


# ── review findings: nothing that used to be reported goes quiet ──────────────

def test_an_unopenable_taxonomy_costs_only_the_subject_checks(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path / "node")
    cap(root / "docs" / "capabilities", "x", Status="Bogus", Subject=["user"])
    cap(root / "docs" / "capabilities", "y", Status="Bogus", Feature="login")
    set_component_key(root, "taxonomy", "path", "nowhere")
    problems = [str(f) for f in FsCapabilitiesStore.open(root).check()]
    assert any("Bogus" in p for p in problems), problems
    unchecked = [p for p in problems if "Subject and Feature not checked" in p]
    assert len(unchecked) == 1 and "nowhere" in unchecked[0], problems


def test_nothing_is_said_unchecked_when_no_capability_names_a_subject(tmp_path):
    root = repo(tmp_path / "node")
    cap(root / "docs" / "capabilities", "x", Status="Supported")
    set_component_key(root, "taxonomy", "path", "nowhere")
    assert FsCapabilitiesStore.open(root).check() == []


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_broken_extends_without_a_local_tree_is_reported(tmp_path, component):
    root = repo(tmp_path / "node")
    set_component_key(root, component, "extends", ["ghost"])
    lines = check_lines(validate(root), component, root)
    assert any("ghost" in p for p in lines), lines


def test_a_work_only_node_reports_nothing_new(tmp_path):
    from tcw.store.fs import init
    root = repo(tmp_path / "node")
    init(["work"], root)
    assert validate(root) == []


