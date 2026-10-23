"""The footer of each stage prompt in a Jira-mode project, through the fake
(TCW-74 Design 4.1; criterion 5's Jira half). Request and qa are kept by
Jira, so their footer says a person decides, and names the `tcw work advance`
the agent runs once that person says to move the item (TCW-100); every other
stage with files names the plain `advance`."""

import pytest

from tests.fullids import wid

EXTERNAL_SENTENCE = "a person decides whether the item moves on"


def last_block(text: str) -> str:
    return text.rstrip().split("\n\n")[-1]


@pytest.fixture
def item(jira_project):
    key, folder = jira_project.item("Refund a payment", "refund-a-payment")
    return wid(jira_project.id, folder)


@pytest.mark.parametrize("stage", ["request", "qa"])
def test_an_external_stage_footer_moves_only_when_told(stage, item, jira_project, tcw):
    r = tcw(["stage", "prompt", stage, item], jira_project.root)
    assert r.code == 0, r.err
    footer = " ".join(last_block(r.out).split())
    assert EXTERNAL_SENTENCE in footer
    assert "only when that person tells you to" in footer
    assert "a question or an implied yes is not that" in footer
    assert f"`tcw work advance {item} " in footer and "--reason" in footer
    assert f"`tcw work advance {item}`" not in footer
    assert "Do not move it yourself" not in r.out


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
