"""`list` in Jira mode (TCW-71 AC 11; the in-memory contract case is in
`test_contract.py`)."""

import re

import pytest

from tcw.errors import UsageError
from tcw.work.backend import Query
from tcw.work.jira.mapping import block_link
from tcw.work.model import Slug
from tests.work.jira.conftest import JiraProject, jira_config
from tests.work.jira.fake import FIELDS, Link
from tests.work.projects import make_project

SINGLE_ISSUE = re.compile(r"^/rest/api/3/issue/[A-Z][A-Z0-9_]*-\d+(/|\?|$)")


def folders(items):
    return sorted(i.slug.folder for i in items)


def searches(fake):
    return [body["jql"] for _, _, body in fake.requests("POST", "/search/jql")]


def test_the_default_hides_finished_work_and_shows_unmapped_statuses(jira_project):
    fake = jira_project.fake
    fake.projects["TCW"].statuses += ("Backlog",)
    _, open_ = jira_project.item("Open", "open", status="In Progress")
    _, unmapped = jira_project.item("Unmapped", "unmapped", status="Backlog")
    _, done = jira_project.item("Done", "done", status="Done")
    _, dropped = jira_project.item("Dropped", "dropped", status="Won't Do")
    backend = jira_project.backend()
    assert folders(backend.list(Query())) == sorted([open_, unmapped])
    assert folders(backend.list(Query(all=True))) == sorted([open_, unmapped, done, dropped])
    assert folders(backend.list(Query(stages=frozenset({"completed"})))) == [done]
    assert 'status NOT IN ("Done", "Won\'t Do")' in searches(fake)[0]


def test_a_stage_with_no_status_is_a_usage_error(tmp_path, fake):
    config = jira_config()
    config["stages"]["review"] = {"enabled": False}
    project = JiraProject(make_project(tmp_path, "tcw", config=config), "tcw", fake)
    with pytest.raises(UsageError, match="review"):
        project.backend().list(Query(stages=frozenset({"review"})))


def test_tcw_project_is_matched_exactly_after_the_search(tmp_path, fake, capsys):
    tcw = JiraProject(make_project(tmp_path, "tcw", config=jira_config("tcw")), "tcw", fake)
    web = JiraProject(make_project(tmp_path, "tcw-web", config=jira_config("tcw-web")),
                      "tcw-web", fake)
    _, mine = tcw.item("Mine", "mine")
    _, theirs = web.item("Theirs", "theirs")
    capsys.readouterr()
    assert folders(tcw.backend().list(Query())) == [mine]
    assert folders(web.backend().list(Query())) == [theirs]
    assert not any("~" in q for q in searches(fake))
    # Another project's tickets are not this project's missing folders.
    assert capsys.readouterr().err == ""


def test_a_ticket_whose_folder_is_not_here_is_left_out_and_named(jira_project, capsys):
    key, _ = jira_project.item("Elsewhere", "elsewhere", folder=False)
    _, here = jira_project.item("Here", "here")
    assert folders(jira_project.backend().list(Query())) == [here]
    err = capsys.readouterr().err
    assert key in err and "left out" in err


def many(jira_project, count, **values):
    work = jira_project.work
    work.mkdir(parents=True, exist_ok=True)
    keys = []
    for n in range(count):
        ticket = jira_project.fake.ticket(f"t{n}", **values)
        name = f"{ticket.key}-t"
        ticket.custom[FIELDS["TCW Project"]] = "tcw"
        ticket.custom[FIELDS["TCW Item"]] = f"tcw/{name}"
        (work / name).mkdir()
        keys.append(ticket.key)
    return keys


def test_every_page_is_read(jira_project):
    many(jira_project, 250)
    jira_project.fake.page_size = 100
    assert len(jira_project.backend().list(Query())) == 250


def test_the_request_budget(jira_project):
    fake = jira_project.fake
    fake.add_project("WEB")
    others = [fake.ticket(f"o{n}", project="WEB", issue_type="Epic") for n in range(20)]
    keys = many(jira_project, 250)
    for n, key in enumerate(keys):
        fake.tickets[key].parent = others[n % 20].key
        fake.link_counter += 1
        fake.links.append(Link(str(fake.link_counter), "Blocks",
                               *block_link(others[(n + 7) % 20].key, key)))
    fake.page_size = 100
    fake.log.clear()
    items = jira_project.backend().list(Query())
    assert len(items) == 250 and all(len(i.untracked) == 2 for i in items)
    queries = searches(fake)
    assert len([q for q in queries if q.startswith('project = "TCW"')]) == 3
    key_searches = [q for q in queries if q.startswith("key IN")]
    assert len(key_searches) == 1 and key_searches[0].count('"WEB-') == 20
    assert [p for _, p, _ in fake.requests("GET") if SINGLE_ISSUE.match(p)] == []


def test_a_refused_key_search_falls_back_to_direct_reads(jira_project):
    fake = jira_project.fake
    parent = fake.ticket("Parent", issue_type="Epic")
    parent.custom[FIELDS["TCW Item"]] = "web/WEB-1-x"
    key, folder = jira_project.item("Child", "child", parent=parent.key)
    fake.link_counter += 1
    fake.links.append(Link("1", "Blocks", *block_link("TCW-99", key)))
    fake.refuse_missing_key_search = True
    item, = jira_project.backend().list(Query())
    assert item.parent == Slug("web", "WEB-1-x")
    assert item.untracked == ("TCW-99",)
    assert len(fake.requests("GET", "/rest/api/3/issue/TCW-99")) == 1
    assert len(fake.requests("GET", f"/rest/api/3/issue/{parent.key}")) == 1


def test_a_parent_missing_from_searches_is_read_directly(jira_project):
    fake = jira_project.fake
    parent = fake.ticket("Parent", issue_type="Epic")
    _, folder = jira_project.item("Child", "child", parent=parent.key)
    backend = jira_project.backend()
    backend.client.edit_issue(parent.key, {FIELDS["TCW Item"]: "web/WEB-2-y"})
    fake.search_lag = 10
    item, = backend.list(Query())
    assert item.parent == Slug("web", "WEB-2-y")
    key_search, = [q for q in searches(fake) if q.startswith("key IN")]
    assert parent.key in key_search


def test_a_parent_filter(jira_project):
    fake = jira_project.fake
    key, epic = jira_project.item("Epic", "epic", issue_type="Epic")
    _, child = jira_project.item("Child", "child", parent=key)
    jira_project.item("Other", "other")
    backend = jira_project.backend()
    assert folders(backend.list(Query(parent=Slug("tcw", epic)))) == [child]
    fake.log.clear()
    assert backend.list(Query(parent=Slug("tcw", "2026-10-01-not-a-ticket"))) == []
    assert fake.log == []


def test_an_assignee_given_by_name(jira_project):
    jira_project.fake.account("ann@example.test", "acct-ann", "Ann Lee")
    _, hers = jira_project.item("Hers", "hers", assignee="acct-ann")
    jira_project.item("Not hers", "other")
    assert folders(jira_project.backend().list(Query(assignee="Ann"))) == [hers]
    assert any('assignee = "acct-ann"' in q for q in searches(jira_project.fake))


# -- tags (Design 6) -----------------------------------------------------------------


@pytest.fixture
def tagged(jira_project):
    made = {name: jira_project.item(name, name.lower(), labels=labels)[1]
            for name, labels in (("A", ["ui"]), ("B", ["api", "ui"]), ("C", ["api"]),
                                 ("D", []), ("E", ["ui-old"]), ("F", ["UI"]))}
    _, done = jira_project.item("G", "g", status="Done", labels=["ui"])
    made["G"] = done
    return jira_project, made


def test_one_tag(tagged):
    project, made = tagged
    assert folders(project.backend().list(Query(tags=frozenset({"ui"})))) == sorted(
        [made["A"], made["B"]])
    assert 'labels IN ("ui")' in searches(project.fake)[-1]


def test_any_of_several_tags(tagged):
    project, made = tagged
    found = folders(project.backend().list(Query(tags=frozenset({"ui", "api"}))))
    assert found == sorted([made["A"], made["B"], made["C"]])


@pytest.mark.parametrize("tags", [{"ui-old"}, set()])
def test_no_registered_tag_gives_nothing_without_a_request(tagged, tags):
    project, _ = tagged
    project.fake.log.clear()
    assert project.backend().list(Query(tags=frozenset(tags))) == []
    assert project.fake.log == []


def test_only_registered_tags_reach_the_clause(tagged):
    project, made = tagged
    found = project.backend().list(Query(tags=frozenset({"ui", "ui-old"})))
    assert folders(found) == sorted([made["A"], made["B"]])
    assert 'labels IN ("ui")' in searches(project.fake)[-1]


def test_a_label_in_another_case_is_not_the_tag(tagged):
    project, made = tagged
    project.fake.ignore_label_case = True
    found = folders(project.backend().list(Query(tags=frozenset({"ui"}))))
    assert made["F"] not in found and found == sorted([made["A"], made["B"]])


def test_tags_with_all(tagged):
    project, made = tagged
    backend = project.backend()
    assert made["G"] in folders(backend.list(Query(tags=frozenset({"ui"}), all=True)))
    assert made["G"] not in folders(backend.list(Query(tags=frozenset({"ui"}))))
