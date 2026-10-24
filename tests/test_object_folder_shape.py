"""A term's or capability's folder is bounded: its fixed files, its child
objects' folders, and one `resources/` folder, and `tcw validate` reports
anything else (TCW-111 Design 2.2, 2.6 rows a-g; AC 5, 6, 7, and AC 17's
validate half)."""

from __future__ import annotations

import json

import pytest

from tests.objectcli import findings, obj, project, store, tcw  # noqa: F401
from tests.statefiles import write_state

ROW_B = ("error: docs/taxonomy/invoice/drafts: is not a child object of "
         "demo.taxonomy/invoice: it has no tcw-taxonomy.yaml; give it one, or move "
         "it into resources/")
ROW_C = "error: docs/capabilities/resources: 'resources' is reserved in the capabilities store"
ROW_F = ("error: docs/capabilities/cli/old: holds a TCW 3.x meta.yaml; run 'tcw "
         "migrate' in this project")
ROW_G = ("error: docs/taxonomy/tcw-taxonomy.yaml: the store's root is not an object; "
         "move this file into an object's folder")


@pytest.fixture
def demo(tmp_path):
    root = project(tmp_path, work={})
    obj(root, "taxonomy", "invoice", name="Invoice")
    obj(root, "capabilities", "cli/x", id="cap-aaaaaa", name="X", Status="Missing")
    return root


def validate(tcw, root):
    checked = tcw(["validate"], root)
    return checked.code, findings(checked), checked


def test_a_clean_project_passes(tcw, demo):
    assert validate(tcw, demo)[:2] == (0, [])


# -- AC 5 -------------------------------------------------------------------------

def test_a_folder_with_no_state_file_in_a_term(tcw, demo):
    (store(demo, "taxonomy") / "invoice" / "drafts").mkdir()
    (store(demo, "taxonomy") / "invoice" / "drafts" / "a.md").write_text("a")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [ROW_B])


def test_a_resources_folder_in_the_store_root(tcw, demo):
    (store(demo, "capabilities") / "resources").mkdir()
    (store(demo, "capabilities") / "resources" / "a.md").write_text("a")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [ROW_C])


def test_a_3x_capability_folder(tcw, demo):
    old = store(demo, "capabilities") / "cli" / "old"
    old.mkdir()
    (old / "meta.yaml").write_text("id: cap-old000\nname: Old\nStatus: Missing\n")
    (old / "description.md").write_text("")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [ROW_F])


def test_a_state_file_in_the_store_root(tcw, demo):
    write_state(store(demo, "taxonomy") / "tcw-taxonomy.yaml", "name: Root\n")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [ROW_G])


def test_resources_at_any_depth_pass(tcw, demo):
    term = store(demo, "taxonomy") / "invoice"
    (term / "resources" / "a").mkdir(parents=True)
    (term / "resources" / "notes.md").write_text("notes")
    (term / "resources" / "a" / "b.png").write_bytes(b"\x89PNG")
    assert validate(tcw, demo)[:2] == (0, [])


def test_a_loose_file_in_the_root_and_an_empty_organising_folder_warn(tcw, demo):
    (store(demo, "capabilities") / "README.md").write_text("about")
    (store(demo, "taxonomy") / "empty").mkdir()
    code, found, _ = validate(tcw, demo)
    assert (code, sorted(found)) == (0, [
        "warning: docs/capabilities/README.md: is not part of any object",
        "warning: docs/taxonomy/empty: holds no TCW object",
    ])


# -- AC 6 -------------------------------------------------------------------------

def test_a_term_named_review_passes(tcw, demo):
    obj(demo, "taxonomy", "review", name="Review")
    assert validate(tcw, demo)[:2] == (0, [])


# -- AC 7 -------------------------------------------------------------------------

def test_attachments_are_the_resources_and_a_loose_file_is_reported(tcw, demo):
    term = store(demo, "taxonomy") / "invoice"
    (term / "resources").mkdir()
    (term / "resources" / "diagram.png").write_bytes(b"\x89PNG")
    (term / "old.txt").write_text("old")
    shown = tcw(["taxonomy", "show", "invoice", "--json"], demo)
    assert json.loads(shown.out)["term"]["attachments"] == ["resources/diagram.png"]
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [
        "error: docs/taxonomy/invoice/old.txt: is not one of demo.taxonomy/invoice's "
        "files; move it into resources/"])


def test_an_appended_document_in_resources_is_read(tcw, demo):
    cap = obj(demo, "capabilities", "cli/cam", id="cap-cccccc", name="Cam",
              Status="Missing", appendedDocs=["resources/camera.md"])
    (cap / "description.md").write_text("Body.")
    (cap / "resources").mkdir()
    (cap / "resources" / "camera.md").write_text("Camera notes.")
    shown = json.loads(tcw(["capabilities", "show", "cli/cam", "--json"], demo).out)
    assert shown["capability"]["body"].endswith("Camera notes.")
    assert validate(tcw, demo)[:2] == (0, [])


def test_an_appended_document_beside_the_state_file_is_not(tcw, demo):
    cap = obj(demo, "capabilities", "cli/cam", id="cap-cccccc", name="Cam",
              Status="Missing", appendedDocs=["camera.md"])
    (cap / "description.md").write_text("Body.")
    (cap / "camera.md").write_text("Camera notes.")
    shown = json.loads(tcw(["capabilities", "show", "cli/cam", "--json"], demo).out)
    assert "Camera notes." not in shown["capability"]["body"]
    code, found, _ = validate(tcw, demo)
    assert code == 1
    assert "error: docs/capabilities/cli/cam: 'camera.md' is not in resources/" in found


# -- AC 17, validate --------------------------------------------------------------

def test_a_3x_taxonomy_folder_is_reported_once(tcw, demo):
    old = store(demo, "taxonomy") / "old"
    old.mkdir()
    (old / "meta.yaml").write_text("name: Old\n")
    (old / "description.md").write_text("")
    (old / "notes.txt").write_text("x")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (1, [
        "error: docs/taxonomy/old: holds a TCW 3.x meta.yaml; run 'tcw migrate' in "
        "this project"])


# -- AC 5's other cases -----------------------------------------------------------

def test_a_leftover_config_yaml_gives_one_finding(tcw, demo):
    (store(demo, "taxonomy") / "config.yaml").write_text("extends: []\n")
    code, found, _ = validate(tcw, demo)
    assert code == 1 and len(found) == 1, found
    assert "no longer read since TCW 2.5.0" in found[0]


def test_yaml_in_resources_is_not_parsed_and_the_checks_still_run(tcw, demo):
    term = store(demo, "taxonomy") / "invoice"
    (term / "resources").mkdir()
    (term / "resources" / "sample.yaml").write_text("a: [unclosed\n")
    obj(demo, "capabilities", "cli/ghost", id="cap-dddddd", name="Ghost",
        Status="Missing", appendedDocs=["resources/ghost.md"])
    code, found, checked = validate(tcw, demo)
    assert (code, found) == (1, [
        "error: docs/capabilities/cli/ghost: missing attachment 'resources/ghost.md'"])
    assert "checks skipped" not in checked.err


def test_yaml_loose_in_a_term_is_still_parsed(tcw, demo):
    (store(demo, "taxonomy") / "invoice" / "sample.yaml").write_text("a: [unclosed\n")
    code, found, checked = validate(tcw, demo)
    assert code == 1
    assert any("docs/taxonomy/invoice/sample.yaml" in f and "while parsing" in f
               for f in found), found
    assert "taxonomy and capabilities checks skipped" in checked.err


def test_markdown_in_resources_that_is_not_utf8_warns(tcw, demo):
    term = store(demo, "taxonomy") / "invoice"
    (term / "resources").mkdir()
    (term / "resources" / "old.md").write_bytes(b"\xff\xfe bad")
    code, found, _ = validate(tcw, demo)
    assert (code, found) == (0, [
        "warning: docs/taxonomy/invoice/resources/old.md: not checked for tcw:// "
        "links: not valid UTF-8"])


def test_a_broken_link_in_resources_is_still_an_error(tcw, demo):
    term = store(demo, "taxonomy") / "invoice"
    (term / "resources").mkdir()
    (term / "resources" / "design.md").write_text("[x](tcw://demo.taxonomy/nope)\n")
    code, found, _ = validate(tcw, demo)
    assert code == 1
    assert any(f.startswith("error: docs/taxonomy/invoice/resources/design.md")
               for f in found), found
