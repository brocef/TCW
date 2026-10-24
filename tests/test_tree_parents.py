"""`parent:` for terms and capabilities (TCW-111 Design 3.1, 3.3, 3.4; AC 11,
13, 15, and choices 3 and 9 of the plan), and the warning where an object's
folder and its `parent` disagree (Design 3.2, row m; AC 12)."""

from __future__ import annotations

import json
import shutil

import pytest

from tests.objectcli import findings, obj, project, store, tcw  # noqa: F401
from tests.projectfiles import connect_projects, write_manifest
from tests.statefiles import CAPABILITY_STATE, TAXONOMY_STATE, read_state


@pytest.fixture
def demo(tmp_path):
    root = project(tmp_path, work={})
    obj(root, "capabilities", "cli/x", name="X", Status="Missing")
    obj(root, "capabilities", "cli/y", name="Y", Status="Missing")
    return root


def state(root, namespace, id_path):
    name = {"taxonomy": TAXONOMY_STATE, "capabilities": CAPABILITY_STATE}[namespace]
    return read_state(store(root, namespace) / id_path / name)


def snapshot(*roots):
    return [sorted((str(p.relative_to(r)), p.read_bytes() if p.is_file() else None)
                   for p in r.rglob("*") if ".git" not in p.parts) for r in roots]


# -- AC 11 ------------------------------------------------------------------------

def test_a_term_added_under_a_parent_records_it(tcw, demo):
    assert tcw(["taxonomy", "add", "Invoice"], demo).code == 0
    added = tcw(["taxonomy", "add", "Refund", "--parent", "invoice"], demo)
    assert (added.code, added.out) == (0, "demo.taxonomy/invoice/refund\n"), added
    assert state(demo, "taxonomy", "invoice/refund")["parent"] == "demo.taxonomy/invoice"
    shown = json.loads(tcw(["taxonomy", "show", "invoice/refund", "--json"], demo).out)
    assert shown["term"]["parent"] == "demo.taxonomy/invoice"
    assert list(shown["term"])[:3] == ["full-id", "owner", "parent"]
    root = json.loads(tcw(["taxonomy", "show", "invoice", "--json"], demo).out)
    assert root["term"]["parent"] is None
    text = tcw(["taxonomy", "show", "invoice/refund"], demo).out.splitlines()
    assert text[2] == "parent: demo.taxonomy/invoice"


def test_a_capability_added_with_a_parent(tcw, demo):
    added = tcw(["capabilities", "add", "cli/w", "--parent", "cli/x"], demo)
    assert (added.code, added.err.count("warning")) == (0, 0), added
    assert state(demo, "capabilities", "cli/w")["parent"] == "demo.capabilities/cli/x"
    shown = json.loads(tcw(["capabilities", "show", "cli/w", "--json"], demo).out)
    assert shown["capability"]["parent"] == "demo.capabilities/cli/x"
    assert "parent" not in shown["capability"]["fields"]


def test_a_capability_whose_folder_and_parent_disagree_is_made_with_a_warning(tcw, demo):
    added = tcw(["capabilities", "add", "cli/x/z", "--parent", "cli/y"], demo)
    assert added.code == 0, added.err
    assert state(demo, "capabilities", "cli/x/z")["parent"] == "demo.capabilities/cli/y"
    assert "sits in the folder of demo.capabilities/cli/x" in added.err
    assert "parent: decides" in added.err


def test_set_parent_and_clear_it(tcw, demo):
    assert tcw(["capabilities", "add", "cli/w"], demo).code == 0
    assert tcw(["capabilities", "set", "cli/w", "--parent", "cli/x"], demo).code == 0
    assert state(demo, "capabilities", "cli/w")["parent"] == "demo.capabilities/cli/x"
    assert tcw(["capabilities", "set", "cli/w", "--parent", ""], demo).code == 0
    # TCW-112 Design 4.2: a cleared field is written as an explicit null on
    # every object of the project's own, which for one that overrides
    # nothing means the same as no key.
    assert state(demo, "capabilities", "cli/w")["parent"] is None
    shown = tcw(["capabilities", "show", "cli/w", "--json"], demo)
    assert json.loads(shown.out)["capability"].get("parent") is None


# -- AC 13 ------------------------------------------------------------------------

@pytest.mark.parametrize("parent, words", [
    ("demo.taxonomy/x", "names a term"),
    ("demo.capabilities/cli/x/bad", "dangling parent ref"),
    ("demo.capabilities/cli/v", "parent names the object itself"),
])
def test_a_bad_capability_parent_is_an_error(tcw, demo, parent, words):
    obj(demo, "capabilities", "cli/v", name="V", Status="Missing",
        parent=parent)
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert any(f.startswith("error: docs/capabilities/cli/v") and words in f
               for f in findings(checked)), findings(checked)


def test_a_loop_of_parents_is_an_error_at_each(tcw, demo):
    obj(demo, "capabilities", "a", name="A", Status="Missing",
        parent="demo.capabilities/b")
    obj(demo, "capabilities", "b", name="B", Status="Missing",
        parent="demo.capabilities/a")
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    loops = [f for f in findings(checked) if "parent forms a loop" in f]
    assert [f.split(":")[1].strip() for f in loops] == ["docs/capabilities/a",
                                                        "docs/capabilities/b"], loops


# -- AC 15 ------------------------------------------------------------------------

@pytest.fixture
def pair(tmp_path):
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    connect_projects(app, "parent", "core", inherit="none")
    write_manifest(app, {"core": "../core"})
    return app, core


def test_a_parent_in_another_project(tcw, pair):
    app, core = pair
    obj(core, "taxonomy", "payment", name="Payment")
    obj(app, "taxonomy", "refund", name="Refund", parent="core.taxonomy/payment")
    assert tcw(["validate"], app).code == 0
    shutil.rmtree(store(core, "taxonomy") / "payment")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert any("dangling parent ref 'core.taxonomy/payment'" in f
               for f in findings(checked)), findings(checked)


def test_a_parent_in_a_project_not_on_this_machine_is_unresolved(tcw, pair):
    app, core = pair
    obj(app, "taxonomy", "refund", name="Refund", parent="core.taxonomy/payment")
    shutil.rmtree(core)
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked
    assert any(f.startswith("unresolved:") and "core.taxonomy/payment" in f
               for f in findings(checked)), findings(checked)


# -- choice 9 ---------------------------------------------------------------------

def test_a_term_whose_parent_is_another_projects_is_made_at_the_root(tcw, pair):
    app, core = pair
    obj(core, "taxonomy", "payment", name="Payment")
    added = tcw(["taxonomy", "add", "X", "--parent", "core.taxonomy/payment"], app)
    assert (added.code, added.out) == (0, "app.taxonomy/x\n"), added
    assert state(app, "taxonomy", "x")["parent"] == "core.taxonomy/payment"
    before = snapshot(app)
    missing = tcw(["taxonomy", "add", "Y", "--parent", "core.taxonomy/nope"], app)
    assert missing.code == 4
    assert snapshot(app) == before


# -- choice 3 ---------------------------------------------------------------------

def test_the_parent_of_an_inherited_capability_is_written_into_the_override(tcw, tmp_path):
    """TCW-112 Design 4.2 replaces TCW-111's interim refusal: `parent` is a
    field of the override like any other, so it is written into the child's
    own object at the same path, and `base` is left alone."""
    from tests.test_capabilities_rm import federated, write_cap
    base, child = federated(tmp_path)
    write_cap(child, "cli/x", Status="Supported")
    before = snapshot(base)
    found = tcw(["capabilities", "set", "base.capabilities/auth/login", "--parent",
                 "cli/x", "--status", "Omitted"], child)
    assert found.code == 0, found
    written = state(child, "capabilities", "auth/login")
    assert written == {"parent": "child.capabilities/cli/x", "Status": "Omitted"}
    assert snapshot(base) == before


# -- AC 12 for the tree stores ----------------------------------------------------

def test_a_nested_term_with_no_parent_warns(tcw, demo):
    obj(demo, "taxonomy", "invoice", name="Invoice")
    obj(demo, "taxonomy", "invoice/refund", name="Refund")
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (0, [
        "warning: docs/taxonomy/invoice/refund/tcw-taxonomy.yaml: "
        "demo.taxonomy/invoice/refund sits in the folder of demo.taxonomy/invoice, but "
        "its parent is not set; parent: decides (set it to demo.taxonomy/invoice, or "
        "move the folder)"])


def test_a_term_in_an_organising_folder_does_not_warn(tcw, demo):
    obj(demo, "taxonomy", "group/refund", name="Refund", parent="demo.taxonomy/other")
    obj(demo, "taxonomy", "other", name="Other")
    assert (tcw(["validate"], demo).code, findings(tcw(["validate"], demo))) == (0, [])
