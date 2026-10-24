"""The web server names taxonomy entries and capabilities by full identifier
(TCW-110 Design 4.5, AC 20): records carry `full-id` and `owner`, and an
inherited entry is read at its encoded full identifier."""

from __future__ import annotations

from urllib.parse import quote

import pytest

from tests.inherit import demo_inheriting_core
from tests.statefiles import TAXONOMY_STATE

STRIPPED = {"slug", "qualified", "path", "origin"}


@pytest.fixture
def served(tmp_path, serve_project):
    return serve_project(demo_inheriting_core(tmp_path))


@pytest.mark.parametrize("route, key, full_id", [
    ("/api/taxonomy/term", "term", "demo.taxonomy/term"),
    ("/api/capabilities/cli%2Fx", "capability", "demo.capabilities/cli/x"),
])
def test_ac20_a_record_carries_full_id_and_owner(served, route, key, full_id):
    answer = served.get(route)
    assert answer.status == 200, answer.body
    record = answer.json[key]
    assert (record["full-id"], record["owner"]) == (full_id, "demo")
    assert not STRIPPED & set(record)


@pytest.mark.parametrize("route", ["/api/taxonomy", "/api/capabilities"])
def test_ac20_listed_records_carry_full_id_and_owner(served, route):
    records = served.get(route).json
    assert {r["owner"] for r in records} == {"demo", "core"}
    assert all(not STRIPPED & set(r) for r in records)


@pytest.mark.parametrize("axis, key, full_id", [
    ("taxonomy", "term", "core.taxonomy/shared"),
    ("capabilities", "capability", "core.capabilities/cli/y"),
])
def test_ac20_an_inherited_entry_is_read_at_its_full_identifier(served, axis, key,
                                                                full_id):
    answer = served.get(f"/api/{axis}/{quote(full_id, safe='')}")
    assert answer.status == 200, answer.body
    assert answer.json[key]["full-id"] == full_id
    assert answer.json[key]["owner"] == "core"


def test_an_inherited_entry_is_read_only_named_by_its_full_identifier(served):
    full_id = "core.taxonomy/shared"
    revision = served.get(f"/api/taxonomy/{quote(full_id, safe='')}").json["coreRevision"]
    answer = served.patch(f"/api/taxonomy/{quote(full_id, safe='')}",
                          {"revision": revision, "fields": {"name": "Mine"}})
    assert answer.status == 403, answer.body
    assert answer.json["error"].startswith(f"{full_id} is inherited from 'core'")


def test_ac8_a_web_edit_stores_the_full_identifier_of_a_reference(served):
    """TCW-110 Design 5.3: a reference typed as an id-path is stored in full."""
    revision = served.get("/api/taxonomy/term").json["coreRevision"]
    answer = served.patch("/api/taxonomy/term", {"revision": revision,
                                                 "fields": {"relatesTo": ["shared"]}})
    assert answer.status == 200, answer.body
    meta = served.root / "docs" / "taxonomy" / "term" / TAXONOMY_STATE
    assert "core.taxonomy/shared" in meta.read_text()


# -- /api/resolve (TCW-110 Design 4.5, AC 20) --------------------------------------------


def _resolve(served, uri):
    answer = served.post("/api/resolve", {"uris": [uri]})
    assert answer.status == 200, answer.body
    return answer.json[uri]


@pytest.mark.parametrize("uri, axis, key", [
    ("tcw://demo.capabilities/cli/x", "capabilities", "cli/x"),
    ("tcw://demo.taxonomy/term", "taxonomy", "term"),
    ("tcw://core.capabilities/cli/y", "capabilities", "core.capabilities/cli/y"),
])
def test_ac20_a_link_resolves_to_its_route_key(served, uri, axis, key):
    assert _resolve(served, uri) == {"ok": True, "axis": axis, "key": key}


def test_ac20_a_link_into_a_project_not_inherited_from_is_other_project(tmp_path,
                                                                       serve_project):
    from tcw.store.fs import init
    from tests.inherit import entry
    from tests.projectfiles import connect_projects
    from tests.work.projects import make_project
    app = make_project(tmp_path, "app", config={})
    core = make_project(tmp_path, "core", config={})
    init(["taxonomy", "capabilities"], core)
    entry(core, "taxonomy", "term")
    connect_projects(app, "parent", "core", inherit="none")
    found = _resolve(serve_project(app), "tcw://core.taxonomy/term")
    assert found == {"ok": False, "reason": "other-project", "project": "core"}
