"""The `tracker.yaml` binding: its registration as a sidecar, and the rules for
reading one.

A binding is what records that a work item answers a tracker ticket. Two
properties matter more than the rest:

- **A command writes it, so no edit surface offers to.** The web client hides its
  Edit affordance for a sidecar the server reports as `generated`.
- **An unreadable binding is never read as "no binding".** A lookup that skipped
  one could not say the ticket is not already bound, so it refuses instead.
"""

from __future__ import annotations

import json
import subprocess
import threading
from urllib.request import urlopen

import pytest
import yaml

from tcw.serve import HOST, TcwServer
from tcw.store.fs import FsWorkStore, init
from tcw.tracker import intake

BINDING = """\
schema: 1
provider: jira-cloud
project: probe
part: default
ticket:
    id: "10052"
    key: TCWCLAIM-6
    url: https://example.invalid/browse/TCWCLAIM-6
bound: "2026-09-14"
unlinked: []
"""


KEY = dict(project="probe", provider="jira-cloud", ticket_id="10052", part="default")


@pytest.fixture()
def store(tmp_path):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, project_id="probe")
    return FsWorkStore.open(root)


def _bound_item(store, title, content=BINDING, *, completed=False):
    """An item carrying `content` as its binding, optionally resolved.

    The binding is written while the item is in `backlog` and travels with it,
    because a resolved item's folder is not tracked and cannot be staged.
    """
    item = store.create(title)
    store.write_sidecar(item.slug, "tracker.yaml", content)
    if completed:
        store.start(item.slug)
        store.complete(item.slug, "done", ["acked"])
    return item.slug


# ── the sidecar ──────────────────────────────────────────────────────────────


def test_a_binding_round_trips_through_the_sidecar_surface(store):
    item = store.create("Bound item")
    store.write_sidecar(item.slug, "tracker.yaml", BINDING)
    assert store.read_sidecar(item.slug, "tracker.yaml").content == BINDING


def test_a_binding_that_is_not_a_mapping_is_refused_on_write(store):
    item = store.create("Bound item")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        store.write_sidecar(item.slug, "tracker.yaml", "- TCWCLAIM-6\n")
    assert store.read_sidecar(item.slug, "tracker.yaml") is None


def test_the_web_api_reports_the_binding_as_generated(store):
    item = store.create("Bound item")
    httpd = TcwServer((HOST, 0), store.node_root)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        url = f"http://{HOST}:{httpd.server_port}/api/work/{item.slug}/sidecars"
        with urlopen(url) as response:
            sidecars = json.loads(response.read())
    finally:
        httpd.shutdown()
        httpd.server_close()
    tracker = next(s for s in sidecars if s["name"] == "tracker.yaml")
    assert tracker["generated"] is True


# ── reading a binding ────────────────────────────────────────────────────────


def test_no_file_is_unbound():
    assert isinstance(intake.read_binding(None), intake.Unbound)


def test_a_file_that_is_not_a_mapping_is_malformed():
    assert isinstance(intake.read_binding("- TCWCLAIM-6\n"), intake.Malformed)
    assert isinstance(intake.read_binding("ticket: [unclosed\n"), intake.Malformed)


def test_a_mapping_without_a_ticket_is_unbound():
    """The state `unlink` leaves behind: history kept, nothing bound."""
    assert isinstance(intake.read_binding("schema: 1\nunlinked: []\n"), intake.Unbound)


def test_a_complete_binding_is_bound_with_its_values():
    bound = intake.read_binding(BINDING)
    assert bound == intake.Bound(
        provider="jira-cloud", project="probe", part="default", ticket_id="10052",
        ticket_key="TCWCLAIM-6", ticket_url="https://example.invalid/browse/TCWCLAIM-6")


@pytest.mark.parametrize("broken", [
    BINDING.replace('    id: "10052"\n', ""),
    BINDING.replace("    key: TCWCLAIM-6\n", ""),
    BINDING.replace("provider: jira-cloud\n", ""),
    BINDING.replace("project: probe\n", ""),
    BINDING.replace("part: default\n", ""),
    BINDING.replace("part: default\n", "part: ''\n"),
    "schema: 1\nprovider: jira-cloud\nproject: probe\npart: default\nticket: TCWCLAIM-6\n",
], ids=["no-id", "no-key", "no-provider", "no-project", "no-part", "empty-part",
        "ticket-is-a-string"])
def test_a_ticket_in_any_other_shape_is_malformed(broken):
    assert isinstance(intake.read_binding(broken), intake.Malformed)


# ── parts ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value", ["default", "api", "web-2", "9"])
def test_a_part_name_is_accepted(value):
    assert intake.validate_part(value) == value


def test_a_missing_part_is_default():
    assert intake.validate_part(None) == "default"


@pytest.mark.parametrize("value", ["API", "-x", "a b", "", "a/b"])
def test_a_bad_part_name_is_refused_and_named(value):
    with pytest.raises(ValueError, match=repr(value)):
        intake.validate_part(value)


# ── finding the item bound to a key ──────────────────────────────────────────


def test_the_bound_item_is_found_by_its_key(store):
    slug = _bound_item(store, "Bound item")
    store.create("Unrelated item")
    assert intake.find_binding(store, **KEY) == slug


@pytest.mark.parametrize("field,other", [
    ("project", "elsewhere"), ("provider", "other-tracker"),
    ("ticket_id", "10053"), ("part", "api"),
])
def test_a_key_differing_in_any_field_does_not_match(store, field, other):
    _bound_item(store, "Bound item")
    assert intake.find_binding(store, **{**KEY, field: other}) is None


def test_a_resolved_item_is_not_consulted(store):
    _bound_item(store, "Finished item", completed=True)
    assert intake.find_binding(store, **KEY) is None


def test_a_malformed_binding_refuses_the_lookup_and_names_the_item(store):
    slug = _bound_item(store, "Broken item", "ticket: TCWCLAIM-6\n")
    with pytest.raises(intake.BindingProblem, match=slug):
        intake.find_binding(store, **KEY)


def test_two_items_holding_one_key_refuse_and_name_both(store):
    first = _bound_item(store, "First")
    second = _bound_item(store, "Second")
    with pytest.raises(intake.BindingProblem) as refused:
        intake.find_binding(store, **KEY)
    assert first in str(refused.value) and second in str(refused.value)


def test_problems_on_resolved_items_change_nothing(store):
    _bound_item(store, "Broken but finished", "ticket: TCWCLAIM-6\n", completed=True)
    _bound_item(store, "Duplicate but finished", completed=True)
    slug = _bound_item(store, "Live item")
    assert intake.find_binding(store, **KEY) == slug


# ── writing a binding ────────────────────────────────────────────────────────


def _document(**overrides):
    values = dict(provider="jira-cloud", project="probe", part="default",
                  ticket_id="10052", ticket_key="TCWCLAIM-6",
                  ticket_url="https://example.invalid/browse/TCWCLAIM-6",
                  bound="2026-09-14", unlinked=[])
    values.update(overrides)
    return intake.binding_document(**values)


def test_a_written_binding_reads_back_as_bound():
    text = _document()
    assert intake.read_binding(text) == intake.read_binding(BINDING)
    assert yaml.safe_load(text) == yaml.safe_load(BINDING)


def test_unlinking_leaves_an_unbound_document_with_the_reason():
    text = intake.unlink_document(_document(), reason="wrong ticket", today="2026-09-15")
    assert isinstance(intake.read_binding(text), intake.Unbound)
    data = yaml.safe_load(text)
    assert data["schema"] == 1
    [entry] = data["unlinked"]
    assert entry["ticket"]["key"] == "TCWCLAIM-6"
    assert "claimed-by" not in entry
    assert (entry["reason"], entry["unlinked-on"]) == ("wrong ticket", "2026-09-15")


LEGACY = BINDING.replace('bound: "2026-09-14"\n', '''claimed-by:
    account-id: acct-a
    name: Probe
bound: "2026-09-14"
''')


def test_a_binding_written_before_claiming_was_dropped_still_reads_as_bound():
    """`claimed-by` used to be written and is not migrated away. An old document
    keeps every field a binding needs, so the stale key is ignored, not fatal."""
    assert intake.read_binding(LEGACY) == intake.read_binding(BINDING)


def test_unlinking_an_old_binding_leaves_its_stale_claim_behind():
    """`_BINDING_KEYS` no longer lists `claimed-by`, so `unlink_document` does not
    move it into the history entry. It stays at the top level rather than crashing
    the unlink — the accepted cost of shipping no migration."""
    text = intake.unlink_document(LEGACY, reason="wrong ticket", today="2026-09-15")
    data = yaml.safe_load(text)
    assert isinstance(intake.read_binding(text), intake.Unbound)
    [entry] = data["unlinked"]
    assert "claimed-by" not in entry
    assert data["claimed-by"] == {"account-id": "acct-a", "name": "Probe"}


def test_history_survives_a_second_binding_and_a_second_unlink():
    first = intake.unlink_document(_document(), reason="one", today="2026-09-15")
    rebound = _document(ticket_id="10053", ticket_key="TCWCLAIM-7",
                        unlinked=yaml.safe_load(first)["unlinked"])
    second = intake.unlink_document(rebound, reason="two", today="2026-09-16")
    assert [e["reason"] for e in yaml.safe_load(second)["unlinked"]] == ["one", "two"]


def test_validate_holds_a_binding_to_the_mapping_contract(store):
    """`tracker.yaml` is a record TCW writes, so `tcw validate` treats it like
    `state.yaml`: a binding that is not a mapping is reported. A syntax error in it
    was already reported, as for every YAML file in the store."""
    from tcw.validate import validate

    slug = store.create("Hand-edited").slug
    (store.path(slug) / "tracker.yaml").write_text("- TCWCLAIM-6\n", encoding="utf-8")
    problems = validate(store.node_root)
    assert any("tracker.yaml: expected a mapping" in p for p in problems), problems
