"""The scenario of Design 15.4 against the fake (CI), and against the real
`TCWTEST` project when `TCW_JIRA_LIVE=1` and its credentials are set
(TCW-71 AC 23; the live run is by hand)."""

import os
from pathlib import Path

import pytest

from tests.work.jira import scenario
from tests.work.jira.capture import Recorder
from tests.work.projects import make_project

#: An epic in another Jira project on the same site, for the cross-project
#: parent question: TCWCLAIM, the 2.x claim experiment's fixture project.
OTHER_PARENT = "TCWCLAIM-7"

#: The live configuration, exactly as `tcwtest-checklist.md` ends.
LIVE = {
    "backend": "jira",
    "tags": ["ui", "api"],
    "jira": {
        "site": "https://proposit.atlassian.net",
        "project": "TCWTEST",
        "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_KEY"},
        "fields": {"project": "TCW Project", "item": "TCW Item", "effort": "Effort",
                   "complexity": "Complexity"},
    },
    "stages": {
        "inbox": {"status": "To Do"},
        "request": {"status": "Triage"},
        "spec": {"enabled": True, "status": "Specifying"},
        "plan": {"enabled": True, "status": "Planning"},
        "implement": {"status": "In Progress"},
        "review": {"enabled": True, "status": "In Review"},
        "qa": {"enabled": True, "status": "In QA"},
        "completed": {"status": "Done"},
        "discarded": {"status": "Won't Do"},
    },
}


def test_the_scenario_against_the_fake(jira_project):
    result = scenario.run(jira_project.root, live=False, say=lambda line: None)
    assert result.lag < 1
    code, out, err = result.validate
    assert code == 0, out + err
    assert jira_project.fake.tickets[result.keys["item"]].status == "Won't Do"


@pytest.mark.skipif(os.environ.get("TCW_JIRA_LIVE") != "1"
                    or not os.environ.get("TCW_JIRA_EMAIL")
                    or not os.environ.get("TCW_JIRA_API_KEY"),
                    reason="the live check runs by hand: TCW_JIRA_LIVE=1 and the "
                           "credential variables")
def test_the_scenario_live(tmp_path, monkeypatch):
    if os.environ.get("TCW_JIRA_CAPTURE"):
        Recorder(Path(os.environ["TCW_JIRA_CAPTURE"]),
                 LIVE["jira"]["site"], LIVE["jira"]["project"]).install(monkeypatch)
    root = make_project(tmp_path, "tcw-test-live", config=LIVE)
    result = scenario.run(root, live=True)
    code, out, err = result.validate
    print(f"lag {result.lag:.1f}s; keys {result.keys}")
    print(f"validate --remote exited {code}\n{out}{err}")
    scenario.probe(root, result, other_parent=OTHER_PARENT)
