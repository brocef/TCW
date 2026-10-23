"""The work API's writes: properties, comments, creating, blocks, tickets and
suggestions (TCW-77 criteria 4's credential marker, 8, 9, 10's write parts
and 12's server half)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.errors import Refused
from tests.serve.conftest import fs_project
from tests.serve.memory import ME
from tests.serve.test_work_read import new, ok
from tests.work.jira.conftest import EMAIL_ENV, TOKEN_ENV
from tests.work.projects import commit_all, connect, git, make_project
from tests.projectfiles import config_file, write_config_file
from tests.projectfiles import write_connected_config_file


def item_yaml(root: Path, folder: str) -> dict:
    return yaml.safe_load((root / "docs" / "work" / folder / "item.yaml").read_text())


def assert_refused(answer, status: int, code: str, *named: str):
    assert answer.status == status, answer.body
    assert answer.json["code"] == code
    for name in named:
        assert name in answer.json["error"], answer.json["error"]


def state(root: Path) -> tuple[str, str]:
    """A repository's commit and every file not committed: what "nothing
    was written" compares."""
    return (git(root, "rev-parse", "HEAD"),
            git(root, "status", "--porcelain", "--untracked-files=all"))


@dataclass
class Family:
    served: object
    p: Path
    q: Path
    r: Path
    upstream_item: str


@pytest.fixture
def family(tmp_path, personal_on, serve_project, tcw):
    """`p` (served) with child `q` and upstream `r`, each its own committed
    repository; `r` holds one item."""
    p = fs_project(tmp_path, tags=("ui", "api"))
    q = make_project(tmp_path, "q")
    r = make_project(tmp_path, "r")
    connect(p, q, "children")
    connect(q, p, "parent")
    connect(p, r, "upstream")
    upstream_item = new(tcw, r, "Upstream thing")
    for root in (p, q, r):
        commit_all(root)
    return Family(serve_project(p), p, q, r, upstream_item)


@pytest.fixture
def two(fs, tcw):
    """Two items, A and B, in the served filesystem project."""
    return new(tcw, fs.root, "Item A"), new(tcw, fs.root, "Item B")


def patch(served, folder, changes, expected):
    return served.patch(f"/api/work/{folder}", {"changes": changes,
                                                 "expected": expected})


# -- properties ---------------------------------------------------------------------------


def test_a_property_change_checks_what_the_form_loaded(fs, two):
    a, _ = two
    changed = ok(patch(fs, a, {"priority": "high"}, {"priority": "medium"}))
    assert changed["item"]["priority"] == "high"
    assert item_yaml(fs.root, a)["priority"] == "high"
    again = patch(fs, a, {"priority": "low"}, {"priority": "medium"})
    assert_refused(again, 409, "stale-revision", "priority")
    assert item_yaml(fs.root, a)["priority"] == "high"


def test_expected_is_required_for_each_changed_property(fs, two):
    a, _ = two
    assert patch(fs, a, {"priority": "high"}, {}).status == 400


def test_an_unregistered_tag_is_refused(fs, two):
    a, _ = two
    before = item_yaml(fs.root, a)
    answer = patch(fs, a, {"tags": {"add": ["unregistered"]}}, {"tags": []})
    assert_refused(answer, 400, "usage", "unregistered")
    assert item_yaml(fs.root, a) == before


def test_a_tag_since_unregistered_does_not_block_other_edits(fs, two, tcw):
    a, _ = two
    ok(patch(fs, a, {"tags": {"add": ["ui"]}}, {"tags": []}))
    config = config_file(fs.root)
    document = yaml.safe_load(config.read_text())
    document["work"]["tags"] = ["api"]
    write_connected_config_file(config, yaml.safe_dump(document))
    ok(patch(fs, a, {"priority": "low"}, {"priority": "medium"}))
    assert item_yaml(fs.root, a)["tags"] == ["ui"]


def test_a_local_parent_must_be_an_item_here(fs, two):
    a, b = two
    refused = patch(fs, a, {"parent": "2026-01-01-nothing"}, {"parent": None})
    assert_refused(refused, 400, "usage", "parent", "2026-01-01-nothing")
    ok(patch(fs, a, {"parent": b}, {"parent": None}))
    assert item_yaml(fs.root, a)["parent"] == f"p.work/{b}"


@pytest.mark.parametrize("value", ["not a slug!", "a.work/b c"])
def test_a_parent_that_is_not_a_slug_is_refused(fs, two, value):
    a, _ = two
    assert_refused(patch(fs, a, {"parent": value}, {"parent": None}), 400, "usage")


def test_a_parent_of_several_parts_names_no_item(fs, two):
    """A work id-path is one folder name, so `a/b/c`, like a 3.x
    `<project>/<folder>`, names no item (TCW-110 Design 3.4)."""
    a, _ = two
    assert_refused(patch(fs, a, {"parent": "a/b/c"}, {"parent": None}), 404, "not-found")


def test_another_projects_parent_is_kept_with_a_warning(fs, two):
    a, _ = two
    answer = ok(patch(fs, a, {"parent": "other-project.work/2026-01-01-x"}, {"parent": None}))
    assert answer["item"]["parent"] == "other-project.work/2026-01-01-x"
    assert any(w["where"] == "parent" and "other-project" in w["message"]
               for w in answer["warnings"])


def test_a_local_blocker_must_be_an_item_here(fs, two):
    a, b = two
    refused = patch(fs, a, {"blocked-by": {"add": ["2026-01-01-nothing"]}},
                    {"blocked-by": []})
    assert_refused(refused, 400, "usage", "blocked-by")
    ok(patch(fs, a, {"blocked-by": {"add": [b]}}, {"blocked-by": []}))
    stale = patch(fs, a, {"blocked-by": {"remove": [f"p.work/{b}"]}}, {"blocked-by": []})
    assert_refused(stale, 409, "stale-revision", "blocked-by")


def test_another_projects_blocker_is_kept_with_a_warning(fs, two):
    a, _ = two
    answer = ok(patch(fs, a, {"blocked-by": {"add": ["other-project.work/2026-01-01-x"]}},
                      {"blocked-by": []}))
    assert answer["item"]["blocked-by"] == ["other-project.work/2026-01-01-x"]
    assert any(w["where"] == "blocked-by" for w in answer["warnings"])


@pytest.mark.parametrize("changes", [
    {"priority": "urgent"}, {"effort": "huge"}, {"stage": "completed"},
    {"title": ""}, {"tags": ["ui"]},
])
def test_malformed_changes_are_refused(fs, two, changes):
    a, _ = two
    before = item_yaml(fs.root, a)
    expected = {k: None for k in changes}
    assert patch(fs, a, changes, expected).status == 400
    assert item_yaml(fs.root, a) == before


# -- blocks ----------------------------------------------------------------------------------


def test_blocks_adds_this_item_to_the_targets_blocked_by(fs, two):
    a, b = two
    ok(fs.post(f"/api/work/{a}/blocks", {"target": b, "expected": False}))
    assert item_yaml(fs.root, b)["blocked-by"] == [f"p.work/{a}"]
    assert ok(fs.get(f"/api/work/{a}"))["item"]["blocks"] == [f"p.work/{b}"]
    again = fs.post(f"/api/work/{a}/blocks", {"target": b, "expected": False})
    assert_refused(again, 409, "stale-revision")


def test_blocks_needs_expected_false(fs, two):
    a, b = two
    assert fs.post(f"/api/work/{a}/blocks", {"target": b}).status == 400


def test_blocks_an_unknown_local_item_is_refused(fs, two):
    a, _ = two
    answer = fs.post(f"/api/work/{a}/blocks", {"target": "2026-01-01-nothing",
                                                "expected": False})
    assert_refused(answer, 400, "usage")


def test_blocks_into_a_connected_project(family, tcw):
    theirs = new(tcw, family.q, "Theirs")
    commit_all(family.q)
    mine = new(tcw, family.p, "Mine")
    ok(family.served.post(f"/api/work/{mine}/blocks", {"target": f"q.work/{theirs}",
                                                        "expected": False}))
    assert item_yaml(family.q, theirs)["blocked-by"] == [f"p.work/{mine}"]


def test_blocks_into_an_upstream_is_refused(family, tcw):
    mine = new(tcw, family.p, "Mine")
    before = state(family.r)
    answer = family.served.post(f"/api/work/{mine}/blocks", {
        "target": f"r.work/{family.upstream_item}", "expected": False})
    assert_refused(answer, 409, "refused", "read-only")
    assert state(family.r) == before


# -- comments ----------------------------------------------------------------------------------


def test_a_comment_is_added_and_shown(fs, two):
    a, _ = two
    assert fs.post(f"/api/work/{a}/comments", {"text": "a thought"}).status == 201
    assert [c["text"] for c in ok(fs.get(f"/api/work/{a}"))["comments"]] == ["a thought"]
    assert fs.post(f"/api/work/{a}/comments", {"text": "  "}).status == 400


@pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
def test_no_route_edits_or_removes_a_comment(fs, two, method):
    a, _ = two
    body = {} if method != "DELETE" else None
    answer = fs.request(method, f"/api/work/{a}/comments/1", body) if body is not None \
        else fs.request(method, f"/api/work/{a}/comments/1")
    assert answer.status == 404


# -- creating ------------------------------------------------------------------------------------


def test_creating_here_calls_new_with_the_request(fs):
    answer = fs.post("/api/work", {"title": "Fresh", "requestText": "please do\n",
                                   "properties": {"priority": "high", "tags": ["ui"]}})
    assert answer.status == 201, answer.body
    slug = answer.json["full-id"]
    folder = slug.split("/", 1)[1]
    assert slug.startswith("p.work/")
    data = item_yaml(fs.root, folder)
    assert (data["priority"], data["tags"]) == ("high", ["ui"])
    request = fs.root / "docs" / "work" / folder / "request" / "request.md"
    assert request.read_text() == "please do\n"


def test_creating_at_the_inbox(fs):
    answer = fs.post("/api/work", {"title": "Raw", "stage": "inbox"})
    assert answer.status == 201
    assert item_yaml(fs.root, answer.json["full-id"].split("/")[1])["stage"] == "inbox"


def test_creating_into_a_connected_project(family):
    before = state(family.p)
    answer = family.served.post("/api/work", {
        "title": "Please help", "requestText": "details\n", "project": "q",
        "properties": {"priority": "high"}})
    assert answer.status == 201, answer.body
    slug = answer.json["full-id"]
    assert slug.startswith("q.work/")
    data = item_yaml(family.q, slug.split("/")[1])
    assert (data["stage"], data["priority"]) == ("inbox", "high")
    assert state(family.p) == before


def test_another_project_takes_only_title_request_and_priority(family):
    before = sorted(os.listdir(family.q / "docs" / "work"))
    answer = family.served.post("/api/work", {
        "title": "Please help", "project": "q",
        "properties": {"priority": "high", "tags": ["ui"]}})
    assert_refused(answer, 400, "usage", "tags")
    assert sorted(os.listdir(family.q / "docs" / "work")) == before


def test_targets_delegation_refuses(family, tmp_path):
    cases = {"nobody": "no project", "r": "read-only"}
    for target, message in cases.items():
        answer = family.served.post("/api/work", {"title": "T", "project": target})
        assert_refused(answer, 409, "refused", message)
    assert state(family.r)[1] == ""
    shutil.rmtree(family.q)
    absent = family.served.post("/api/work", {"title": "T", "project": "q"})
    assert_refused(absent, 409, "refused", "not on this machine")


@pytest.mark.parametrize("properties", [
    {"parent": "2026-01-01-nothing"}, {"blocked-by": ["2026-01-01-nothing"]},
    {"tags": ["unregistered"]}, {"priority": "urgent"}, {"effort": "huge"},
])
def test_creating_with_a_refused_value_creates_nothing(fs, properties):
    before = sorted(os.listdir(fs.root / "docs" / "work"))
    answer = fs.post("/api/work", {"title": "T", "properties": properties})
    assert_refused(answer, 400, "usage")
    assert sorted(os.listdir(fs.root / "docs" / "work")) == before


def test_creating_needs_a_title(fs):
    assert fs.post("/api/work", {"title": "  "}).status == 400


# -- Jira mode ------------------------------------------------------------------------------------


def test_jira_owned_content_is_read_only(jira):
    served = jira.served
    for answer in (
            patch(served, "TCW-1-first", {"priority": "high"}, {"priority": "medium"}),
            served.post("/api/work/TCW-1-first/comments", {"text": "hi"}),
            served.post("/api/work/TCW-1-first/blocks", {"target": "TCW-2-second",
                                                         "expected": False})):
        assert_refused(answer, 403, "read-only")
    assert not jira.backend.named("update") and not jira.backend.named("comment")


def test_jira_create_carries_a_refused_tickets_key(jira, monkeypatch):
    def refuse(*args, **kwargs):
        raise Refused("no single transition reaches the request status", name="ABC-9")

    monkeypatch.setattr(jira.backend, "create", refuse)
    answer = jira.served.post("/api/work", {"title": "T", "requestText": "x"})
    assert_refused(answer, 409, "refused", "transition")
    assert answer.json["ticket"] == "ABC-9"


def test_jira_create_blocked_by_only_this_projects_items(jira):
    for blocker in ("TCW-9-nothing", "other.work/2026-01-01-x"):
        answer = jira.served.post("/api/work", {"title": "T", "properties": {
            "blocked-by": [blocker]}})
        assert_refused(answer, 400, "usage", "blocked-by")
    assert not jira.backend.named("create")
    answer = jira.served.post("/api/work", {"title": "T", "properties": {
        "blocked-by": ["TCW-2-second"]}})
    assert answer.status == 201, answer.body


def test_jira_tickets_and_adopt(jira):
    jira.stubs.tickets = [{"key": "TCW-7", "summary": "Waiting"}]
    found = ok(jira.served.get("/api/tickets"))
    assert found["tickets"] == [{"key": "TCW-7", "summary": "Waiting"}]
    adopted = jira.served.post("/api/tickets/TCW-7/adopt", {})
    assert adopted.status == 201 and adopted.json["full-id"] == "tcw.work/TCW-7-adopted"
    assert (adopted.json["code"], adopted.json["problem"]) == (0, None)


def test_tickets_are_a_usage_error_in_filesystem_mode(fs):
    assert_refused(fs.get("/api/tickets"), 400, "usage")
    assert_refused(fs.post("/api/tickets/ABC-1/adopt", {}), 400, "usage")


def test_assignee_suggestions_ask_for_ten(jira):
    found = ok(jira.served.get("/api/options/assignee?q=al"))
    assert jira.stubs.calls[-1] == ("assignable_users", "al", 10)
    assert found == [{"id": "acc-alf", "name": "Alf Alpha"}]


def test_assignee_suggestions_are_a_usage_error_in_filesystem_mode(fs):
    assert_refused(fs.get("/api/options/assignee?q=al"), 400, "usage")


def test_work_suggestions_come_from_connected_filesystem_projects(family, tcw):
    theirs = new(tcw, family.q, "Shared widget")
    found = ok(family.served.get("/api/options/work?q=widget"))
    assert found == [{"full-id": f"q.work/{theirs}", "title": "Shared widget",
                      "stage": "request", "project": "q"}]


def test_an_unknown_suggestion_field_is_404(fs):
    assert fs.get("/api/options/nonsense?q=x").status == 404


# -- credentials never leave the server ------------------------------------------------------------

MARKER = "s3cr3t-marker-7731"


def every_route(served, folder: str) -> list:
    """One request to every route, valid where the fixture allows."""
    calls = [
        ("GET", "/api/project", None), ("GET", "/api/work", None),
        ("GET", "/api/work?all=1&tag=ui", None), ("GET", f"/api/work/{folder}", None),
        ("GET", f"/api/work/{folder}/files/spec/spec.md", None),
        ("PUT", f"/api/work/{folder}/files/spec/spec.md",
         {"content": "# Spec\n", "revision": None}),
        ("POST", f"/api/work/{folder}/files", {"stage": "implement", "kind": "round"}),
        ("GET", f"/api/work/{folder}/declaration", None),
        ("PUT", f"/api/work/{folder}/declaration",
         {"capabilities": {"new": ["x"]}, "revision": None}),
        ("PATCH", f"/api/work/{folder}", {"changes": {"priority": "high"},
                                          "expected": {"priority": "medium"}}),
        ("POST", f"/api/work/{folder}/comments", {"text": "hi"}),
        ("POST", f"/api/work/{folder}/blocks", {"target": "nothing", "expected": False}),
        ("POST", "/api/work", {"title": "New one"}),
        ("GET", "/api/tickets", None), ("POST", "/api/tickets/TCW-7/adopt", {}),
        ("GET", "/api/options/assignee?q=a", None), ("GET", "/api/options/work?q=a", None),
        ("GET", "/api/taxonomy", None), ("GET", "/api/capabilities", None),
        ("POST", "/api/resolve", {"uris": [f"tcw://W/{folder}"]}),
        ("GET", "/", None), ("GET", "/api/nope", None),
    ]
    return [served.request(m, p) if b is None else served.request(m, p, b)
            for m, p, b in calls]


def test_no_answer_carries_the_jira_credentials(jira, monkeypatch):
    monkeypatch.setenv(EMAIL_ENV, MARKER)
    monkeypatch.setenv(TOKEN_ENV, MARKER)
    answers = every_route(jira.served, "TCW-1-first")
    assert any(a.status == 200 for a in answers)
    for answer in answers:
        assert MARKER not in answer.body.decode("utf-8", "replace")
        assert all(MARKER not in v for v in answer.headers.values())


def test_the_current_user_is_offered(jira):
    assert ok(jira.served.get("/api/project"))["user"] == ME


# -- review round 1 ---------------------------------------------------------------------------


def test_a_reference_to_a_stray_folder_is_refused(fs, two):
    a, _ = two
    (fs.root / "docs" / "work" / "notes").mkdir()
    before = item_yaml(fs.root, a)
    assert_refused(patch(fs, a, {"parent": "notes"}, {"parent": None}), 400, "usage",
                   "parent")
    assert_refused(patch(fs, a, {"blocked-by": {"add": ["notes"]}},
                         {"blocked-by": []}), 400, "usage", "blocked-by")
    assert item_yaml(fs.root, a) == before


def test_jira_create_keeps_another_projects_parent_with_a_warning(jira):
    """Spec 9's parent row: the backend decides whether it can hold it."""
    answer = jira.served.post("/api/work", {"title": "T", "properties": {
        "parent": "other.work/2026-01-01-x"}})
    assert answer.status == 201, answer.body
    assert [w["where"] for w in answer.json["warnings"]] == ["parent"]
    assert jira.backend.named("create")


def test_jira_create_checks_the_assignee_is_assignable(jira):
    for value in ("Ann Author", "acc-nobody"):
        answer = jira.served.post("/api/work", {"title": "T", "properties": {
            "assignee": value}})
        assert_refused(answer, 400, "usage", "assignee", value)
    assert not jira.backend.named("create")
    answer = jira.served.post("/api/work", {"title": "T", "properties": {
        "assignee": "acc-ann"}})
    assert answer.status == 201, answer.body
    assert ("is_assignable", "acc-ann") in jira.stubs.calls


def test_jira_create_with_a_name_that_is_not_a_tag_is_a_usage_error(jira):
    answer = jira.served.post("/api/work", {"title": "T", "properties": {
        "tags": ["!!"]}})
    assert_refused(answer, 400, "usage", "'!!'")
    assert not jira.backend.named("create")


@pytest.fixture
def adopting(tmp_path, monkeypatch, personal_on, serve_project):
    """A Jira-mode project on TCW-71's real backend over its fake, served
    with the real services; `make(command)` sets the request stage's post
    hook and returns the served project and an inbox ticket's key."""
    from tests.work.jira.conftest import ME as JIRA_ME, jira_config as config_of
    from tests.work.jira.fake import FakeJira
    monkeypatch.setenv(EMAIL_ENV, "dev@example.test")
    monkeypatch.setenv(TOKEN_ENV, "token")
    fake = FakeJira().install(monkeypatch)
    fake.account("dev@example.test", JIRA_ME, "Dev Eloper")

    def make(command: str):
        config = config_of()
        config["stages"]["request"]["post"] = [{"command": command}]
        root = make_project(tmp_path, "tcw", config=config)
        commit_all(root)
        return serve_project(root), fake.ticket("Adopt me", status="To Do").key
    return make


def test_adopting_runs_the_request_stages_post_hook(adopting, tmp_path):
    ran = tmp_path / "hook-ran"
    served, key = adopting(f"echo $TCW_SLUG > {ran}")
    answer = served.post(f"/api/tickets/{key}/adopt", {})
    assert answer.status == 201, answer.body
    slug = f"tcw.work/{key}-adopt-me"
    assert answer.json == {"full-id": slug, "code": 0, "problem": None}
    assert ran.read_text().strip() == slug


def test_a_failed_adopt_hook_keeps_the_item_and_says_what_failed(adopting):
    served, key = adopting("echo the hook broke >&2; exit 7")
    answer = served.post(f"/api/tickets/{key}/adopt", {})
    assert answer.status == 201, answer.body
    assert answer.json["code"] == 6
    problem = answer.json["problem"]
    assert problem.startswith(f"adopted {key} as tcw.work/{key}-adopt-me, but"), problem
    assert (served.root / "docs" / "work" / f"{key}-adopt-me").is_dir()
