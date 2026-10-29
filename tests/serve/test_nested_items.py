"""The web app reads a nested work item by its id-path, percent-encoded as
one segment (TCW-111 Design 8; AC 18's reading half)."""

from __future__ import annotations

from urllib.parse import quote

from tests.serve.conftest import fs_project
from tests.work.projects import commit_all, write_item

EPIC, PART = "2026-10-01-epic", "2026-10-02-part"


def test_a_nested_item_is_read_and_listed(tmp_path, personal_on, serve_project):
    root = fs_project(tmp_path)
    write_item(root, EPIC, {"title": "Epic", "stage": "request"})
    write_item(root, f"{EPIC}/{PART}", {"title": "Part", "stage": "request",
                                        "parent": f"p.work/{EPIC}"})
    commit_all(root)
    served = serve_project(root)
    answer = served.get(f"/api/work/{quote(f'{EPIC}/{PART}', safe='')}")
    assert answer.status == 200, answer.body
    assert answer.json["item"]["full-id"] == f"p.work/{EPIC}/{PART}"
    board = served.get("/api/work")
    assert board.status == 200, board.body
    assert {i["full-id"] for i in board.json["items"]} == \
        {f"p.work/{EPIC}", f"p.work/{EPIC}/{PART}"}


def test_an_encoded_id_path_naming_no_item_is_404(tmp_path, personal_on, serve_project):
    root = fs_project(tmp_path)
    write_item(root, EPIC, {"title": "Epic", "stage": "request"})
    commit_all(root)
    served = serve_project(root)
    assert served.get(f"/api/work/{quote(f'{EPIC}/{PART}', safe='')}").status == 404


# -- creating (Step 10; AC 18's writing half) ------------------------------------------------


def _served_epic(tmp_path, serve_project):
    root = fs_project(tmp_path)
    write_item(root, EPIC, {"title": "Epic", "stage": "request"})
    commit_all(root)
    return root, serve_project(root)


def test_a_create_with_flat_is_made_at_the_top(tmp_path, personal_on, serve_project):
    root, served = _served_epic(tmp_path, serve_project)
    answer = served.post("/api/work", {"title": "Flat", "flat": True,
                                       "properties": {"parent": f"p.work/{EPIC}"}})
    assert answer.status == 201, answer.body
    assert answer.json["full-id"].count("/") == 1


def test_a_create_with_a_parent_is_made_inside_the_parents_folder(tmp_path, personal_on,
                                                                  serve_project):
    root, served = _served_epic(tmp_path, serve_project)
    answer = served.post("/api/work", {"title": "Part",
                                       "properties": {"parent": f"p.work/{EPIC}"}})
    assert answer.status == 201, answer.body
    made = answer.json["full-id"]
    assert made.startswith(f"p.work/{EPIC}/") and made.endswith("-part")
    assert (root / "docs" / "work" / made.split("/", 1)[1]).is_dir()


def test_flat_with_no_parent_is_refused_making_nothing(tmp_path, personal_on, serve_project):
    root, served = _served_epic(tmp_path, serve_project)
    before = sorted(p.name for p in (root / "docs" / "work").iterdir())
    answer = served.post("/api/work", {"title": "Part", "flat": True})
    assert answer.status == 400
    assert sorted(p.name for p in (root / "docs" / "work").iterdir()) == before


def test_a_create_under_a_200_character_parent_gets_a_shortened_folder(
        tmp_path, personal_on, serve_project):
    root = fs_project(tmp_path)
    letters = 200 - len("p.work/") - len("2026-10-01-/2026-10-02-")
    outer = f"2026-10-01-{'a' * (letters // 2)}"
    parent = f"{outer}/2026-10-02-{'b' * (letters - letters // 2)}"
    write_item(root, outer, {"title": "Outer", "stage": "request"})
    write_item(root, parent, {"title": "Parent", "stage": "request"})
    commit_all(root)
    served = serve_project(root)
    answer = served.post("/api/work", {"title": "A very long title " * 8,
                                       "properties": {"parent": f"p.work/{parent}"}})
    assert answer.status == 201, answer.body
    assert answer.json["full-id"].startswith(f"p.work/{parent}/")
    assert len(answer.json["full-id"]) <= 255
