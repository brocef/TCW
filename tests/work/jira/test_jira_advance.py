"""`advance`, `discard` and `path` in Jira mode, through the CLI (TCW-71 AC 10,
and AC 3's `advance` case). The qa rules are TCW-69's `advance`, unchanged."""

import pytest

from tcw.work.jira.mapping import document_text


def at(project, status, words="x"):
    return project.item("Item", words, status=status)


def newest_comment(project, key):
    return document_text(project.fake.tickets[key].comments[-1]["body"])


def accept_review(project, folder):
    path = project.work / folder / "review" / "round-1.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nverdict: accepted\njudges: 0\n---\n")


def test_a_bare_advance_from_qa_is_refused(jira_project, tcw):
    key, folder = at(jira_project, "In QA")
    result = tcw(["advance", folder], jira_project.root)
    assert result.code == 3, result.err
    assert jira_project.fake.writes() == []


def test_back_to_implement_from_qa_with_a_reason(jira_project, tcw):
    key, folder = at(jira_project, "In QA")
    result = tcw(["advance", folder, "--to", "implement", "--reason", "fails on iOS"],
                 jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].status == "In Progress"
    assert "fails on iOS" in newest_comment(jira_project, key)


def test_completed_from_qa_checks_only_reviews_verdict(jira_project, tcw):
    key, folder = at(jira_project, "In QA")
    refused = tcw(["advance", folder, "--to", "completed", "--reason", "QA passed"],
                  jira_project.root)
    assert refused.code == 3 and "review" in refused.err
    assert jira_project.fake.tickets[key].status == "In QA"
    accept_review(jira_project, folder)
    result = tcw(["advance", folder, "--to", "completed", "--reason", "QA passed"],
                 jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].status == "Done"
    assert not (jira_project.work / folder / "qa").exists()


def test_inbox_is_refused(jira_project, tcw):
    key, folder = at(jira_project, "Triage")
    result = tcw(["advance", folder, "--to", "inbox", "--force", "--reason", "back"],
                 jira_project.root)
    assert result.code == 3
    assert jira_project.fake.tickets[key].status == "Triage"


def test_discard_from_an_unmapped_status(jira_project, tcw):
    jira_project.fake.projects["TCW"].statuses += ("Backlog",)
    key, folder = at(jira_project, "Backlog")
    result = tcw(["discard", folder, "--reason", "not needed"], jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].status == "Won't Do"
    assert "not needed" in newest_comment(jira_project, key)


@pytest.mark.parametrize("stage", ["request", "qa"])
@pytest.mark.parametrize("handoff", [False, True])
def test_path_to_a_stage_jira_keeps_is_refused(jira_project, tcw, stage, handoff):
    _, folder = at(jira_project, "In Progress")
    result = tcw(["path", folder, stage, *(["--handoff"] if handoff else [])],
                 jira_project.root)
    assert result.code == 3
    assert "Jira" in result.err


def test_typing_a_key_to_advance(jira_project, tcw):
    key, folder = at(jira_project, "Triage")
    result = tcw(["advance", key], jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].status == "Specifying"
    assert jira_project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]
