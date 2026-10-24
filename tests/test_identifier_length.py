"""No full identifier is longer than 255 characters (TCW-111 Design 4.2, 4.3;
AC 14, and row n of Design 2.6). Every length named here is of a full
identifier; the parents are built by hand, an item nested in an item, with
folder names chosen so the full identifier has the length named."""

from __future__ import annotations

import json

import pytest

from tcw.ids import ID_LIMIT
from tests.objectcli import findings, item, obj, project, store, tcw  # noqa: F401


@pytest.fixture
def demo(tmp_path):
    return project(tmp_path, work={})


def snapshot(root):
    return sorted((str(p.relative_to(root)), p.read_bytes() if p.is_file() else None)
                  for p in (root / "docs").rglob("*"))


def nested_parent(total: int, project_id: str = "demo") -> str:
    """The id-path of an item nested in an item, both files-backend folder
    names, whose full identifier is `total` characters."""
    letters = total - len(f"{project_id}.work/") - len("2026-10-01-/2026-10-02-")
    first = letters // 2
    path = f"2026-10-01-{'a' * first}/2026-10-02-{'b' * (letters - first)}"
    assert len(f"{project_id}.work/{path}") == total
    return path


def cap_path(total: int) -> str:
    """A capability id-path of three parts whose full identifier is `total`
    characters."""
    rest = total - len("demo.capabilities/") - 2
    path = f"{'a' * 100}/{'b' * 100}/{'c' * (rest - 200)}"
    assert len(f"demo.capabilities/{path}") == total
    return path


def made_parent(root, total: int) -> str:
    path = nested_parent(total)
    item(root, path.split("/")[0], title="Outer")
    item(root, path, title="Parent")
    return path


# -- the tree stores ----------------------------------------------------------------

def test_a_capability_of_256_characters_is_refused_and_255_made(tcw, demo):
    long = cap_path(256)
    before = snapshot(demo)
    refused = tcw(["capabilities", "add", long], demo)
    assert refused.code == 2 and "a full identifier is at most 255" in refused.err
    assert snapshot(demo) == before
    assert tcw(["capabilities", "add", cap_path(255)], demo).code == 0


def test_a_term_slug_that_makes_256_characters_is_refused(tcw, demo):
    obj(demo, "taxonomy", "p" * 120, name="Parent")
    before = snapshot(demo)
    refused = tcw(["taxonomy", "add", "Long", "--slug", "s" * 121, "--parent", "p" * 120],
                  demo)
    assert refused.code == 2 and "at most 255" in refused.err
    assert snapshot(demo) == before
    assert tcw(["taxonomy", "add", "Long", "--slug", "s" * 120, "--parent", "p" * 120],
               demo).code == 0


# -- the files backend --------------------------------------------------------------

def test_a_long_title_under_a_200_character_parent_is_shortened(tcw, demo):
    parent = made_parent(demo, 200)
    made = tcw(["work", "new", "A very long title " * 8, "--parent", parent, "--nest"], demo)
    assert made.code == 0, made.err
    full = made.out.strip()
    assert full.startswith(f"demo.work/{parent}/") and len(full) <= ID_LIMIT


def test_under_a_235_character_parent_eight_characters_fit(tcw, demo):
    parent = made_parent(demo, 235)
    made = tcw(["work", "new", "Eight is enough", "--parent", parent, "--nest"], demo)
    assert made.code == 0, made.err
    assert len(made.out.strip()) == ID_LIMIT


def test_under_a_240_character_parent_nothing_fits(tcw, demo):
    parent = made_parent(demo, 240)
    before = snapshot(demo)
    refused = tcw(["work", "new", "Part", "--parent", parent, "--nest"], demo)
    assert refused.code == 2 and f"demo.work/{parent}" in refused.err
    assert "--nest" in refused.err
    assert snapshot(demo) == before


def test_a_project_id_of_231_characters_leaves_no_room(tcw, tmp_path):
    long = "p" * 231
    root = project(tmp_path, long, work={}, name="long")
    refused = tcw(["work", "new", "x"], root)
    assert refused.code == 2 and long in refused.err and "no room for any item" in refused.err


# -- row n: placed by hand beyond the limit -----------------------------------------

def test_a_capability_folder_of_256_characters_is_reported_and_still_listed(tcw, demo):
    path = cap_path(256)
    obj(demo, "capabilities", path, id="cap-aaaaaa", name="Long", Status="Missing")
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert findings(checked) == [
        f"error: docs/capabilities/{path}/tcw-capability.yaml: demo.capabilities/{path} is "
        f"256 characters; a full identifier is at most 255"]
    assert tcw(["capabilities", "list"], demo).out == f"demo.capabilities/{path}\n"


def test_a_nested_item_of_256_characters_is_reported_and_still_listed(tcw, demo):
    path = nested_parent(256)
    item(demo, path.split("/")[0])
    item(demo, path)
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert findings(checked) == [
        f"error: docs/work/{path}/tcw-work-item.yaml: demo.work/{path} is 256 characters; "
        f"a full identifier is at most 255"]
    listed = tcw(["work", "list", "--all", "--json"], demo)
    assert f"demo.work/{path}" in [i["full-id"] for i in json.loads(listed.out)["items"]]


def test_the_same_layouts_at_255_characters_pass(tcw, demo):
    obj(demo, "capabilities", cap_path(255),
        id="cap-aaaaaa", name="Long", Status="Missing")
    path = nested_parent(255)
    item(demo, path.split("/")[0])
    item(demo, path)
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (0, [])
