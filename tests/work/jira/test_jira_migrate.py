"""The two methods of the Jira backend that only `tcw migrate` uses (TCW-116
Design 5.4; plan Decided 10, 11 and Step 9): `item_values`, the search made
while planning, and `set_item_values`, the edits of phase F. Neither is one
of the twelve operations.

The backend is built as `tcw/migrate/jira.py` builds it, from F-single's own
`work.jira`, over the fake at F-single's site.
"""

from __future__ import annotations

import pytest
import yaml

from tcw.errors import BackendError, Unreachable
from tcw.work.model import Slug
from tcw.work.config import parse_work_config
from tcw.work.jira.backend import JiraBackend
from tcw.work.jira.client import PAGE
from tcw.work.jira.config import parse_jira_config
from tests.migrate import fixtures
from tests.work.jira.fake import FIELDS, FakeJira

ITEM, PROJECT = FIELDS["TCW Item"], FIELDS["TCW Project"]


def _work_section() -> dict:
    return yaml.safe_load(fixtures._CONFIG)["work"]


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv(fixtures.EMAIL_VARIABLE, "dev@example.invalid")
    monkeypatch.setenv(fixtures.TOKEN_VARIABLE, "token")
    found = FakeJira(site=fixtures.SITE)
    found.install(monkeypatch)
    return found


def backend_for(tmp_path, *, work: dict | None = None) -> JiraBackend:
    jira, problems = parse_jira_config(_work_section()["jira"])
    assert not problems
    config = parse_work_config(work if work is not None else {})[0]
    return JiraBackend(fixtures.APP, tmp_path / "docs/work", config, jira)


def puts(fake) -> list:
    return [(m, p, b) for m, p, b in fake.log if m == "PUT"]


def test_item_values_lists_every_ticket_with_an_item(fake, tmp_path):
    fixtures.seed_tickets(fake)
    found = backend_for(tmp_path).item_values()
    assert found == [
        ("APP-1", "app", "app/APP-1-a"), ("APP-2", "app", "app/APP-2-b"),
        ("APP-3", "app", "app/APP-3-gone"), ("APP-4", "app", "app.work/APP-4-d"),
        ("APP-5", "app", "other/APP-5-e"),
        ("APP-6", "app", f"app/{fixtures.LONG_FOLDER}"),
        ("APP-8", "lib", "lib/LIB-1-l")]
    assert not puts(fake)
    searched = [b for m, p, b in fake.log if p.endswith("/search/jql")]
    assert [b["maxResults"] for b in searched] == [PAGE]
    assert searched[0]["jql"].startswith('project = "APP" AND cf[10002] IS NOT EMPTY')


def test_the_search_is_paged_at_the_clients_page_size(fake, tmp_path):
    fake.add_project("APP")
    for n in range(5):
        fake.ticket(project="APP").custom.update({PROJECT: "app", ITEM: f"app/APP-{n + 1}-x"})
    fake.page_size = 2
    assert len(backend_for(tmp_path).item_values()) == 5
    assert len([p for m, p, b in fake.log if p.endswith("/search/jql")]) == 3


def test_set_item_values_edits_each_ticket_still_holding_the_old_value(fake, tmp_path):
    fixtures.seed_tickets(fake)
    edited = []
    backend_for(tmp_path).set_item_values(
        [("APP-1", "app/APP-1-a", "app.work/APP-1-a"),
         ("APP-4", "app/APP-4-d", "app.work/APP-4-d"),      # already done
         ("APP-2", "app/APP-2-b", "app.work/APP-2-b")], edited=edited.append)
    assert fake.custom("APP-1", "TCW Item") == "app.work/APP-1-a"
    assert fake.custom("APP-2", "TCW Item") == "app.work/APP-2-b"
    assert [p for _, p, _ in puts(fake)] == ["/rest/api/3/issue/APP-1",
                                            "/rest/api/3/issue/APP-2"]
    assert edited == ["APP-1", "APP-2"]
    # Only the `TCW Item` field is sent.
    assert [b for _, _, b in puts(fake)] == [{"fields": {ITEM: "app.work/APP-1-a"}},
                                            {"fields": {ITEM: "app.work/APP-2-b"}}]


def test_the_edit_is_the_one_a_move_sends(fake, tmp_path):
    """Criterion 65: method, path form and body, request by request."""
    fake.add_project("APP")
    for _ in range(2):
        fake.ticket(project="APP").custom.update({PROJECT: "app", ITEM: "app.work/APP-1-a"})
    backend = backend_for(tmp_path)
    item_field = backend.metadata().field_ids["item"]
    backend._set_item("APP-1", Slug("app", "APP-1-a"), Slug("app", "APP-1-b"), item_field)
    by_move = puts(fake)
    fake.log.clear()
    backend.set_item_values([("APP-2", "app.work/APP-1-a", "app.work/APP-1-b")])
    by_migrate = puts(fake)
    assert [(m, p.replace("APP-2", "APP-1"), b) for m, p, b in by_migrate] == by_move


def test_the_pairs_swapped_put_every_3x_value_back(fake, tmp_path):
    made = fixtures.seed_tickets(fake)
    pairs = [("APP-1", "app/APP-1-a", "app.work/APP-1-a"),
             ("APP-3", "app/APP-3-gone", "app.work/APP-3-gone")]
    before = {key: dict(t.custom) for key, t in fake.tickets.items()}
    backend = backend_for(tmp_path)
    backend.set_item_values(pairs)
    backend.set_item_values([(key, new, old) for key, old, new in pairs])
    assert {key: dict(t.custom) for key, t in fake.tickets.items()} == before
    assert made["APP-1"]["TCW Item"] == "app/APP-1-a"


def test_a_ticket_holding_another_value_is_left_and_named(fake, tmp_path):
    fixtures.seed_tickets(fake)
    with pytest.raises(BackendError) as raised:
        backend_for(tmp_path).set_item_values(
            [("APP-5", "app/APP-5-e", "app.work/APP-5-e"),
             ("APP-1", "app/APP-1-a", "app.work/APP-1-a")])
    assert "APP-5" in str(raised.value) and "APP-1" not in str(raised.value)
    assert raised.value.pending == ["APP-5"]
    assert fake.custom("APP-1", "TCW Item") == "app.work/APP-1-a"


def test_every_ticket_is_tried_and_a_refused_one_is_named(fake, tmp_path):
    fixtures.seed_tickets(fake)
    fake.fail_edit(1, status=400)
    with pytest.raises(BackendError) as raised:
        backend_for(tmp_path).set_item_values(
            [("APP-1", "app/APP-1-a", "app.work/APP-1-a"),
             ("APP-2", "app/APP-2-b", "app.work/APP-2-b")])
    assert not isinstance(raised.value, Unreachable)
    assert raised.value.pending == ["APP-1"]
    assert fake.custom("APP-2", "TCW Item") == "app.work/APP-2-b"


def test_unreachable_when_any_attempt_could_not_reach_jira(fake, tmp_path):
    fixtures.seed_tickets(fake)
    fake.fail_edit(2, status=400)
    edits = [("APP-1", "app/APP-1-a", "app.work/APP-1-a"),
             ("APP-2", "app/APP-2-b", "app.work/APP-2-b"),
             ("APP-3", "app/APP-3-gone", "app.work/APP-3-gone")]

    def down_after(method, path):
        if method == "GET" and path.startswith("/rest/api/3/issue/APP-3"):
            fake.unreachable()
    fake.before_request(down_after)
    with pytest.raises(Unreachable) as raised:
        backend_for(tmp_path).set_item_values(edits)
    assert raised.value.pending == ["APP-2", "APP-3"]
    assert "APP-2, APP-3" in str(raised.value)


def test_the_same_tickets_whatever_the_work_section(fake, tmp_path):
    """Decided 11: neither method reads `self.config`."""
    fixtures.seed_tickets(fake)
    whole = backend_for(tmp_path, work=_work_section())
    defaults = backend_for(tmp_path)
    assert whole.item_values() == defaults.item_values()
    pairs = [("APP-1", "app/APP-1-a", "app.work/APP-1-a")]
    whole.set_item_values(pairs)
    first = puts(fake)
    whole.set_item_values([(k, n, o) for k, o, n in pairs])
    fake.log.clear()
    defaults.set_item_values(pairs)
    assert puts(fake) == first[:1]
