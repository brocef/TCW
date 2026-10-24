"""The web router makes the ownership check (TCW-114 AC 4, the server half;
Design 1.2, 1.4; plan Step 4): every route that writes says what it writes,
and the router refuses another project's object, 403 `read-only`, before
the route's handler runs."""

from __future__ import annotations

import re

import pytest

from tcw.ids import FullId
from tcw.serve.server import Written, _routes, route
from tests.objectcli import obj, project
from tests.projectfiles import connect_projects, write_manifest
from tests.serve.test_records import assert_error

WRITES = {
    ("POST", "/api/work"), ("PATCH", "/api/work/x"), ("POST", "/api/work/x/comments"),
    # The `/blocks` route is removed in Step 7 of the plan.
    ("POST", "/api/work/x/blocks"),
    ("POST", "/api/tickets/X-1/adopt"), ("PUT", "/api/work/x/files/spec/spec.md"),
    ("POST", "/api/work/x/files"), ("PUT", "/api/work/x/declaration"),
    ("POST", "/api/taxonomy"), ("PATCH", "/api/taxonomy/x"),
    ("POST", "/api/capabilities"), ("PATCH", "/api/capabilities/x"),
}
CREATORS = {("POST", "/api/work"), ("POST", "/api/tickets/X-1/adopt"),
            ("POST", "/api/taxonomy"), ("POST", "/api/capabilities")}


def _matching(method: str, path: str):
    return next(r for r in _routes() if r.method == method and r.pattern.fullmatch(path))


def test_the_routes_that_write_are_exactly_design_1_2s():
    marked = set()
    for found in _routes():
        if found.writes is None:
            continue
        sample = next(p for m, p in WRITES if m == found.method
                      and found.pattern.fullmatch(p)) if any(
            m == found.method and found.pattern.fullmatch(p) for m, p in WRITES) else None
        assert sample is not None, f"{found.method} {found.pattern.pattern} writes"
        marked.add((found.method, sample))
    assert marked == WRITES
    assert _matching("POST", "/api/resolve").writes is None


@pytest.mark.parametrize("method,path", sorted(CREATORS))
def test_a_creator_names_nothing_for_the_router_to_check(method, path):
    found = _matching(method, path)
    assert found.writes(object()) == []


@pytest.fixture
def family(tmp_path):
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    connect_projects(app, "parent", "core", inherit=["taxonomy", "capabilities"])
    write_manifest(app, {"core": "../core"})
    obj(core, "taxonomy", "t", name="T", kind="Vocabulary")
    obj(core, "capabilities", "cli/x", name="X", Status="Missing")
    return app, core


def test_a_marked_route_is_refused_before_its_handler_runs(family, serve_project):
    app, core = family
    made = app / "made.txt"

    def handler(request):
        made.write_text("written")
        return 200, {}
    served = serve_project(app)
    served.server.routes.insert(0, route(
        "POST", r"/api/test-write", handler,
        writes=lambda request: [Written(FullId("core", "capabilities", "cli/x"))]))
    answer = served.post("/api/test-write", {})
    assert_error(answer, 403, "read-only")
    assert "belongs to project 'core'" in answer.json["error"]
    assert f"tcw -C {core.resolve()}" in answer.json["error"]
    assert not made.exists()


@pytest.mark.parametrize("key", ["cli%2Fx", "core.capabilities%2Fcli%2Fx"])
def test_patching_an_inherited_capability_is_refused_with_the_cli_hint(
        family, serve_project, key):
    app, core = family
    served = serve_project(app)
    answer = served.patch(f"/api/capabilities/{key}", {"revision": "r",
                                                       "fields": {"Lifecycle": "Stable"}})
    assert_error(answer, 403, "read-only")
    message = answer.json["error"]
    assert message.startswith("core.capabilities/cli/x belongs to project 'core'; "
                              f"run the command there: tcw -C {core.resolve()} …")
    assert message.endswith("; or override it in this project with `tcw capabilities "
                            "set cli/x --field <name>=<value>`")


def test_patching_an_inherited_term_is_refused_with_no_hint(family, serve_project):
    app, core = family
    answer = serve_project(app).patch("/api/taxonomy/core.taxonomy%2Ft",
                                      {"revision": "r", "name": "U"})
    assert_error(answer, 403, "read-only")
    assert answer.json["error"] == (f"core.taxonomy/t belongs to project 'core'; run "
                                    f"the command there: tcw -C {core.resolve()} …")


def test_a_full_identifier_of_a_project_nothing_names_is_refused_not_missing(
        family, serve_project):
    """The check comes before the lookup (spec 1.1, review M4): a project
    that is not here is a 403, not a 404."""
    app, _ = family
    answer = serve_project(app).patch("/api/capabilities/zz.capabilities%2Fa",
                                      {"revision": "r", "fields": {}})
    assert_error(answer, 403, "read-only")
    assert re.search(r"project 'zz' is not on this machine$", answer.json["error"])


@pytest.mark.parametrize("method,path,body", [
    ("PATCH", "/api/work/core.work%2F2026-10-01-c", {"changes": {"priority": "low"},
                                                     "expected": {"priority": None}}),
    ("POST", "/api/work/core.work%2F2026-10-01-c/comments", {"text": "hi"}),
    ("PUT", "/api/work/core.work%2F2026-10-01-c/files/request/request.md",
     {"content": "x", "revision": None}),
    ("PUT", "/api/work/core.work%2F2026-10-01-c/declaration",
     {"revision": None, "capabilities": {}, "taxonomy": {}}),
])
def test_a_work_route_naming_another_projects_item(family, serve_project, method,
                                                    path, body):
    app, core = family
    answer = serve_project(app).request(method, path, body)
    assert_error(answer, 403, "read-only")
    assert "core.work/2026-10-01-c belongs to project 'core'" in answer.json["error"]
