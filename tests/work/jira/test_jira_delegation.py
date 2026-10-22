"""`tcw work new --project <id>` into a Jira-mode project (TCW-71 AC 17, and
AC 14's last bullet for delegation)."""

import shutil

import pytest
import yaml

from tests.work.jira.conftest import EMAIL_ENV, TOKEN_ENV, jira_config
from tests.work.jira.fake import FIELDS, SITE
from tests.work.projects import commit_all, connect, make_project
from tests.projectfiles import config_file, write_config_file, write_local_config
from tests.projectfiles import write_connected_config_file

ITEM, PROJECT = FIELDS["TCW Item"], FIELDS["TCW Project"]


@pytest.fixture
def pair(tmp_path, fake):
    """`p`, a filesystem project, with `tcw`, a Jira-mode project, as its child."""
    target_config = jira_config()
    out = tmp_path / "hook-ran"
    for kind in ("pre", "post"):
        target_config["stages"]["request"][kind] = [{"command": f"touch {out}"}]
    target = make_project(tmp_path, "tcw", config=target_config)
    p = make_project(tmp_path, "p", config={})
    connect(p, target, "children")
    commit_all(target)
    commit_all(p)
    return p, target, out


def test_a_creatable_folder_makes_the_item(pair, fake, tcw):
    p, target, hook = pair
    result = tcw(["new", "Add export", "--project", "tcw"], p, stdin="Please add it")
    assert result.code == 0, result.err
    assert result.out.strip() == "tcw/TCW-1-add-export"
    ticket = fake.tickets["TCW-1"]
    assert (ticket.custom[PROJECT], ticket.custom[ITEM]) == ("tcw", "tcw/TCW-1-add-export")
    assert ticket.status == "Triage"
    assert (target / "docs" / "work" / "TCW-1-add-export" / "item.yaml").is_file()
    assert "uncommitted" in result.err
    # The next filing there would stay in the inbox until these are committed
    # (TCW-101), so the message says so.
    assert "before filing into tcw again" in " ".join(result.err.split())
    assert not hook.exists()                         # creation runs no hooks


def test_uncommitted_changes_keep_it_in_the_inbox(pair, fake, tcw):
    p, target, _ = pair
    (target / "docs" / "work" / "scratch.md").write_text("mine")
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert (result.code, result.out.strip()) == (0, "TCW-1")
    assert fake.tickets["TCW-1"].status == "To Do"
    assert ITEM not in fake.tickets["TCW-1"].custom
    assert "uncommitted changes" in result.err


def test_no_route_to_request_keeps_it_in_the_inbox(pair, fake, tcw):
    p, _, _ = pair
    flow = fake.projects["TCW"]
    flow.transitions = [t for t in flow.transitions if t.to != "Triage"]
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert (result.code, result.out.strip()) == (0, "TCW-1")
    assert fake.tickets["TCW-1"].status == "To Do"


def block_for(p, block):
    path = config_file(p)
    doc = yaml.safe_load(path.read_text())
    # The entry's location is in the manifest `connect` wrote (TCW-107).
    doc["projects"]["children"]["tcw"] = {"jira": block}
    write_connected_config_file(path, yaml.safe_dump(doc, sort_keys=False))


BLOCK = {"site": SITE, "project": "TCW", "inbox-status": "To Do",
         "credentials": {"email-env": EMAIL_ENV, "token-env": TOKEN_ENV},
         "fields": {"project": "TCW Project"}}


def test_a_target_not_here_with_a_jira_block(pair, fake, tcw):
    p, target, _ = pair
    shutil.rmtree(target)
    block_for(p, BLOCK)
    result = tcw(["new", "Add export", "--project", "tcw", "--priority", "high"], p)
    assert (result.code, result.out.strip()) == (0, "TCW-1")
    ticket = fake.tickets["TCW-1"]
    assert (ticket.status, ticket.priority, ticket.custom[PROJECT]) == (
        "To Do", "High", "tcw")
    assert ITEM not in ticket.custom
    assert "not on this machine" in result.err


def test_a_target_not_here_without_a_block(pair, fake, tcw):
    p, target, _ = pair
    shutil.rmtree(target)
    assert tcw(["new", "Add export", "--project", "tcw"], p).code == 3
    assert fake.log == []


def test_the_block_is_only_read_when_the_target_is_not_here(pair, fake, tcw):
    p, _, _ = pair
    block_for(p, dict(BLOCK, site="https://elsewhere.atlassian.net"))
    commit_all(p)
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert result.code == 0, result.err
    assert fake.tickets["TCW-1"].custom[ITEM] == "tcw/TCW-1-add-export"


def test_other_property_flags_are_usage_errors(pair, fake, tcw):
    p, _, _ = pair
    assert tcw(["new", "Add export", "--project", "tcw", "--tag", "ui"], p).code == 2
    assert fake.log == []


def test_a_refused_inbox_move_prints_the_created_key(pair, fake, tcw):
    p, target, _ = pair
    shutil.rmtree(target)
    block_for(p, {**BLOCK, "inbox-status": "Specifying"})
    flow = fake.projects["TCW"]
    flow.transitions = [t for t in flow.transitions if t.to != "Specifying"]
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert (result.code, result.out.strip()) == (3, "TCW-1")


# -- TCW-72 AC 9: a Jira-mode target is read without the person's own files -----------


def test_the_targets_local_file_is_not_read(pair, fake, tcw, monkeypatch):
    p, target, _ = pair
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    write_local_config(target, "id: wrong\n")
    commit_all(target)
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert result.code == 0, result.err
    assert result.out.strip() == "tcw/TCW-1-add-export"


def test_a_user_wide_token_name_does_not_reach_the_target(pair, fake, tcw, monkeypatch,
                                                          tmp_path):
    p, _, _ = pair
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    user = tmp_path / "xdg-config" / "tcw" / "config.yaml"
    user.parent.mkdir(parents=True)
    user.write_text("work:\n  jira:\n    credentials:\n"
                    "      token-env: TCW_TEST_NOT_SET\n")
    monkeypatch.delenv("TCW_TEST_NOT_SET", raising=False)
    result = tcw(["new", "Add export", "--project", "tcw"], p)
    assert result.code == 0, result.err
    assert result.out.strip() == "tcw/TCW-1-add-export"
