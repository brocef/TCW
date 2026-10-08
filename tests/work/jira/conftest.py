"""Fixtures for the Jira backend's tests: a Jira-mode project wired to the fake
(TCW-71 plan Task 7)."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.work.open import open_backend
from tests.work.jira.fake import FIELDS, SITE, FakeJira
from tests.work.projects import make_project

EMAIL_ENV, TOKEN_ENV = "TCW_TEST_JIRA_EMAIL", "TCW_TEST_JIRA_TOKEN"
ME = "acct-dev"

#: The nine statuses of the TCWTEST checklist, by stage.
STATUSES = {"inbox": "To Do", "request": "Triage", "spec": "Specifying",
            "plan": "Planning", "implement": "In Progress", "review": "In Review",
            "qa": "In QA", "completed": "Done", "discarded": "Won't Do"}
OPTIONAL = ("spec", "plan", "review", "qa")


def jira_config(project_id: str = "tcw", *, jira_project: str = "TCW",
                site: str = SITE, tags=("ui", "api"), **extra) -> dict:
    stages = {name: ({"enabled": True, "status": status} if name in OPTIONAL
                     else {"status": status}) for name, status in STATUSES.items()}
    return {
        "backend": "jira",
        "tags": list(tags),
        "jira": {"site": site, "project": jira_project,
                 "credentials": {"email-env": EMAIL_ENV, "token-env": TOKEN_ENV},
                 "fields": {"project": "TCW Project", "item": "TCW Item",
                            "effort": "Effort", "complexity": "Complexity"},
                 **extra},
        "stages": stages,
    }


@dataclass
class JiraProject:
    root: Path
    id: str
    fake: FakeJira
    jira_project: str = "TCW"

    @property
    def work(self) -> Path:
        return self.root / "docs" / "work"

    def backend(self, **kw):
        return open_backend(self.root, **kw)

    def item(self, summary: str = "A ticket", words: str = "x", *,
             status: str = "Triage", folder: bool = True, project_id: str | None = None,
             item: str | None = None, **values):
        """A ticket carrying this project's TCW Project and TCW Item, and its
        folder here. Returns `(key, folder)`."""
        ticket = self.fake.ticket(summary, project=self.jira_project, status=status,
                                  **values)
        name = f"{ticket.key}-{words}"
        ticket.custom[FIELDS["TCW Project"]] = project_id or self.id
        ticket.custom[FIELDS["TCW Item"]] = item or f"{self.id}/{name}"
        if folder:
            path = self.work / name
            path.mkdir(parents=True)
            (path / "item.yaml").write_text(
                yaml.safe_dump({"ticket": f"{self.fake.site}/browse/{ticket.key}"}))
        return ticket.key, name


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv(EMAIL_ENV, "dev@example.test")
    monkeypatch.setenv(TOKEN_ENV, "token")
    fake = FakeJira().install(monkeypatch)
    fake.account("dev@example.test", ME, "Dev Eloper")
    return fake


@pytest.fixture
def jira_project(tmp_path, fake) -> JiraProject:
    root = make_project(tmp_path, "tcw", config=jira_config())
    return JiraProject(root, "tcw", fake)


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(["work", *argv])
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run
