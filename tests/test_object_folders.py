"""`tcw/object_folders.py`: the state files, the walk and the rules for one
object's folder (TCW-111 Design 1 and 2), on folders built by hand."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tcw.findings import Finding
from tcw.ids import FullId
from tcw.object_folders import (
    LEGACY, MISPLACED, ORGANISING, RESERVED, UNMADE, disagreement, exact_path,
    folder_parent, is_object, object_paths, objects_below, read_state,
    removal_blockers, reserved_names, shape_problems, state_text, walk,
)
from tcw.project_files import version_line

TERM, CAP, ITEM = "tcw-taxonomy.yaml", "tcw-capability.yaml", "tcw-work-item.yaml"


def obj(root: Path, path: str, state: str = TERM) -> Path:
    folder = root / path
    folder.mkdir(parents=True, exist_ok=True)
    (folder / state).write_text(version_line())
    return folder


def mixed(root: Path) -> Path:
    """A work store holding one of every kind of folder the walk classes."""
    obj(root, "2026-10-01-epic", ITEM)
    (root / "2026-10-01-epic" / "plan").mkdir()
    (root / "2026-10-01-epic" / "plan" / "plan.md").write_text("x")
    obj(root, "2026-10-01-epic/2026-10-02-part", ITEM)
    obj(root, "2026-10-01-epic/drafts/2026-10-03-hidden", ITEM)
    obj(root, "2026/2026-10-04-grouped", ITEM)
    obj(root, "review/2026-10-05-under-reserved", ITEM)
    (root / "empty").mkdir()
    (root / "old").mkdir()
    (root / "old" / "item.yaml").write_text("title: x\n")
    obj(root, "2026-10-01-epic/resources/2026-10-06-sample", ITEM)
    obj(root, "2026-10-01-epic/plan/2026-10-07-in-a-stage", ITEM)
    (root / ".hidden").mkdir()
    obj(root, ".hidden/2026-10-08-x", ITEM)
    return root


def test_the_walk_lists_objects_at_any_depth_and_skips_what_it_must(tmp_path):
    found = walk(mixed(tmp_path), "work")
    assert found.objects == (
        "2026/2026-10-04-grouped", "2026-10-01-epic", "2026-10-01-epic/2026-10-02-part",
        "2026-10-01-epic/drafts/2026-10-03-hidden", "review/2026-10-05-under-reserved")
    kinds = {path: kind for path, kind, _ in found.folders}
    assert kinds == {"2026-10-01-epic/drafts": MISPLACED, "2026": ORGANISING,
                     "review": RESERVED, "empty": ORGANISING, "old": LEGACY}
    assert found.resources == ("2026-10-01-epic/resources",)


def test_the_walk_classes_files(tmp_path):
    obj(tmp_path, "a")
    (tmp_path / "README.md").write_text("x")
    (tmp_path / TERM).write_text(version_line())
    (tmp_path / "a" / "notes.md").write_text("x")
    (tmp_path / "a" / "description.md").write_text("x")
    (tmp_path / "group").mkdir()
    (tmp_path / "group" / "x.txt").write_text("x")
    files = {(p, k) for p, k, _ in walk(tmp_path, "taxonomy").files}
    assert files == {("README.md", "loose"), (TERM, "root-state"),
                     ("a/notes.md", "extra"), ("group/x.txt", "loose")}


@pytest.mark.skipif(sys.platform == "win32", reason="symbolic links")
def test_a_symbolic_linked_folder_is_not_visited(tmp_path):
    outside = tmp_path / "outside"
    obj(outside, "x")
    store = tmp_path / "store"
    store.mkdir()
    os.symlink(outside, store / "link")
    assert object_paths(store, "taxonomy") == []
    assert not is_object(store, "taxonomy", "link/x")


def test_organising_folders_in_every_namespace(tmp_path):
    for ns, state in (("taxonomy", TERM), ("capabilities", CAP), ("work", ITEM)):
        root = tmp_path / ns
        obj(root, "group/x", state)
        assert object_paths(root, ns) == ["group/x"]
        assert not is_object(root, ns, "group")


def test_is_object_agrees_with_the_walk_on_every_folder(tmp_path):
    root = mixed(tmp_path)
    listed = set(walk(root, "work").objects)
    every = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_dir()]
    assert every
    for path in every:
        assert is_object(root, "work", path) == (path in listed), path


@pytest.mark.parametrize("bad", ["/etc", "a/../b", "a//b", ".x", "", "a/", "/", "a/./b"])
def test_is_object_refuses_bad_id_paths_before_reading(tmp_path, bad):
    obj(tmp_path, "a/b")
    assert not is_object(tmp_path, "taxonomy", bad)


def test_exact_path_refuses_a_letter_case_variant(tmp_path):
    obj(tmp_path, "cli/x")
    assert exact_path(tmp_path, "cli/x") is True
    assert exact_path(tmp_path, "CLI/x") in (False, "cli/x")
    assert not is_object(tmp_path, "taxonomy", "CLI/x")


def test_reserved_names_are_per_store():
    assert reserved_names("taxonomy") == {"resources"}
    assert {"resources", "comments", "plan", "review", "inbox"} <= reserved_names("work")


def test_state_text_keeps_the_version_line_as_written(tmp_path):
    path = tmp_path / CAP
    path.write_text('tcw-version: "4.0.0"\nname: x\n')
    assert state_text(path, {"name": "y"}) == 'tcw-version: "4.0.0"\nname: y\n'
    path.write_text("# a comment\nname: x\ntcw-version: 4.0.0\n")
    assert state_text(path, {"name": "y"}).startswith("tcw-version: 4.0.0\n")
    new = tmp_path / "new" / CAP
    assert state_text(new, {"name": "y"}) == version_line() + "name: y\n"


@pytest.mark.parametrize("text, words", [
    ("name: x\n", "has no tcw-version"),
    ("tcw-version: 4\nname: x\n", "written as text"),
    ("tcw-version: '3.0'\n", "format of TCW 3.0"),
    ("tcw-version: '99.1'\n", "newer"),
])
def test_read_state_reports_each_version_problem(tmp_path, text, words):
    path = tmp_path / TERM
    path.write_text(text)
    data, problem = read_state(path)
    assert data is None and words in problem


def test_read_state_of_a_good_and_an_absent_file(tmp_path):
    path = tmp_path / TERM
    path.write_text(version_line() + "name: x\n")
    assert read_state(path) == ({"name": "x"}, None)
    assert read_state(tmp_path / "nothing.yaml") == ({}, None)


def test_disagreement():
    child = FullId("demo", "work", "e/p")
    epic = FullId("demo", "work", "e")
    other = FullId("demo", "work", "o")
    assert disagreement(child, None, other) is None
    assert disagreement(child, epic, epic) is None
    text = disagreement(child, epic, other)
    assert text == ("demo.work/e/p sits in the folder of demo.work/e, but its parent "
                    "is demo.work/o; parent: decides (set it to demo.work/e, or move "
                    "the folder)")
    assert "its parent is not set" in disagreement(child, epic, None)


def test_folder_parent(tmp_path):
    root = mixed(tmp_path)
    assert folder_parent(root, "work", "2026-10-01-epic/2026-10-02-part") == "2026-10-01-epic"
    assert folder_parent(root, "work", "2026-10-01-epic/drafts/2026-10-03-hidden") is None
    assert folder_parent(root, "work", "2026/2026-10-04-grouped") is None
    assert folder_parent(root, "work", "2026-10-01-epic") is None


def test_objects_below(tmp_path):
    root = mixed(tmp_path)
    assert objects_below(root, "work", "2026-10-01-epic") == [
        "2026-10-01-epic/2026-10-02-part", "2026-10-01-epic/drafts/2026-10-03-hidden"]


def test_removal_blockers_search_everything_below(tmp_path):
    folder = obj(tmp_path, "cli/x", CAP)
    obj(tmp_path, "cli/x/.drafts/y", CAP)
    obj(tmp_path, "cli/x/resources/sample", CAP)
    (tmp_path / "cli/x/old").mkdir()
    (tmp_path / "cli/x/old/meta.yaml").write_text("name: x\n")
    assert removal_blockers(folder, tmp_path) == [
        ("cli/x/.drafts/y", "state"), ("cli/x/old", "meta.yaml"),
        ("cli/x/resources/sample", "state")]


def test_the_walk_finds_resources_by_its_exact_spelling(tmp_path):
    obj(tmp_path, "a")
    obj(tmp_path, "b")
    (tmp_path / "a" / "resources").mkdir()
    (tmp_path / "b" / "Resources").mkdir()
    found = walk(tmp_path, "taxonomy")
    assert found.resources == ("a/resources",)
    assert ("b/Resources", RESERVED, "") in found.folders


def test_shape_problems_rows_a_to_h(tmp_path):
    root = mixed(tmp_path)
    (root / "dod.yaml").write_text("- x\n")
    (root / "2026-10-01-epic" / "notes.md").write_text("x")
    (root / "2026-10-09-stateless").mkdir()
    found = walk(root, "work", item_named=lambda name: name[:4].isdigit()
                 and name[4:5] == "-")
    problems = shape_problems(found, root, "work", "demo",
                              where=lambda p: p.relative_to(root).as_posix(),
                              unmade_message="named as an item, but no state file")
    assert set(problems) == {
        Finding("warning", "dod.yaml", "is not part of any object"),
        Finding("error", "2026-10-01-epic/notes.md",
                "is not one of demo.work/2026-10-01-epic's files; move it into "
                "resources/"),
        Finding("error", "2026-10-01-epic/drafts",
                "is not a child object of demo.work/2026-10-01-epic: it has no "
                "tcw-work-item.yaml; give it one, or move it into resources/"),
        Finding("error", "review", "'review' is reserved in the work store; see "
                "docs/migration-guide-2.8-to-3.0.0.md for the work store layout"),
        Finding("warning", "empty", "holds no TCW object"),
        Finding("error", "old", "holds a TCW 3.x item.yaml; run 'tcw migrate' in this "
                                "project"),
        Finding("error", "2026-10-09-stateless/tcw-work-item.yaml",
                "named as an item, but no state file"),
    }


def test_a_state_file_in_the_root_and_a_skipped_file(tmp_path):
    (tmp_path / TERM).write_text(version_line())
    (tmp_path / "config.yaml").write_text("extends: []\n")
    problems = shape_problems(walk(tmp_path, "taxonomy"), tmp_path, "taxonomy", "demo",
                              skip=[tmp_path / "config.yaml"])
    assert problems == [Finding("error", str(tmp_path / TERM),
                                "the store's root is not an object; move this file "
                                "into an object's folder")]


def test_an_unmade_folder_is_not_also_empty_or_its_files_loose(tmp_path):
    (tmp_path / "TCW-7-x" / "plan").mkdir(parents=True)
    (tmp_path / "TCW-7-x" / "notes.md").write_text("x")
    found = walk(tmp_path, "work", item_named=lambda n: n.startswith("TCW-"))
    assert [(p, k) for p, k, _ in found.folders] == [("TCW-7-x", UNMADE)]
    assert found.files == ()
