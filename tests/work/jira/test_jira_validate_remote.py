"""`tcw validate --remote` (TCW-71 AC 18). Every case asserts, from the
fake's log, that nothing was written."""

import re
from dataclasses import dataclass

import pytest
import yaml

from tcw.cli import main
from tcw.work.model import Changes
from tests.work.jira.conftest import JiraProject, jira_config
from tests.work.jira.fake import FIELDS, Transition as Route
from tests.work.projects import make_project

ITEM = FIELDS["TCW Item"]
LINE = re.compile(r"^(error|warning|unresolved): \S+: .+$")


@dataclass
class Run:
    code: int
    out: str
    err: str

    @property
    def lines(self):
        return [line for line in self.out.splitlines() if line]


def remote(project, monkeypatch, capsys) -> Run:
    project.fake.log.clear()
    monkeypatch.chdir(project.root)
    code = main(["validate", "--remote"])
    captured = capsys.readouterr()
    run = Run(code, captured.out, captured.err)
    assert all(LINE.match(line) for line in run.lines), run.out
    assert project.fake.writes() == []
    return run


@pytest.fixture
def clean(jira_project):
    """One item, and a ticket of each issue type the checks sample."""
    jira_project.item("Item", "x")
    jira_project.fake.ticket("A sub-task", issue_type="Subtask", parent="TCW-1")
    return jira_project


def test_a_clean_project_prints_nothing_on_stdout(clean, monkeypatch, capsys):
    run = remote(clean, monkeypatch, capsys)
    assert (run.code, run.out) == (0, ""), run.err
    assert "screen fields left unchecked" in run.err


def test_filesystem_mode_is_a_usage_error(tmp_path, fake, monkeypatch, capsys):
    root = make_project(tmp_path, "p", config={})
    monkeypatch.chdir(root)
    assert main(["validate", "--remote"]) == 2
    assert fake.log == []


def configured(tmp_path, fake, change) -> JiraProject:
    config = jira_config()
    change(config)
    project = JiraProject(make_project(tmp_path, "tcw", config=config), "tcw", fake)
    project.item("Item", "x")
    fake.ticket("A sub-task", issue_type="Subtask", parent="TCW-1")
    return project


def test_a_missing_tcw_item_field(tmp_path, fake, monkeypatch, capsys):
    project = configured(tmp_path, fake,
                         lambda c: c["jira"]["fields"].update(item="No Such Field"))
    run = remote(project, monkeypatch, capsys)
    assert run.code == 1
    assert any("work.jira.fields.item 'No Such Field' is not on the Task create screen"
               in line for line in run.lines), run.out
    # The checks after the fields still run: one missing field does not stop them.
    assert not any("remaining remote checks did not run" in line
                   for line in run.lines), run.out
    assert "items and tickets were not checked" in run.err, run.err


def test_tcw_item_off_an_edit_screen_and_an_unsampled_type(jira_project, monkeypatch,
                                                           capsys):
    jira_project.item("Item", "x")
    jira_project.fake.off_edit_screen.add(("Task", ITEM))
    run = remote(jira_project, monkeypatch, capsys)
    assert run.code == 1
    assert "error: work.jira: TCW Item is not on the Task edit screen (read on TCW-1), " \
           "so TCW cannot change it" in run.lines
    assert "warning: work.jira: unchecked: the Subtask edit screen: no Subtask ticket in " \
           "TCW to sample" in run.lines


def test_the_top_level_type_needs_no_parent_field(clean, monkeypatch, capsys):
    """Jira gives an Epic no Parent field, since nothing sits above it; the
    Task below it still needs one."""
    clean.item("An epic", "e", issue_type="Epic")
    run = remote(clean, monkeypatch, capsys)
    assert not [line for line in run.lines if "Epic edit screen" in line], run.lines
    assert not [line for line in run.lines if "Parent is not on" in line], run.lines
    clean.fake.off_edit_screen.add(("Task", "parent"))
    run = remote(clean, monkeypatch, capsys)
    assert "error: work.jira: Parent is not on the Task edit screen (read on TCW-1), " \
           "so TCW cannot change it" in run.lines


def test_an_epic_configured_type_needs_no_parent_on_create(tmp_path, fake, monkeypatch,
                                                          capsys):
    project = configured(tmp_path, fake, lambda c: c["jira"].update(**{"issue-type": "Epic"}))
    run = remote(project, monkeypatch, capsys)
    assert not any("Parent is not on" in line for line in run.lines), run.out


def test_without_an_epic_type_a_task_still_needs_parent(clean, monkeypatch, capsys):
    """Only a top level of 1 or more is spared Parent: a Task in a project with
    no Epic type can still take a parent in another project."""
    flow = clean.fake.projects["TCW"]
    flow.issue_types = tuple(t for t in flow.issue_types if t.level < 1)
    clean.fake.off_edit_screen.add(("Task", "parent"))
    run = remote(clean, monkeypatch, capsys)
    assert "error: work.jira: Parent is not on the Task edit screen (read on TCW-1), " \
           "so TCW cannot change it" in run.lines, run.out


def test_a_refused_key_search_reports_only_the_gone_ticket(clean, monkeypatch, capsys):
    (clean.work / "TCW-50-gone").mkdir()
    clean.fake.refuse_missing_key_search = True
    run = remote(clean, monkeypatch, capsys)
    # The offline check's line for the folder's missing `item.yaml` shares
    # stdout with the remote findings since TCW-73 (Design 6.3).
    remote_lines = [line for line in run.lines if "item.yaml" not in line]
    assert remote_lines == ["error: tcw/TCW-50-gone: its ticket TCW-50 does not exist in "
                            "Jira, or this account cannot see it"], run.out


def test_search_lag_gives_a_new_item_no_finding(clean, monkeypatch, capsys):
    item = clean.backend().create("Fresh", Changes(), stage="request", request=None)
    clean.fake.search_lag = 1000
    run = remote(clean, monkeypatch, capsys)
    assert not any(str(item.slug) in line for line in run.lines), run.out


def test_records_problems_mid_work_only(clean, monkeypatch, capsys):
    _, open_ = clean.item("Open", "open", status="In Progress")
    _, done = clean.item("Done", "done", status="Done")
    for folder in (open_, done):
        (clean.work / folder / "capabilities.yaml").write_text("no-such-key: 1\n")
    run = remote(clean, monkeypatch, capsys)
    assert run.code == 1
    assert any(line.startswith(f"error: tcw/{open_}:") for line in run.lines), run.out
    assert not any(f"tcw/{done}" in line for line in run.lines), run.out


def test_records_problems_wait_for_remote_offline(clean, monkeypatch, capsys):
    """TCW-73 AC 15: the stage that decides whether the records check runs is
    in Jira, so plain `tcw validate` leaves it to `--remote` and asks Jira
    nothing."""
    _, open_ = clean.item("Open", "open", status="In Progress")
    (clean.work / open_ / "capabilities.yaml").write_text("no-such-key: 1\n")
    clean.fake.log.clear()
    monkeypatch.chdir(clean.root)
    assert main(["validate"]) == 0
    assert "capabilities.yaml" not in capsys.readouterr().out
    assert clean.fake.log == []


def test_a_stage_status_missing_from_the_project(tmp_path, fake, monkeypatch, capsys):
    project = configured(tmp_path, fake,
                         lambda c: c["stages"]["qa"].update(status="In Quality"))
    run = remote(project, monkeypatch, capsys)
    assert run.code == 1
    assert "error: work.jira: status 'In Quality' (stage qa) is not a status of Task " \
           "in TCW" in run.lines


def routes_into(project, status, *extra):
    flow = project.fake.projects["TCW"]
    flow.transitions = [t for t in flow.transitions if t.to != status] + list(extra)


MOVE = "the move from 'Specifying' to 'Planning' (spec to plan) for Task"


def test_a_needed_move_with_no_transition(clean, monkeypatch, capsys):
    routes_into(clean, "Planning")
    run = remote(clean, monkeypatch, capsys)
    assert f"error: work.jira: no transition makes {MOVE}" in run.lines


@pytest.mark.parametrize("second, verdict", [
    ({}, "error"),                                   # both ask for nothing but a comment
    ({"resolution": False}, None),                   # the rule picks the plain one
])
def test_two_candidates_are_decided_by_a_sample(clean, monkeypatch, capsys, second,
                                                verdict):
    routes_into(clean, "Planning", Route("90", "Plan", "Planning"),
                Route("91", "Plan too", "Planning", screen=second))
    clean.fake.ticket("At spec", status="Specifying")
    run = remote(clean, monkeypatch, capsys)
    about = [line for line in run.lines if MOVE in line]
    if verdict is None:
        assert about == [], run.out
    else:
        assert len(about) == 1 and about[0].startswith("error:") and "several" in about[0]


def test_two_candidates_with_no_sample_are_unchecked(clean, monkeypatch, capsys):
    routes_into(clean, "Planning", Route("90", "Plan", "Planning"),
                Route("91", "Plan too", "Planning"))
    run = remote(clean, monkeypatch, capsys)
    assert f"warning: work.jira: unchecked: {MOVE}: no Task ticket is at 'Specifying' " \
           f"to sample" in run.lines


def test_without_the_definition_moves_are_sampled(clean, monkeypatch, capsys):
    clean.fake.workflows_forbidden = True
    triage = next(t for t in clean.fake.projects["TCW"].transitions if t.to == "Specifying")
    clean.fake.require_screen_field(triage.id, "resolution")
    run = remote(clean, monkeypatch, capsys)
    assert run.code == 1
    assert any(line.startswith("error: work.jira: the move from 'Triage' to 'Specifying'")
               and "requires resolution" in line for line in run.lines), run.out
    assert any(line.startswith("warning: work.jira: unchecked: the move from "
                               "'Specifying' to 'Planning'") for line in run.lines)
    assert "could not be read (no permission, or an empty answer)" in run.err


def test_tcw_item_naming_another_slug(clean, monkeypatch, capsys):
    clean.fake.tickets["TCW-1"].custom[ITEM] = "tcw/TCW-1-other"
    run = remote(clean, monkeypatch, capsys)
    assert "error: tcw/TCW-1-x: its ticket's TCW Item is 'tcw/TCW-1-other', not " \
           "'tcw/TCW-1-x'" in run.lines


def test_a_ticket_answered_under_another_key(clean, monkeypatch, capsys):
    moved = clean.fake.ticket("Moved")
    moved.custom.update({FIELDS["TCW Project"]: "tcw", ITEM: "tcw/TCW-9-moved"})
    folder = clean.work / "TCW-9-moved"
    folder.mkdir()
    (folder / "item.yaml").write_text(yaml.safe_dump(
        {"ticket": f"{clean.fake.site}/browse/TCW-9"}))
    clean.fake.tickets["TCW-9"] = moved
    run = remote(clean, monkeypatch, capsys)
    assert any(line.startswith(f"error: tcw/TCW-9-moved: Jira answers for TCW-9 with "
                               f"{moved.key}") for line in run.lines), run.out


def test_warnings_alone_exit_zero(clean, monkeypatch, capsys):
    clean.item("Elsewhere", "elsewhere", folder=False)
    clean.item("Waiting", "waiting", status="To Do")
    run = remote(clean, monkeypatch, capsys)
    assert run.code == 0, run.out
    assert "warning: TCW-3: names tcw/TCW-3-elsewhere, whose folder is not here; the " \
           "item may exist in another copy of this repository" in run.lines
    assert any(line.startswith("warning: tcw/TCW-4-waiting: its ticket is at the inbox "
                               "status") for line in run.lines)


def test_unreachable_mid_run(tmp_path, fake, monkeypatch, capsys):
    project = configured(tmp_path, fake,
                         lambda c: c["jira"].update(priorities={"high": "Major"}))
    answer = fake.answer

    def failing(client, method, path, body):
        if path.endswith("/statuses"):
            fake.unreachable()
        return answer(client, method, path, body)
    monkeypatch.setattr(fake, "answer", failing)
    run = remote(project, monkeypatch, capsys)
    assert run.code == 5
    assert "error: work.jira: priority 'Major' (work.jira.priorities.high) is not a " \
           "priority of TCW" in run.lines
    assert run.lines[-1].startswith("unresolved: tcw: Jira could not be reached")


def test_rejected_credentials_skip_the_rest(clean, monkeypatch, capsys):
    clean.fake.unauthorized()
    run = remote(clean, monkeypatch, capsys)
    assert run.code == 1 and len(run.lines) == 1
    assert run.lines[0].startswith("error: work.jira: Jira rejected the credentials")
    assert "remaining remote checks were skipped" in run.err


def test_a_missing_status_without_the_definition_keeps_every_finding(
        tmp_path, fake, monkeypatch, capsys):
    project = configured(tmp_path, fake,
                         lambda c: c["stages"]["qa"].update(status="In Quality"))
    fake.workflows_forbidden = True
    run = remote(project, monkeypatch, capsys)
    assert run.code == 1
    assert "error: work.jira: status 'In Quality' (stage qa) is not a status of Task " \
           "in TCW" in run.lines
    assert not any("did not run" in line for line in run.lines), run.out
    # Moves into or out of the missing status are not sampled: no ticket can
    # be there, and Jira's search just answers with none.
    assert not any("unchecked:" in line and "In Quality" in line
                   for line in run.lines), run.out


def test_a_refused_read_keeps_what_was_found(tmp_path, fake, monkeypatch, capsys):
    project = configured(tmp_path, fake,
                         lambda c: c["jira"].update(priorities={"high": "Major"}))
    answer = fake.answer

    def refusing(client, method, path, body):
        if path.endswith("/statuses"):
            raise fake._error(403, path, "You do not have permission")
        return answer(client, method, path, body)
    monkeypatch.setattr(fake, "answer", refusing)
    run = remote(project, monkeypatch, capsys)
    assert run.code == 1
    assert "error: work.jira: priority 'Major' (work.jira.priorities.high) is not a " \
           "priority of TCW" in run.lines
    assert run.lines[-1].startswith("error: work.jira: Jira refused a read, so the "
                                    "remaining remote checks did not run")


def test_the_create_transition_is_no_route(clean, monkeypatch, capsys):
    flow = clean.fake.projects["TCW"]
    flow.statuses = ("Triage",) + tuple(s for s in flow.statuses if s != "Triage")
    routes_into(clean, "Triage")       # only the create transition leads there now
    run = remote(clean, monkeypatch, capsys)
    assert "error: work.jira: no transition makes the move from 'To Do' to 'Triage' " \
           "(inbox to request) for Task" in run.lines, run.out


def test_an_empty_definition_is_sampled_rather_than_failed(clean, monkeypatch, capsys):
    monkeypatch.setattr(clean.fake, "_workflows",
                        lambda body, route: {"statuses": [], "workflows": []})
    run = remote(clean, monkeypatch, capsys)
    assert not any("no transition makes" in line for line in run.lines), run.out
    assert "or an empty answer" in run.err


@pytest.mark.parametrize("entry, expected", [
    ({"fieldId": "customfield_1", "key": "customfield_1"}, "customfield_1"),
    ({"key": "customfield_2"}, "customfield_2"),        # an older answer
])
def test_field_id_reads_field_id_then_key(entry, expected):
    from tcw.work.jira.backend import field_id
    assert field_id(entry) == expected
