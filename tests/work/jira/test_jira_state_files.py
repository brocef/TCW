"""A Jira item's state file (TCW-111 Design 1.2, 1.5; AC 1's Jira half and
AC 3's flat Jira case): exactly `tcw-version` and `ticket`, its version
checked first, and never rewritten when it is one this TCW cannot read."""

import pytest
import yaml

from tcw import __version__
from tcw.cli import main
from tests.statefiles import ITEM_STATE
from tests.work.jira.conftest import Result
from tests.work.jira.fake import FIELDS

PROJECT, ITEM = FIELDS["TCW Project"], FIELDS["TCW Item"]

NEWER = "tcw-version: '99.1'\nticket: {site}/browse/{key}\nadded-in-4-1: x\n"


def keys_of(path):
    return set(yaml.safe_load(path.read_text()))


def test_new_writes_the_version_and_the_ticket(jira_project, tcw):
    assert tcw(["new", "Dark mode"], jira_project.root).code == 0
    path = jira_project.work / "TCW-1-dark-mode" / ITEM_STATE
    assert path.read_text() == (f"tcw-version: {__version__}\n"
                                f"ticket: {jira_project.fake.site}/browse/TCW-1\n")
    assert keys_of(path) == {"tcw-version", "ticket"}


def test_adopt_writes_the_version_and_the_ticket(jira_project, tcw):
    key = jira_project.fake.ticket("Fix the login", project="TCW", status="To Do").key
    assert tcw(["tickets", "adopt", key], jira_project.root).code == 0
    path = jira_project.work / f"{key}-fix-the-login" / ITEM_STATE
    assert keys_of(path) == {"tcw-version", "ticket"}
    assert path.read_text().startswith(f"tcw-version: {__version__}\n")


def test_a_newer_state_file_is_read_from_jira_and_reported_as_newer(jira_project, tcw, validate):
    key, name = jira_project.item()
    path = jira_project.work / name / ITEM_STATE
    path.write_text(NEWER.format(site=jira_project.fake.site, key=key))
    shown = tcw(["show", key], jira_project.root)
    assert shown.code == 0, shown.err
    assert f"slug: tcw.work/{name}" in shown.out or name in shown.out
    checked = validate(jira_project)
    assert checked.code == 1
    assert "newer than this TCW" in checked.out and ITEM_STATE in checked.out
    assert "must hold exactly" not in checked.out


def test_adopt_writes_nothing_over_a_state_file_it_cannot_read(jira_project, tcw):
    fake = jira_project.fake
    key = fake.ticket("x", project="TCW", status="To Do").key
    ticket = fake.tickets[key]
    ticket.custom[PROJECT] = "tcw"
    ticket.custom[ITEM] = f"tcw.work/{key}-kept"
    folder = jira_project.work / f"{key}-kept"
    folder.mkdir(parents=True)
    text = NEWER.format(site=fake.site, key=key)
    (folder / ITEM_STATE).write_text(text)
    fake.log.clear()
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 1 and "newer than this TCW" in result.err
    assert fake.writes() == []
    assert (folder / ITEM_STATE).read_text() == text


def test_a_state_file_with_another_key_must_hold_exactly(jira_project, tcw, validate):
    key, name = jira_project.item()
    path = jira_project.work / name / ITEM_STATE
    path.write_text(path.read_text() + "stage: plan\n")
    checked = validate(jira_project)
    assert checked.code == 1
    assert "must hold exactly tcw-version and ticket (and may hold id); it also has " \
           "stage" in checked.out


def test_an_id_naming_the_folder_is_allowed_and_another_is_not(jira_project, tcw, validate):
    key, name = jira_project.item()
    path = jira_project.work / name / ITEM_STATE
    original = path.read_text()
    path.write_text(original + f"id: {name}\n")
    assert validate(jira_project).code == 0
    path.write_text(original + "id: other\n")
    checked = validate(jira_project)
    assert checked.code == 1 and "id 'other'" in checked.out


@pytest.fixture
def validate(monkeypatch, capsys):
    """`tcw validate` in a project, as the `tcw` fixture runs `tcw work`."""
    def run(project):
        monkeypatch.chdir(project.root)
        try:
            code = main(["validate"])
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run
