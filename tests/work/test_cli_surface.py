"""The `tcw work` surface TCW-73 fixes (Design 1.6, 1.9, 2; AC 3, 8, 10, 19, 28).

What each command prints and which spellings it accepts. What the commands do
to items is TCW-70's and TCW-71's, tested beside their code.
"""

import json
import re
from datetime import date

import pytest

from tests.work.jira.conftest import fake, jira_project, tcw  # noqa: F401 (fixtures)
from tests.work.projects import make_project

TODAY = date.today().isoformat()


@pytest.fixture
def fx(tmp_path):
    return make_project(tmp_path, "fx", config={"tags": ["a", "b"]})


def new(tcw, root, title, *flags, stdin=""):
    r = tcw(["new", title, *flags], root, stdin=stdin)
    assert r.code == 0, r.err
    return r.out.strip()


# -- show: the record, the request and the comments (Design 1.9) ----------------------


def test_show_prints_the_record_then_the_request_then_comments_newest_first(tcw, fx):
    slug = new(tcw, fx, "A b", stdin="Need X\n")
    assert tcw(["comment", slug], fx, stdin="one\n").code == 0
    assert tcw(["comment", slug], fx, stdin="two\n").code == 0
    out = tcw(["show", slug], fx).out
    record, request, comments = out.split("\n\n")
    assert record.splitlines()[0] == f"slug: {slug}"
    assert "untracked:" not in record
    assert request == "request:\n  Need X"
    lines = comments.splitlines()
    assert lines[0] == "comments:"
    assert re.fullmatch(r"- \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ( \S.*)?", lines[1])
    assert lines[2] == "  two" and lines[4] == "  one"


def test_show_json_carries_the_request_and_comments(tcw, fx):
    slug = new(tcw, fx, "A b", stdin="Need X\n")
    tcw(["comment", slug], fx, stdin="one\n")
    tcw(["comment", slug], fx, stdin="two\n")
    shown = json.loads(tcw(["show", slug, "--json"], fx).out)
    assert list(shown) == ["schema", "item", "request", "comments"]
    assert shown["schema"] == 1 and shown["item"]["slug"] == slug
    assert "Need X" in shown["request"]
    assert [c["text"].strip() for c in shown["comments"]] == ["two", "one"]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", shown["comments"][0]["at"])
    assert shown["item"]["untracked"] == []


def test_an_item_with_no_request(tcw, fx):
    slug = new(tcw, fx, "A b")
    out = tcw(["show", slug], fx).out
    assert "\n\nrequest: none\n" in out and "comments:" not in out
    assert json.loads(tcw(["show", slug, "--json"], fx).out)["request"] is None


def test_list_json_is_one_object_with_items(tcw, fx):
    slug = new(tcw, fx, "A b")
    listed = json.loads(tcw(["list", "--json"], fx).out)
    assert listed["schema"] == 1
    assert [i["slug"] for i in listed["items"]] == [slug]
    assert "request" not in listed["items"][0]


# -- list --tag (Design 2, decision 6) ----------------------------------------------------


def test_list_by_tag(tcw, fx):
    a = new(tcw, fx, "Tagged a", "--tag", "a")
    b = new(tcw, fx, "Tagged b", "--tag", "b")
    new(tcw, fx, "Untagged")
    r = tcw(["list", "--tag", "a", "--tag", "b"], fx)
    assert sorted(r.out.split()) == sorted([a, b])
    assert tcw(["advance", a], fx).code == 0
    assert tcw(["list", "--tag", "a", "--tag", "b", "--stage", "spec"], fx).out.split() == [a]


def test_an_unregistered_tag_warns_and_still_filters(tcw, fx):
    new(tcw, fx, "Tagged a", "--tag", "a")
    r = tcw(["list", "--tag", "zzz"], fx)
    assert (r.code, r.out) == (0, "")
    assert re.search(r"^warning: .*zzz", r.err, re.M)


@pytest.mark.parametrize("argv", [["list", "--tag", "a,b"],
                                  ["new", "x", "--tag", "a,b"],
                                  ["tags", "add", "a,b"]])
def test_a_comma_is_refused_and_says_to_repeat(tcw, fx, argv):
    r = tcw(argv, fx)
    assert r.code == 2
    assert "repeat" in r.err
    assert not list((fx / "docs" / "work").glob("*-x"))


@pytest.mark.parametrize("argv", [["list", "--tags", "a"],
                                  ["edit", "fx/x", "--untags", "a"]])
def test_the_plural_aliases_are_gone(tcw, fx, argv):
    assert tcw(argv, fx).code == 2


# -- tags ----------------------------------------------------------------------------------


def test_tags_add_and_rm_print_nothing_and_name_the_config(tcw, fx):
    r = tcw(["tags", "add", "c", "d"], fx)
    assert (r.code, r.out) == (0, "")
    assert "wrote tcw-config.yaml" in r.err.splitlines()
    assert tcw(["tags", "list"], fx).out.split() == ["a", "b", "c", "d"]
    r = tcw(["tags", "rm", "d"], fx)
    assert (r.code, r.out) == (0, "")
    assert tcw(["tags", "list"], fx).out.split() == ["a", "b", "c"]


# -- removed commands and their suggestions (AC 3) ----------------------------------------


def test_start_suggests_advance(tcw, fx):
    r = tcw(["start", "x"], fx)
    assert r.code == 2 and "tcw work advance" in r.err


def test_drop_suggests_nothing(tcw, fx):
    r = tcw(["drop", "x"], fx)
    assert r.code == 2 and "did you mean" not in r.err


@pytest.mark.parametrize("word", ["init"])
def test_removed_work_commands(tcw, fx, word):
    assert tcw([word], fx).code == 2


# -- the readers (AC 19) -------------------------------------------------------------------


def test_procedure_prints_its_text(tcw, fx):
    r = tcw(["procedure", "create-work"], fx)
    assert r.code == 0 and r.out.strip()
    assert tcw(["procedure", "prompt", "create-work"], fx).code == 2


def test_an_unknown_procedure_lists_the_names(tcw, fx):
    r = tcw(["procedure", "nonsense"], fx)
    assert r.code == 2 and "create-work" in r.err


def test_lifecycle_json(tcw, tmp_path):
    root = make_project(tmp_path, "fx", config={"stages": {"qa": {"enabled": False}}})
    data = json.loads(tcw(["lifecycle", "--json"], root).out)
    assert data["schema"] == 1
    assert [s["name"] for s in data["stages"] if not s["enabled"]] == ["qa"]
    assert "request" in [s["name"] for s in data["stages"] if s["enabled"]]
    text = tcw(["lifecycle"], root).out
    assert "qa  [flow, disabled]" in text


@pytest.mark.parametrize("argv", [["lifecycle", "--directive"],
                                  ["lifecycle", "--phase", "pre"],
                                  ["lifecycle", "fx/x"]])
def test_lifecycle_options_that_went(tcw, fx, argv):
    assert tcw(argv, fx).code == 2


def test_an_unknown_stage_lists_the_stages(tcw, fx):
    slug = new(tcw, fx, "A b")
    r = tcw(["advance", slug, "--to", "nonsense"], fx)
    assert r.code == 2 and "implement" in r.err


# -- Jira mode ----------------------------------------------------------------------------


def test_new_at_the_inbox_is_filesystem_only(tcw, jira_project):
    r = tcw(["new", "x", "--stage", "inbox"], jira_project.root)
    assert (r.code, r.out) == (2, "")
    assert jira_project.fake.writes() == []


def test_show_names_people_in_text_and_ids_in_json(tcw, jira_project):
    fake = jira_project.fake
    fake.account("ada@example.test", "acct-ada", "Ada")
    bo = fake.account("bo@example.test", "acct-bo", "Bo")
    key, _ = jira_project.item("A thing", "a-thing", assignee="acct-ada")
    fake.tickets[key].comments.append({
        "id": "1", "author": {"accountId": bo.account_id, "displayName": "Bo"},
        "created": "2026-10-02T10:00:00.000+0000",
        "body": {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}]}})
    text = tcw(["show", key], jira_project.root)
    assert text.code == 0, text.err
    assert "assignee: Ada" in text.out and "- 2026-10-02T10:00:00Z Bo" in text.out
    shown = tcw(["show", key, "--json"], jira_project.root).out
    assert "Ada" not in shown and '"Bo"' not in shown
    data = json.loads(shown)
    assert data["item"]["assignee"] == "acct-ada"
    assert data["comments"][0]["author"] == "acct-bo"


def test_tickets_list_json_is_one_object(tcw, jira_project):
    jira_project.fake.ticket("Loose", status="To Do")
    data = json.loads(tcw(["tickets", "list", "--json"], jira_project.root).out)
    assert data["schema"] == 1 and isinstance(data["tickets"], list)
