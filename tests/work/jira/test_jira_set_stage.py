"""`set_stage` in Jira mode (TCW-71 AC 9, and AC 16's multi-line note), each
case checked against the fake's write log."""

import pytest

from tcw.errors import MovedWithoutNote, Refused, Unreachable
from tcw.work.jira import client as jira
from tcw.work.jira.backend import Refusal, choose_transition
from tcw.work.jira.client import Transition
from tcw.work.jira.mapping import document_text
from tests.work.jira.fake import Transition as Route

NOTE = "forced: the spec is in the old wiki"


@pytest.fixture
def item(jira_project):
    key, folder = jira_project.item("Move me", "x")
    return jira_project, key, folder


def routes(project, *extra):
    """Replace the transitions into Planning with `extra`."""
    flow = project.fake.projects["TCW"]
    flow.transitions = [t for t in flow.transitions if t.to != "Planning"] + list(extra)


def transition_posts(project, key):
    return [b for m, p, b in project.fake.log
            if (m, p) == ("POST", f"/rest/api/3/issue/{key}/transitions")]


def comment_texts(project, key):
    return [document_text(c["body"]) for c in project.fake.tickets[key].comments]


def test_one_transition_carries_the_note(item):
    project, key, folder = item
    assert project.backend().set_stage(folder, "plan", NOTE) == "plan"
    post, = transition_posts(project, key)
    assert document_text(post["update"]["comment"][0]["add"]["body"]) == NOTE
    assert project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]
    assert comment_texts(project, key) == [NOTE]


def test_without_a_note_no_comment_is_sent(item):
    project, key, folder = item
    project.backend().set_stage(folder, "plan", None)
    post, = transition_posts(project, key)
    assert "update" not in post


def test_the_returned_stage_is_the_one_read_back(item, monkeypatch):
    project, key, folder = item
    original = project.fake._transition

    def elsewhere(ticket, body, route):
        original(ticket, body, route)
        ticket.status = "In Review"
    monkeypatch.setattr(project.fake, "_transition", elsewhere)
    assert project.backend().set_stage(folder, "plan", None) == "review"


def test_of_two_the_one_with_no_screen(item):
    project, key, folder = item
    routes(project, Route("90", "Plan with resolution", "Planning",
                          screen={"resolution": False}),
           Route("91", "Plan", "Planning"))
    project.backend().set_stage(folder, "plan", None)
    post, = transition_posts(project, key)
    assert post["transition"]["id"] == "91"


def test_two_comment_only_routes_are_refused(item):
    project, key, folder = item
    routes(project, Route("90", "Plan", "Planning"),
           Route("91", "Plan with note", "Planning", screen={"comment": False}))
    with pytest.raises(Refused, match="Plan → Planning.*Plan with note → Planning"):
        project.backend().set_stage(folder, "plan", NOTE)
    assert project.fake.writes() == []


def test_no_route_lists_every_offered_transition(item):
    project, key, folder = item
    routes(project)
    with pytest.raises(Refused) as refused:
        project.backend().set_stage(folder, "plan", NOTE)
    assert "Move to Done" in str(refused.value) and "Move to Triage" in str(refused.value)
    assert project.fake.writes() == []


def test_a_refused_comment_is_retried_without_it_then_posted(item):
    project, key, folder = item
    project.fake.refuse_commented_transitions = True
    assert project.backend().set_stage(folder, "plan", NOTE) == "plan"
    assert project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions"),
                                     ("POST", f"/rest/api/3/issue/{key}/transitions"),
                                     ("POST", f"/rest/api/3/issue/{key}/comment")]
    assert "update" not in transition_posts(project, key)[1]
    assert comment_texts(project, key) == [NOTE]


def someone_moved_it_first(project, monkeypatch):
    def lost_race(ticket, body, route):
        ticket.status = "Planning"
        raise jira._for_status(400, {}, "Transition is not valid", route)
    monkeypatch.setattr(project.fake, "_transition", lost_race)


def test_a_lost_race_with_a_note_posts_it(item, monkeypatch):
    project, key, folder = item
    someone_moved_it_first(project, monkeypatch)
    assert project.backend().set_stage(folder, "plan", NOTE) == "plan"
    assert project.fake.writes()[-1] == ("POST", f"/rest/api/3/issue/{key}/comment")
    assert comment_texts(project, key) == [NOTE]


def test_a_lost_race_whose_note_cannot_be_posted(item, monkeypatch):
    project, key, folder = item
    someone_moved_it_first(project, monkeypatch)

    def refused(*args, **kwargs):
        raise jira._for_status(400, {}, "no", "/x")
    monkeypatch.setattr(project.fake, "_comment", refused)
    with pytest.raises(MovedWithoutNote):
        project.backend().set_stage(folder, "plan", NOTE)


def test_a_lost_race_without_a_note(item, monkeypatch):
    project, key, folder = item
    someone_moved_it_first(project, monkeypatch)
    assert project.backend().set_stage(folder, "plan", None) == "plan"
    assert project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]


@pytest.mark.parametrize("note, posts", [(NOTE, 2), (None, 1)])
def test_a_required_screen_field_is_refused_with_jiras_text(item, note, posts):
    project, key, folder = item
    planning = next(t for t in project.fake.projects["TCW"].transitions
                    if t.to == "Planning")
    project.fake.require_screen_field(planning.id, "resolution")
    with pytest.raises(Refused, match="resolution is required.*post function"):
        project.backend().set_stage(folder, "plan", note)
    assert project.fake.tickets[key].status == "Triage"
    assert len(project.fake.writes()) == posts
    assert comment_texts(project, key) == []


def test_a_drop_after_the_move_without_the_note(item, monkeypatch):
    project, key, folder = item

    def moved_then_dropped(ticket, body, route):
        ticket.status = "Planning"
        raise jira.TrackerUnavailable("connection lost")
    monkeypatch.setattr(project.fake, "_transition", moved_then_dropped)
    with pytest.raises(MovedWithoutNote):
        project.backend().set_stage(folder, "plan", NOTE)
    assert project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]


def test_a_multi_line_note_that_landed_before_the_drop_is_found(item):
    project, key, folder = item
    note = "line one  \nline two\n\n\nlast part"
    project.fake.drop_after_next_write()
    assert project.backend().set_stage(folder, "plan", note) == "plan"
    assert len(project.fake.tickets[key].comments) == 1


def test_a_drop_before_the_write(item, tcw):
    project, key, folder = item
    project.fake.drop_before_next_write()
    with pytest.raises(Unreachable, match="it was not moved"):
        project.backend().set_stage(folder, "plan", NOTE)
    assert project.fake.tickets[key].status == "Triage"


def test_a_drop_after_which_nothing_can_be_read(item):
    project, key, folder = item
    project.fake.drop_after_next_write(then_unreachable=True)
    with pytest.raises(Unreachable, match="may have happened"):
        project.backend().set_stage(folder, "plan", NOTE)


# -- the choice rule on its own ---------------------------------------------------------


def t(id_, to, fields=()):
    return Transition(id_, f"T{id_}", to, fields=tuple(fields))


@pytest.mark.parametrize("offered, expected", [
    ([t("1", "Done", ["resolution"])], "1"),                 # a lone candidate, screen or not
    ([t("1", "Done", ["resolution"]), t("2", "Done", ["comment"])], "2"),
    ([t("1", "Done"), t("2", "Done")], None),
    ([t("1", "Done", ["resolution"]), t("2", "Done", ["resolution"])], None),
    ([t("1", "Triage")], None),
    ([], None),
])
def test_choose_transition(offered, expected):
    chosen = choose_transition(offered, "Done")
    if expected is None:
        assert isinstance(chosen, Refusal)
    else:
        assert chosen.id == expected
