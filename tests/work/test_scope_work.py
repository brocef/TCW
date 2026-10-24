"""TCW-113: `tcw work list` and `tcw work show` across a scope (spec Design
1, 2, 3.1-3.4; plan Steps 5 and 6). Each test names the acceptance
criterion it proves, on the family `F` of `tests/families.py`."""

from __future__ import annotations

import pytest
import yaml

from tests.families import build_family, item_folder, jira_mode
from tests.projectfiles import write_local_config
from tests.work.jira.fake import FakeJira

EMAIL, TOKEN = "TCW_TEST_JIRA_EMAIL", "TCW_TEST_JIRA_TOKEN"


def wid(project_id: str, folder: str | None = None) -> str:
    return f"{project_id}.work/{folder or item_folder(project_id)}"


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv(EMAIL, "dev@example.test")
    monkeypatch.setenv(TOKEN, "token")
    fake = FakeJira().install(monkeypatch)
    # The account the credentials sign in as: the person `ann`, `a-1`.
    fake.account("dev@example.test", "a-1", "ann")
    return fake


def searches(fake) -> list[dict]:
    """The bodies of every search the fake was sent that is not a key search."""
    return [body for _, _, body in fake.requests("POST", "/search/jql")
            if "key in" not in body["jql"].lower()]


def warnings_about(result, project_id: str) -> list[str]:
    return [line for line in result.err_lines
            if line.startswith(f"warning: '{project_id}' is unavailable")]


# -- AC 1, 2 ---------------------------------------------------------------------------


def test_ac1_an_unknown_scope_is_a_usage_error(family):
    assert family.run("shared", "work", "list", "--scope", "sideways").code == 2


def test_ac1_commands_that_list_no_objects_refuse_the_options(family):
    assert family.run("shared", "work", "tickets", "list", "--scope", "up").code == 2
    assert family.run("shared", "work", "tags", "list", "--scope", "up").code == 2


def test_ac2_own_is_the_default(family):
    ran = family.run("desktop", "work", "list")
    assert ran.code == 0, ran.err
    assert ran.lines == [wid("desktop")]
    assert ran.lines == family.run("desktop", "work", "list", "--scope", "own").lines
    document = family.run("desktop", "work", "list", "--json").json
    assert "projects" not in document
    assert "projects" not in family.run("desktop", "work", "list", "--scope", "own",
                                        "--json").json


# -- AC 3-6 ----------------------------------------------------------------------------


def test_ac3_scope_order_and_projects(family):
    ran = family.run("shared", "work", "list", "--scope", "all", "--json")
    assert ran.code == 0, ran.err
    projects = ran.json["projects"]
    assert [p["id"] for p in projects] == ["docs", "shared", "desktop", "server", "mobile"]
    assert [p["relation"] for p in projects] == [
        "ancestor", "current", "descendant", "descendant", "descendant"]
    assert [p["id"] for p in projects if "unavailable" in p] == ["mobile"]
    assert "tcw project provision mobile" in projects[-1]["unavailable"]
    text = family.run("shared", "work", "list", "--scope", "all")
    assert text.code == 0
    assert text.lines == [wid(p) for p in ("docs", "shared", "desktop", "server")]
    assert len(warnings_about(text, "mobile")) == 1
    assert warnings_about(text, "mobile")[0].startswith(
        "warning: 'mobile' is unavailable, so its work items are not listed")


def test_ac4_never_a_sibling(family):
    for scope in ("own", "up", "down", "all"):
        ran = family.run("shared", "work", "list", "--scope", scope, "--json")
        assert wid("other") not in [i["full-id"] for i in ran.json["items"]]
        assert "other" not in [p["id"] for p in ran.json.get("projects", [])]
    refused = family.run("shared", "work", "list", "--project", "other", "--scope", "all")
    assert refused.code == 2
    assert "is neither an ancestor nor a descendant of 'shared'" in refused.err
    assert refused.out == ""


def test_ac5_up_and_down(family):
    up = family.run("desktop", "work", "list", "--scope", "up")
    assert up.lines == [wid("docs"), wid("shared"), wid("desktop")]
    down = family.run("shared", "work", "list", "--scope", "down")
    assert down.lines == [wid("shared"), wid("desktop"), wid("server")]


def test_ac6_project(family):
    only = family.run("shared", "work", "list", "--scope", "down", "--project", "desktop")
    assert only.code == 0 and only.lines == [wid("desktop")]
    refused = family.run("shared", "work", "list", "--scope", "own", "--project", "desktop")
    assert refused.code == 2 and "--scope down covers it" in refused.err
    mobile = family.run("shared", "work", "list", "--scope", "down", "--project", "mobile")
    assert mobile.code == 0 and mobile.out == ""
    assert len(warnings_about(mobile, "mobile")) == 1
    assert family.run("shared", "work", "list", "--project", "Bad_Id").code == 2


# -- AC 22, 23 -------------------------------------------------------------------------


def test_ac22_a_descendant_whose_configuration_is_undecided(family, fake):
    jira_mode(family, "server", fake)
    document = family.config("server")
    del document["work"]["jira"]
    family.write_config("server", document)
    family.add_parent("server", "cfg", inherit=["config"])
    ran = family.run("shared", "work", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert ran.lines == [wid("shared"), wid("desktop")]
    [warning] = warnings_about(ran, "server")
    assert "'server'" in warning.partition(": ")[2] and "cfg" in warning
    assert family.run("server", "work", "list").code == 7


def test_ac23_a_project_is_read_for_itself(family, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)
    write_local_config(family["server"], "user: [unclosed\n")
    ran = family.run("shared", "work", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert wid("server") in ran.lines
    assert family.run("server", "work", "list").code == 1


# -- AC 26 and the side stage ----------------------------------------------------------


def _no_review(stages: dict) -> dict:
    return {**stages, "review": {"enabled": False}}


def test_ac26_a_stage_another_project_does_not_enable(family, fake):
    from tests.work.jira.conftest import STATUSES, jira_config
    stages = _no_review(jira_config("server")["stages"])
    jira_mode(family, "server", fake, stages=stages)
    before = len(searches(fake))
    review = family.run("shared", "work", "list", "--scope", "down", "--stage", "review")
    assert review.code == 0, review.err
    assert warnings_about(review, "server") == []
    assert len(searches(fake)) == before
    both = family.run("shared", "work", "list", "--scope", "down", "--stage", "review",
                      "--stage", "spec")
    assert both.code == 0, both.err
    made = searches(fake)[before:]
    assert len(made) == 1
    assert STATUSES["spec"] in made[0]["jql"] and STATUSES["review"] not in made[0]["jql"]
    assert family.run("server", "work", "list", "--stage", "review").code == 2


def test_a_stage_a_files_project_does_not_enable_opens_no_backend(family, monkeypatch):
    import tcw.work.open as work_open
    document = family.config("desktop")
    document.setdefault("work", {})["stages"] = {"review": {"enabled": False}}
    family.write_config("desktop", document)
    opened = []
    real = work_open.open_backend
    monkeypatch.setattr(work_open, "open_backend",
                        lambda root, **kw: opened.append(root.name) or real(root, **kw))
    ran = family.run("shared", "work", "list", "--scope", "down", "--stage", "review")
    assert ran.code == 0, ran.err
    assert "server" in opened and "desktop" not in opened


def test_the_side_stage_is_not_asked_of_a_jira_project(family, fake):
    jira_mode(family, "server", fake)
    before = len(searches(fake))
    ran = family.run("shared", "work", "list", "--scope", "down", "--stage", "postmortem")
    assert ran.code == 0, ran.err
    assert warnings_about(ran, "server") == []
    assert len(searches(fake)) == before
    # In `server` itself, today's answer: the stage has no Jira status.
    assert family.run("server", "work", "list", "--stage", "postmortem").code == 2


# -- AC 27, 38 -------------------------------------------------------------------------


def test_ac27_mine_in_each_projects_own_form(family, fake, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)
    write_local_config(family["shared"], yaml.safe_dump({"user": {"name": "ann"}}))
    # The Jira account is not called `ann`, so only its own identity finds
    # its tickets: the person's `user.name` would match no one there.
    fake.account("dev@example.test", "a-1", "Bea")
    family.item("desktop", item_folder("desktop"), assignee="ann")
    family.item("server", item_folder("server"), assignee="a-1")
    renamed = jira_mode(family, "server", fake)
    ran = family.run("shared", "work", "list", "--scope", "down", "--mine")
    assert ran.code == 0, ran.err
    assert ran.lines == [wid("desktop"), wid("server", renamed[item_folder("server")])]


def test_ac38_tag_assignee_and_all_across_projects(family, fake):
    document = family.config("desktop")
    document.setdefault("work", {})["tags"] = ["ui"]
    family.write_config("desktop", document)
    family.item("desktop", item_folder("desktop"), tags=["ui"], assignee="ann")
    family.item("desktop", "2026-10-02-desktop-done", stage="completed")
    tagged = family.run("shared", "work", "list", "--scope", "down", "--tag", "ui")
    assert tagged.code == 0, tagged.err
    assert tagged.lines == [wid("desktop")]
    # One tag warning, checked against `shared`'s registry only; the
    # family's `mobile` adds its own line, as every `--scope down` does.
    assert [line for line in tagged.err_lines if line.startswith("warning: tag")] == [
        "warning: tag 'ui' is not in this project's registry"]
    assert [line for line in tagged.err_lines
            if not line.startswith("warning: tag")] == warnings_about(tagged, "mobile")
    assigned = family.run("shared", "work", "list", "--scope", "down", "--assignee", "ann")
    assert assigned.lines == [wid("desktop")]
    every = family.run("shared", "work", "list", "--scope", "down", "--all")
    assert wid("desktop", "2026-10-02-desktop-done") in every.lines
    unfinished = family.run("shared", "work", "list", "--scope", "down")
    assert wid("desktop", "2026-10-02-desktop-done") not in unfinished.lines
    # `server` in Jira, where the person `ann` is the account `a-1`.
    family.item("server", item_folder("server"), assignee="a-1")
    renamed = jira_mode(family, "server", fake)
    both = family.run("shared", "work", "list", "--scope", "down", "--assignee", "ann")
    assert both.code == 0, both.err
    assert both.lines == [wid("desktop"), wid("server", renamed[item_folder("server")])]


def test_an_unreadable_item_makes_its_project_unavailable(family):
    # The files backend refuses a whole board for one unreadable item, so
    # the project is unavailable, its reason naming the file (Design 1.6 g),
    # and the rest is listed.
    bad = family["desktop"] / "docs" / "work" / "2026-10-03-broken"
    bad.mkdir()
    (bad / "tcw-work-item.yaml").write_text("tcw-version: 99.0.0\ntitle: x\n")
    ran = family.run("shared", "work", "list", "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    assert [i["full-id"] for i in ran.json["items"]] == [wid("shared"), wid("server")]
    [warning] = warnings_about(ran, "desktop")
    assert "2026-10-03-broken" in warning


# -- `tcw work show` (plan Step 6) -----------------------------------------------------


def test_ac4_show_by_full_identifier_outside_the_scope(family):
    for scope in ("own", "down", "all"):
        ran = family.run("shared", "work", "show", wid("other"), "--scope", scope,
                         "--json")
        assert ran.code == 0, ran.err
        assert ran.json["item"]["full-id"] == wid("other")


def test_ac22_an_item_named_by_its_full_identifier_is_never_unavailable(family, fake):
    jira_mode(family, "server", fake)
    document = family.config("server")
    del document["work"]["jira"]
    family.write_config("server", document)
    family.add_parent("server", "cfg", inherit=["config"])
    [folder] = [p.name for p in (family["server"] / "docs" / "work").iterdir()
                if p.name.startswith("APP-")]
    assert family.run("shared", "work", "show", wid("server", folder)).code == 7
    assert family.run("shared", "work", "show", wid("server", folder),
                      "--scope", "down").code == 7


def test_ac24_show_by_folder_name_follows_the_scope(family):
    own = family.run("shared", "work", "show", item_folder("desktop"))
    assert own.code == 4
    # Today's message under `own`, which never tries a wider scope.
    assert own.err_lines == [f"tcw work show: no work item shared.work/"
                             f"{item_folder('desktop')}"]
    down = family.run("shared", "work", "show", item_folder("desktop"), "--scope", "down",
                      "--json")
    assert down.code == 0, down.err
    assert down.json["item"]["full-id"] == wid("desktop")
    family.item("server", item_folder("desktop"))
    both = family.run("shared", "work", "show", item_folder("desktop"), "--scope", "down")
    assert both.code == 2
    assert (f"'{item_folder('desktop')}' names 2 items in --scope down: "
            f"{wid('desktop')}, server.work/{item_folder('desktop')}; name one by its "
            f"full identifier") in both.err


def test_ac25_an_epics_parts_across_projects(family):
    family.item("shared", "2026-10-05-epic")
    family.item("desktop", "2026-10-06-part", parent="shared.work/2026-10-05-epic")
    epic = "shared.work/2026-10-05-epic"
    alone = family.run("shared", "work", "show", "2026-10-05-epic", "--json")
    assert alone.code == 0, alone.err
    assert alone.json["item"]["children"] == []
    down = family.run("shared", "work", "show", "2026-10-05-epic", "--scope", "down",
                      "--json")
    assert down.code == 0, down.err
    assert down.json["item"]["children"] == ["desktop.work/2026-10-06-part"]
    parts = family.run("shared", "work", "list", "--scope", "down", "--parent", epic)
    assert parts.code == 0, parts.err
    assert parts.lines == ["desktop.work/2026-10-06-part"]
    listed = family.run("shared", "work", "list", "--scope", "down", "--json")
    [record] = [i for i in listed.json["items"] if i["full-id"] == epic]
    assert record["children"] == ["desktop.work/2026-10-06-part"]


def test_design_2_3_show_with_project(family):
    ran = family.run("shared", "work", "show", item_folder("desktop"), "--scope", "down",
                     "--project", "desktop", "--json")
    assert ran.code == 0, ran.err
    assert ran.json["item"]["full-id"] == wid("desktop")
    family.item("server", item_folder("desktop"))
    only = family.run("shared", "work", "show", item_folder("desktop"), "--scope", "down",
                      "--project", "server", "--json")
    assert only.json["item"]["full-id"] == f"server.work/{item_folder('desktop')}"
    mixed = family.run("shared", "work", "show", wid("shared"), "--scope", "down",
                       "--project", "desktop")
    assert mixed.code == 2
    assert "'shared'" in mixed.err and "'desktop'" in mixed.err


def test_a_ticket_key_in_another_project_of_the_scope(family, fake):
    renamed = jira_mode(family, "server", fake)
    key = "-".join(renamed[item_folder("server")].split("-")[:2])
    assert family.run("shared", "work", "show", key).code == 4
    ran = family.run("shared", "work", "show", key, "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    assert ran.json["item"]["full-id"] == wid("server", renamed[item_folder("server")])


def test_show_names_an_unavailable_project(family):
    ran = family.run("shared", "work", "show", item_folder("shared"), "--scope", "down",
                     "--json")
    assert ran.code == 0, ran.err
    [warning] = warnings_about(ran, "mobile")
    assert warning.startswith("warning: 'mobile' is unavailable, so its items are not "
                              "counted in children and blocks: ")
    assert [p["id"] for p in ran.json["projects"] if "unavailable" in p] == ["mobile"]


def test_a_project_without_the_folder_is_no_unavailability(family):
    ran = family.run("shared", "work", "show", item_folder("desktop"), "--scope", "down",
                     "--json")
    assert ran.code == 0, ran.err
    assert warnings_about(ran, "server") == []
    assert [p["id"] for p in ran.json["projects"] if "unavailable" in p] == ["mobile"]


def test_show_warns_of_another_projects_unreadable_item(family):
    # The `_readable` path: `show` counts every readable item for `children`
    # and `blocks`, and names those it could not read, as today.
    bad = family["desktop"] / "docs" / "work" / "2026-10-03-broken"
    bad.mkdir()
    (bad / "tcw-work-item.yaml").write_text("tcw-version: 99.0.0\ntitle: x\n")
    ran = family.run("shared", "work", "show", item_folder("shared"), "--scope", "down",
                     "--json")
    assert ran.code == 0, ran.err
    [line] = [l for l in ran.err_lines if "could not be read" in l]
    assert line.startswith("warning: these items could not be read, so blocks and "
                           "children may be incomplete: ")
    assert "2026-10-03-broken" in line
    assert warnings_about(ran, "desktop") == []


def test_a_descendants_work_store_not_provisioned_here_is_fetched_in_its_folder(family):
    # A child's work store declared in a repository and not on this machine
    # makes the child unavailable, and the advice runs the provisioning in
    # the child's folder: run in the active project, `tcw project provision
    # --component work` would fetch the active project's own store (TCW-115
    # Design 7.2).
    import shutil
    document = family.config("server")
    document["work"] = {**document.get("work", {}), "path": "docs/work-elsewhere",
                        "repository": {"url": "https://example.invalid/server-work.git",
                                       "path": "docs/work"}}
    family.write_config("server", document)
    shutil.rmtree(family["server"] / "docs" / "work")
    ran = family.run("shared", "work", "list", "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    assert [i["full-id"] for i in ran.json["items"]] == [wid("shared"), wid("desktop")]
    [warning] = warnings_about(ran, "server")
    assert "has not been provisioned here" in warning, warning
    assert f"tcw -C {family['server']} project provision --component work" in warning, warning
