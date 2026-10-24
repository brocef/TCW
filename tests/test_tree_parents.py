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
    obj(root, "capabilities", "cli/x", id="cap-aaaaaa", name="X", Status="Missing")
    obj(root, "capabilities", "cli/y", id="cap-bbbbbb", name="Y", Status="Missing")
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
    assert "parent" not in state(demo, "capabilities", "cli/w")


# -- AC 13 ------------------------------------------------------------------------

@pytest.mark.parametrize("parent, words", [
    ("demo.taxonomy/x", "names a term"),
    ("demo.capabilities/cli/x/bad", "dangling parent ref"),
    ("demo.capabilities/cli/v", "parent names the object itself"),
])
def test_a_bad_capability_parent_is_an_error(tcw, demo, parent, words):
    obj(demo, "capabilities", "cli/v", id="cap-cccccc", name="V", Status="Missing",
        parent=parent)
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert any(f.startswith("error: docs/capabilities/cli/v") and words in f
               for f in findings(checked)), findings(checked)


def test_a_loop_of_parents_is_an_error_at_each(tcw, demo):
    obj(demo, "capabilities", "a", id="cap-dddddd", name="A", Status="Missing",
        parent="demo.capabilities/b")
    obj(demo, "capabilities", "b", id="cap-eeeeee", name="B", Status="Missing",
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

def test_the_parent_of_an_inherited_capability_is_refused_whole(tcw, tmp_path):
    """The capability is inherited, so the only place to write its parent
    would be an override folder, which TCW-112 replaces (Design 3.4)."""
    from tests.test_capabilities_rm import federated, write_cap
    base, child = federated(tmp_path)
    write_cap(child, "cli/x", id="cap-own001", Status="Supported")
    before = snapshot(child, base)
    refused = tcw(["capabilities", "set", "base.capabilities/auth/login", "--parent",
                   "cli/x", "--status", "Omitted"], child)
    assert refused.code == 3, refused
    assert "the parent of base.capabilities/auth/login is set in project 'base'" \
        in refused.err
    assert snapshot(child, base) == before
    # Without --parent the same command writes the override, as today.
    assert tcw(["capabilities", "set", "base.capabilities/auth/login",
                "--status", "Omitted"], child).code == 0


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
