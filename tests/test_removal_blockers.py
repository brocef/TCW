"""A removal is refused while anything below the folder is an object of any
store, or a TCW 3.x one, wherever it is (TCW-111 Design 2.5, review decision
16; AC 17a). The search is the folder's own, not the walk's, so hidden
folders and `resources/` are searched too, as `git rm -rf` would delete them."""

from __future__ import annotations

import hashlib

import pytest

from tests.objectcli import obj, project, store, tcw  # noqa: F401
from tests.statefiles import write_state


@pytest.fixture
def demo(tmp_path):
    return project(tmp_path, work={})


def tree_hash(root) -> str:
    h = hashlib.sha256()
    for f in sorted((root / "docs").rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(root)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def test_a_term_with_a_3x_folder_below_it_names_tcw_migrate(tcw, demo):
    term = obj(demo, "taxonomy", "invoice", name="Invoice")
    (term / "old").mkdir()
    (term / "old" / "meta.yaml").write_text("name: Old\n")
    before = tree_hash(demo)
    removed = tcw(["taxonomy", "rm", "invoice"], demo)
    assert removed.code == 3, removed
    assert removed.err == ("tcw taxonomy rm: cannot remove 'invoice': invoice/old holds "
                           "a TCW 3.x meta.yaml; run 'tcw migrate' in this project "
                           "first\n")
    assert tree_hash(demo) == before


def test_a_capability_with_a_3x_folder_below_it_names_tcw_migrate(tcw, demo):
    cap = obj(demo, "capabilities", "cli/x", name="X", Status="Missing")
    (cap / "old").mkdir()
    (cap / "old" / "item.yaml").write_text("title: Old\n")
    before = tree_hash(demo)
    removed = tcw(["capabilities", "rm", "cli/x"], demo)
    assert removed.code == 3, removed
    assert removed.err == ("tcw capabilities rm: cannot remove 'cli/x': cli/x/old holds "
                           "a TCW 3.x item.yaml; run 'tcw migrate' in this project "
                           "first\n")
    assert tree_hash(demo) == before


@pytest.mark.parametrize("below", [".drafts/y", "resources/sample"])
def test_a_capability_with_an_object_below_it_anywhere(tcw, demo, below):
    cap = obj(demo, "capabilities", "cli/x", name="X", Status="Missing")
    write_state(cap / below / "tcw-capability.yaml", "name: Y\n")
    before = tree_hash(demo)
    removed = tcw(["capabilities", "rm", "cli/x"], demo)
    assert removed.code == 3, removed
    assert "nested under it" in removed.err and f"cli/x/{below}" in removed.err
    assert tree_hash(demo) == before


def test_a_state_file_of_another_store_blocks_too(tcw, demo):
    term = obj(demo, "taxonomy", "invoice", name="Invoice")
    write_state(term / "resources" / "x" / "tcw-work-item.yaml", "title: x\nstage: plan\n")
    assert tcw(["taxonomy", "rm", "invoice"], demo).code == 3


def test_with_nothing_below_both_removals_succeed(tcw, demo):
    term = obj(demo, "taxonomy", "invoice", name="Invoice")
    (term / "resources").mkdir()
    (term / "resources" / "diagram.png").write_bytes(b"png")
    cap = obj(demo, "capabilities", "cli/x", name="X", Status="Missing")
    (cap / "resources" / "notes").mkdir(parents=True)
    (cap / "resources" / "notes" / "a.md").write_text("a")
    assert tcw(["taxonomy", "rm", "invoice"], demo).code == 0
    assert tcw(["capabilities", "rm", "cli/x"], demo).code == 0
    assert not term.exists() and not cap.exists()
    assert store(demo, "capabilities").joinpath("cli").is_dir() is False or \
        not any(store(demo, "capabilities").joinpath("cli").iterdir())
