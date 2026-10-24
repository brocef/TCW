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
