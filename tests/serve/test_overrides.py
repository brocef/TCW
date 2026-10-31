"""The web app and overrides by path (TCW-112 Design 4.5; AC 33, 42, 44).

`app` inherits everything from `core` (`parents: [core]`, found through
`app`'s manifest). `core`'s `cli/x` has `Status: Missing`, `Priority: P1`,
`prependedDocs: [resources/a.md]` and the description `Core body`; `app`'s
own `cli/x` holds only `Status: Supported`, with no `description.md`: AC 5's
override, with AC 7's attached document."""

from __future__ import annotations

import shutil

import pytest

from tests.projectfiles import write_config, write_manifest
from tests.serve.test_records import assert_error, detail
from tests.statefiles import CAPABILITY_STATE, TAXONOMY_STATE, read_state, write_state
from tests.test_capabilities_rm import repo, write_cap


def state(root, path: str) -> dict:
    return read_state(root / "docs" / "capabilities" / path / CAPABILITY_STATE)


def patch(served, path: str, payload: dict):
    key = path.replace("/", "%2F")
    revision = detail(served, "capabilities", f"{key}?scope=up")["coreRevision"]
    return served.patch(f"/api/capabilities/{key}", {"revision": revision, **payload})


def tcw_show(tcw, root, path: str) -> dict:
    import json
    shown = tcw(["capabilities", "show", path, "--json"], root)
    assert shown.code == 0, shown
    return json.loads(shown.out)["capability"]


@pytest.fixture
def family(tmp_path):
    core = repo(tmp_path, "core")
    write_cap(core, "cli/x", Status="Missing", Priority="P1", body="Core body",
              prependedDocs=["resources/a.md"])
    (core / "docs" / "capabilities" / "cli" / "x" / "resources").mkdir()
    (core / "docs" / "capabilities" / "cli" / "x" / "resources" / "a.md").write_text(
        "From a.md.\n")
    write_cap(core, "cli/y", Status="Supported")
    (core / "docs" / "taxonomy").mkdir()
    app = repo(tmp_path, "app")
    (app / "docs" / "taxonomy").mkdir()
    write_config(app, "id: app\nparents:\n- core\n")
    write_manifest(app, {"core": "../core"})
    write_cap(app, "cli/x", complete=False, Status="Supported")
    return core, app


@pytest.fixture
def served(family, serve_project):
    return serve_project(family[1])


# -- AC 33 -------------------------------------------------------------------------


def test_ac33_an_override_carries_what_it_overrides(served):
    found = detail(served, "capabilities", "cli%2Fx")["capability"]
    assert (found["full-id"], found["overrides"]) == \
        ("app.capabilities/cli/x", "core.capabilities/cli/x")
    listed = {c["full-id"]: c for c in
              served.get("/api/capabilities?scope=up").json["capabilities"]}
    assert listed["app.capabilities/cli/x"]["overrides"] == "core.capabilities/cli/x"
    assert listed["core.capabilities/cli/y"]["overrides"] is None
    assert "core.capabilities/cli/x" not in listed


def test_ac33_a_patch_of_the_override_changes_apps_file(family, served):
    _, app = family
    answer = patch(served, "cli/x", {"fields": {"Lifecycle": "Stable"}})
    assert answer.status == 200, answer.body
    assert state(app, "cli/x") == {"Status": "Supported", "Lifecycle": "Stable"}


def test_ac33_a_patch_of_an_inherited_capability_is_read_only(family, served):
    core, app = family
    before = (core / "docs" / "capabilities" / "cli" / "y" / CAPABILITY_STATE).read_text()
    answer = patch(served, "cli/y", {"fields": {"Lifecycle": "Stable"}})
    assert_error(answer, 403, "read-only")
    assert "belongs to project 'core'" in answer.json["error"]
    assert (core / "docs" / "capabilities" / "cli" / "y" / CAPABILITY_STATE).read_text() \
        == before
    assert not (app / "docs" / "capabilities" / "cli" / "y").exists()


def test_ac33_a_missing_parent_answers_503(family, serve_project):
    core, app = family
    shutil.rmtree(core)
    answer = serve_project(app).get("/api/taxonomy?scope=up")
    assert_error(answer, 503, "inherited-unavailable")
    assert "'core'" in answer.json["error"]


# -- AC 42 -------------------------------------------------------------------------


def test_ac42_clearing_a_field_of_a_project_with_no_parents(tmp_path, serve_project,
                                                            tcw):
    app = repo(tmp_path, "app")
    write_cap(app, "cli/y", Status="Supported", Priority="P1")
    served = serve_project(app)
    answer = patch(served, "cli/y", {"fields": {"Priority": None}})
    assert answer.status == 200, answer.body
    assert "Priority" in state(app, "cli/y") and state(app, "cli/y")["Priority"] is None
    assert "Priority" not in tcw_show(tcw, app, "cli/y")["fields"]
    checked = tcw(["validate"], app)
    assert "cli/y" not in checked.out, checked


def test_ac42_clearing_a_field_of_an_override_hides_the_inherited_value(family, served,
                                                                        tcw):
    _, app = family
    answer = patch(served, "cli/x", {"fields": {"Priority": None}})
    assert answer.status == 200, answer.body
    assert state(app, "cli/x") == {"Status": "Supported", "Priority": None}
    assert "Priority" not in tcw_show(tcw, app, "cli/x")["fields"]


# -- AC 44 and choice 5 --------------------------------------------------------------


def test_ac44_the_detail_gives_the_declared_description(served):
    answer = detail(served, "capabilities", "cli%2Fx")
    assert answer["capability"]["body"].startswith("From a.md.")
    assert "Core body" in answer["capability"]["body"]
    assert answer["declaredDescription"] is None


def test_ac44_a_body_edit_writes_the_declared_description_only(family, served, tcw):
    _, app = family
    answer = patch(served, "cli/x", {"body": "App body"})
    assert answer.status == 200, answer.body
    assert answer.json["declaredDescription"] == "App body"
    folder = app / "docs" / "capabilities" / "cli" / "x"
    assert (folder / "description.md").read_text() == "App body"
    body = tcw_show(tcw, app, "cli/x")["body"]
    assert body.count("From a.md.") == 1
    assert body.index("From a.md.") < body.index("App body")


def test_ac44_an_own_capability_with_attached_documents(tmp_path, serve_project, tcw):
    solo = repo(tmp_path, "solo")
    write_cap(solo, "cli/y", Status="Supported", body="Y body\n",
              prependedDocs=["resources/p.md"])
    folder = solo / "docs" / "capabilities" / "cli" / "y"
    (folder / "resources").mkdir()
    (folder / "resources" / "p.md").write_text("From p.md.\n")
    served = serve_project(solo)
    answer = detail(served, "capabilities", "cli%2Fy")
    # Trimmed as the combined body uses it, so a file ending in a newline
    # does not make the two differ (plan Step 17b).
    assert answer["declaredDescription"] == "Y body"
    changed = patch(served, "cli/y", {"body": "Y edited"})
    assert changed.status == 200, changed.body
    assert (folder / "description.md").read_text() == "Y edited"
    assert tcw_show(tcw, solo, "cli/y")["body"].count("From p.md.") == 1


def test_ac44_with_no_attached_documents_the_two_are_equal(tmp_path, serve_project):
    solo = repo(tmp_path, "solo")
    write_cap(solo, "cli/y", Status="Supported", body="Y body\n")
    answer = detail(serve_project(solo), "capabilities", "cli%2Fy")
    assert answer["declaredDescription"] == "Y body" == answer["capability"]["body"]


def test_ac44_an_empty_description_is_an_empty_declared_description(tmp_path,
                                                                    serve_project):
    solo = repo(tmp_path, "solo")
    write_cap(solo, "cli/y", Status="Supported", body="")
    served = serve_project(solo)
    assert detail(served, "capabilities", "cli%2Fy")["declaredDescription"] == ""


def test_ac44_post_and_patch_answers_carry_the_declared_description(tmp_path,
                                                                     serve_project):
    solo = repo(tmp_path, "solo")
    served = serve_project(solo)
    created = served.post("/api/capabilities", {"path": "cli/z", "body": "Z body"})
    assert created.status == 201, created.body
    assert created.json["declaredDescription"] == "Z body"
    changed = patch(served, "cli/z", {"fields": {"Lifecycle": "Stable"}})
    assert changed.json["declaredDescription"] == "Z body"


def test_choice5_an_empty_body_on_an_object_overriding_nothing(tmp_path, serve_project,
                                                               tcw):
    solo = repo(tmp_path, "solo")
    write_cap(solo, "cli/y", Status="Supported", body="Y body")
    served = serve_project(solo)
    answer = patch(served, "cli/y", {"body": ""})
    assert answer.status == 200, answer.body
    assert (solo / "docs" / "capabilities" / "cli" / "y" / "description.md"
            ).read_text() == ""
    checked = tcw(["validate"], solo)
    assert checked.code == 0, checked


def test_choice5_an_empty_body_on_an_override_falls_back(family, served, tcw):
    _, app = family
    patch(served, "cli/x", {"body": "App body"})
    answer = patch(served, "cli/x", {"body": ""})
    assert answer.status == 200, answer.body
    assert "Core body" in tcw_show(tcw, app, "cli/x")["body"]


# -- choice 6, and the revision over every chain member ---------------------------------


def test_choice6_a_patch_of_an_own_term_override_changes_only_its_file(tmp_path,
                                                                      serve_project):
    from tests.inherit import entry
    core, app = repo(tmp_path, "core"), repo(tmp_path, "app")
    for root in (core, app):
        (root / "docs" / "taxonomy").mkdir()
    entry(core, "taxonomy", "invoice")
    (core / "docs" / "taxonomy" / "invoice" / "description.md").write_text("Core text")
    write_config(app, "id: app\nparents:\n- core\n")
    write_manifest(app, {"core": "../core"})
    override = app / "docs" / "taxonomy" / "invoice"
    override.mkdir()
    write_state(override / TAXONOMY_STATE, "kind: Vocabulary\n")
    before = (core / "docs" / "taxonomy" / "invoice" / TAXONOMY_STATE).read_text()
    served = serve_project(app)
    revision = detail(served, "taxonomy", "invoice")["coreRevision"]
    answer = served.patch("/api/taxonomy/invoice",
                          {"revision": revision, "fields": {"name": "Bill"}})
    assert answer.status == 200, answer.body
    assert answer.json["term"]["full-id"] == "app.taxonomy/invoice"
    assert answer.json["term"]["name"] == "Bill"
    assert read_state(override / TAXONOMY_STATE)["name"] == "Bill"
    assert (core / "docs" / "taxonomy" / "invoice" / TAXONOMY_STATE).read_text() == before


def test_a_second_patch_with_the_same_revision_is_stale(served):
    revision = detail(served, "capabilities", "cli%2Fx")["coreRevision"]
    first = served.patch("/api/capabilities/cli%2Fx",
                         {"revision": revision, "fields": {"Lifecycle": "Stable"}})
    assert first.status == 200, first.body
    second = served.patch("/api/capabilities/cli%2Fx",
                          {"revision": revision, "fields": {"Lifecycle": "Deprecated"}})
    assert_error(second, 409, "stale-revision")


def test_the_revision_covers_the_inherited_member(family, served):
    core, _ = family
    revision = detail(served, "capabilities", "cli%2Fx")["coreRevision"]
    (core / "docs" / "capabilities" / "cli" / "x" / "description.md").write_text(
        "Core body, changed")
    answer = served.patch("/api/capabilities/cli%2Fx",
                          {"revision": revision, "fields": {"Lifecycle": "Stable"}})
    assert_error(answer, 409, "stale-revision")
