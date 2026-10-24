"""TCW-113 Design 6.3-6.5 (plan Step 14): any object TCW can locate can be
read from its owner, and every write names the object by its owner. AC 34.
`tcw serve` runs in `shared` of the family `F` (`tests/families.py`)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from tcw.serve.server import route
from tests.families import build_family, item_folder, jira_mode
from tests.work.jira.fake import FakeJira

DESKTOP_ITEM = f"desktop.work/{item_folder('desktop')}"
K = quote(DESKTOP_ITEM, safe="")


@pytest.fixture
def family(tmp_path):
    family = build_family(tmp_path, docs_passes="none")
    folder = family["desktop"] / "docs" / "work" / item_folder("desktop")
    (folder / "request").mkdir(exist_ok=True)
    (folder / "request" / "request.md").write_text("desktop's request\n", encoding="utf-8")
    (folder / "capabilities.yaml").write_text("new:\n  - desktop.capabilities/def\n",
                                              encoding="utf-8")
    return family


@pytest.fixture
def shared(family, serve_project):
    return serve_project(family["shared"])


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


def assert_error(answer, status: int, code: str):
    assert answer.status == status, answer.body
    assert answer.json["code"] == code, answer.body


# -- AC 34: the reads ------------------------------------------------------------------


def test_ac34_another_projects_item_is_read_from_its_owner(shared):
    answer = shared.get(f"/api/work/{K}")
    assert answer.status == 200, answer.body
    assert answer.json["item"]["full-id"] == DESKTOP_ITEM
    assert answer.json["item"]["owner"] == "desktop"
    assert answer.json["folder"] == item_folder("desktop")


def test_ac34_its_files_and_declaration_come_from_its_folder(shared):
    found = shared.get(f"/api/work/{K}/files/request/request.md")
    assert found.status == 200, found.body
    assert found.json["content"] == "desktop's request\n"
    declared = shared.get(f"/api/work/{K}/declaration")
    assert declared.status == 200, declared.body
    assert declared.json["present"] is True
    assert declared.json["capabilities"]["new"] == ["desktop.capabilities/def"]


WRITES = [
    ("PATCH", f"/api/work/{K}", {"changes": {"priority": "low"},
                                 "expected": {"priority": None}}),
    ("POST", f"/api/work/{K}/comments", {"text": "hi"}),
    ("PUT", f"/api/work/{K}/files/request/request.md", {"content": "x", "revision": None}),
    ("POST", f"/api/work/{K}/files", {"stage": "spec", "kind": "document"}),
    ("PUT", f"/api/work/{K}/declaration", {"revision": None, "capabilities": {},
                                           "taxonomy": {}}),
    ("PATCH", "/api/work/" + quote("desktop.work/no-such-item", safe=""),
     {"changes": {"priority": "low"}, "expected": {"priority": None}}),
]


@pytest.mark.parametrize("method,path,body", WRITES)
def test_ac34_each_write_is_refused_and_nothing_changes(family, shared, method, path,
                                                        body):
    before = snapshot(family["desktop"])
    answer = shared.request(method, path, body)
    assert_error(answer, 403, "read-only")
    assert "belongs to project 'desktop'" in answer.json["error"]
    assert snapshot(family["desktop"]) == before


def test_ac34_another_projects_capability_reads_under_down(shared):
    answer = shared.get("/api/capabilities/" + quote("desktop.capabilities/abc", safe="")
                        + "?scope=down")
    assert answer.status == 200, answer.body
    assert answer.json["capability"]["full-id"] == "desktop.capabilities/abc"


def test_ac34_a_link_to_another_projects_item_resolves(shared):
    there, missing = f"tcw://{DESKTOP_ITEM}", "tcw://mobile.work/x"
    answer = shared.post("/api/resolve", {"uris": [there, missing]})
    assert answer.status == 200
    assert answer.json[there] == {"ok": True, "axis": "work", "key": DESKTOP_ITEM}
    assert answer.json[missing] == {"ok": False, "reason": "other-project",
                                    "project": "mobile"}


# -- AC 34: a project TCW cannot find ----------------------------------------------------


def test_ac34_a_project_nothing_knows_is_not_found(shared):
    for path in ("/api/work/" + quote("nosuch.work/x", safe=""),
                 "/api/taxonomy/" + quote("nosuch.taxonomy/x", safe=""),
                 "/api/capabilities/" + quote("nosuch.capabilities/x", safe="")):
        assert_error(shared.get(path), 404, "not-found")


def test_a_project_declared_but_not_here_is_unreachable(shared):
    assert_error(shared.get("/api/work/" + quote("mobile.work/x", safe="")), 503,
                 "unreachable")


# -- the work route key rule --------------------------------------------------------------


def test_the_work_route_key_rule_opens_nothing(family, shared, monkeypatch):
    from tcw.serve import work
    opened = []
    monkeypatch.setattr("tcw.work.open.open_backend",
                        lambda *a, **kw: opened.append(a))

    class Request:
        root = family["shared"]
    for text, project, name in (("desktop.work/x", "desktop", "x"),
                                ("desktop.work/APP-7", "desktop", "APP-7"),
                                ("x", "shared", "x"), ("APP-7", "shared", "APP-7")):
        key = work.work_key(Request(), text)
        assert (key.project, key.name) == (project, name), text
        assert (key.full is not None) == ("." in text)
    assert opened == []


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("TCW_TEST_JIRA_EMAIL", "dev@example.test")
    monkeypatch.setenv("TCW_TEST_JIRA_TOKEN", "token")
    fake = FakeJira().install(monkeypatch)
    fake.account("dev@example.test", "a-1", "Ann")
    return fake


def test_the_ticket_key_form_names_another_projects_item(family, fake, serve_project):
    renamed = jira_mode(family, "desktop", fake)
    folder = renamed[item_folder("desktop")]
    ticket = folder.split("-")[0] + "-" + folder.split("-")[1]
    key = quote(f"desktop.work/{ticket}", safe="")
    served = serve_project(family["shared"])
    answer = served.get(f"/api/work/{key}")
    assert answer.status == 200, answer.body
    assert answer.json["item"]["full-id"] == f"desktop.work/{folder}"
    refused = served.patch(f"/api/work/{key}", {"changes": {"priority": "low"},
                                                 "expected": {"priority": None}})
    assert_error(refused, 403, "read-only")
    assert "belongs to project 'desktop'" in refused.json["error"]


# -- Design 6.5's second paragraph: the write handlers stay in the served project --------


HANDLERS = {
    "edit": ("PATCH", r"/api/test/([^/]+)", {"changes": {"priority": "low"},
                                              "expected": {"priority": None}}),
    "add_comment": ("POST", r"/api/test/([^/]+)/comments", {"text": "hi"}),
    "put_file": ("PUT", r"/api/test/([^/]+)/files/(.+)",
                 {"content": "x", "revision": None}),
    "new_file": ("POST", r"/api/test/([^/]+)/files", {"stage": "spec",
                                                       "kind": "document"}),
    "put_declaration": ("PUT", r"/api/test/([^/]+)/declaration",
                        {"revision": None, "capabilities": {}, "taxonomy": {}}),
}


@pytest.mark.parametrize("name", sorted(HANDLERS))
def test_a_write_handler_reached_unchecked_answers_404(family, shared, name):
    from tcw.serve import files, work
    handler = getattr(work, name, None) or getattr(files, name)
    method, pattern, body = HANDLERS[name]
    shared.server.routes.insert(0, route(method, pattern, handler))
    path = pattern.replace("([^/]+)", K).replace("(.+)", "request/request.md")
    # `shared` has an item at the same folder name, which a handler that
    # read only the key's id-path would write.
    family.item("shared", item_folder("desktop"))
    before = snapshot(family["desktop"]), snapshot(family["shared"])
    answer = shared.request(method, path, body)
    assert_error(answer, 404, "not-found")
    assert (snapshot(family["desktop"]), snapshot(family["shared"])) == before
