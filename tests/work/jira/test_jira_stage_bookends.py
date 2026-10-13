"""The footer of each stage prompt in a Jira-mode project, through the fake
(TCW-74 Design 4.1; criterion 5's Jira half). Request and qa are kept by
Jira, so their footer names no `tcw work advance`; every other stage with
files names it."""

import pytest

EXTERNAL_SENTENCE = "a person moves the item on in the backend"


def last_block(text: str) -> str:
    return text.rstrip().split("\n\n")[-1]


@pytest.fixture
def item(jira_project):
    key, folder = jira_project.item("Refund a payment", "refund-a-payment")
    return f"{jira_project.id}/{folder}"


@pytest.mark.parametrize("stage", ["request", "qa"])
def test_an_external_stage_footer_names_no_advance(stage, item, jira_project, tcw):
    r = tcw(["stage", "prompt", stage, item], jira_project.root)
    assert r.code == 0, r.err
    footer = last_block(r.out)
    assert EXTERNAL_SENTENCE in footer
    assert "tcw work advance" not in footer


@pytest.mark.parametrize("stage", ["spec", "plan", "implement", "review"])
def test_a_stage_with_files_names_advance(stage, item, jira_project, tcw):
    r = tcw(["stage", "prompt", stage, item], jira_project.root)
    assert r.code == 0, r.err
    footer = last_block(r.out)
    assert f"`tcw work advance {item}`" in footer
    assert EXTERNAL_SENTENCE not in footer
    assert "<slug>" not in r.out


def test_the_jira_text_is_the_jira_passages(item, jira_project, tcw):
    r = tcw(["stage", "prompt", "qa", item], jira_project.root)
    assert r.code == 0, r.err
    assert "qa happens on the ticket" in r.out
    assert "--next" not in r.out and "<!--" not in r.out
