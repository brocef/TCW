"""Serve a Jira-mode fixture project against TCW-71's fake Jira (TCW-77
criterion 11).

    python -m tests.serve.jira_launcher <folder> [--port N]

builds a Jira-mode project in `<folder>/project` (TCW-71's test
configuration), seeds the fake with two tickets that have items here, with
assignees and comments, and one inbox ticket, installs the fake in place of
the Jira client's request function, and runs `tcw serve` on it. No socket to
Jira is opened, and `work.jira.site` stays a valid `https://` site.

While it runs:

- every request the fake answers is appended to `<folder>/requests.log` as
  one `METHOD path` line;
- while `<folder>/unreachable` exists, every request fails as unreachable.

The credential variables, `TCW_TEST_JIRA_EMAIL` and `TCW_TEST_JIRA_TOKEN`,
are read from the environment the launcher is started in and never set by
it, so a test can leave them unset. The browser tests (`web/e2e/jira.spec.ts`)
and `test_jira_launcher.py` start it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from tcw.serve.server import serve
from tcw.work.jira import client as jira
from tests.work.jira.conftest import JiraProject, jira_config
from tests.work.jira.fake import FakeJira, install_sites
from tests.work.projects import commit_all, make_project

#: The accounts the fixture knows, by email; the first is the user.
ACCOUNTS = {"dev@example.test": ("acct-dev", "Dev Eloper"),
            "ann@example.test": ("acct-ann", "Ann Author")}
USER_EMAIL = "dev@example.test"
LOG = "requests.log"
MARKER = "unreachable"


def _document(text: str) -> dict:
    """`text` as the one-paragraph document Jira keeps a comment as."""
    return {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def build(folder: Path) -> tuple[Path, FakeJira]:
    """The fixture project in `folder/project` and its seeded fake."""
    fake = FakeJira()
    for email, (account_id, name) in ACCOUNTS.items():
        fake.account(email, account_id, name)
    root = make_project(folder, "tcw", config=jira_config(), name="project")
    project = JiraProject(root, "tcw", fake)
    first, folder_a = project.item("Make the board load", "board",
                                   status="Specifying", assignee="acct-ann")
    project.item("Show a ticket's comments", "comments", status="In Progress",
                 assignee="acct-dev")
    ticket = fake.tickets[first]
    ticket.description = _document("Load the board with one search.")
    fake._comment(ticket, fake.accounts["ann@example.test"], _document("First comment."))
    fake._comment(ticket, fake.accounts[USER_EMAIL], _document("Second comment."))
    fake.ticket("Triage me", status="To Do")        # in the inbox: no TCW Item
    (root / "docs" / "work" / folder_a / "spec").mkdir()
    (root / "docs" / "work" / folder_a / "spec" / "spec.md").write_text(
        "# Spec\n\nThe board loads with one search.\n")
    commit_all(root)
    return root, fake


def install(folder: Path, fake: FakeJira) -> pytest.MonkeyPatch:
    """Put the fake in place of the client's request function, logging each
    request it answers and failing every one while the marker exists."""
    patch = pytest.MonkeyPatch()
    install_sites(patch, fake)
    answered = fake.answer
    log, marker = folder / LOG, folder / MARKER

    def answer(client, method, path, body):
        if marker.exists():
            raise jira.TrackerUnavailable(f"could not reach the tracker at {fake.site}")
        with log.open("a") as out:
            out.write(f"{method} {path}\n")
        return answered(client, method, path, body)

    patch.setattr(fake, "answer", answer)
    return patch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jira_launcher")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    folder = args.folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    root, fake = build(folder)
    patch = install(folder, fake)
    try:
        return serve(root, port=args.port, open_browser=False)
    finally:
        patch.undo()


if __name__ == "__main__":
    sys.exit(main())
