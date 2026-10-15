"""The Jira browser fixture's launcher, run as the browser tests run it
(TCW-77 criterion 11's pytest case).

The launcher is started as its own process on a free port, as
`web/e2e/jira.spec.ts` starts it, and asked over HTTP.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.serve.jira_launcher import LOG, MARKER
from tests.work.jira.conftest import EMAIL_ENV, TOKEN_ENV

REPO = Path(__file__).resolve().parents[2]


class Launched:
    def __init__(self, folder: Path, credentials: bool):
        env = {**os.environ, "HOME": str(folder / "home"),
               "XDG_CONFIG_HOME": str(folder / "config")}
        env.pop(EMAIL_ENV, None)
        env.pop(TOKEN_ENV, None)
        if credentials:
            env[EMAIL_ENV], env[TOKEN_ENV] = "dev@example.test", "token"
        self.folder = folder
        self.process = subprocess.Popen(
            [sys.executable, "-m", "tests.serve.jira_launcher", str(folder)],
            cwd=REPO, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.url = self.process.stdout.readline().strip()
        if not self.url:
            self.stop()
            pytest.fail(f"the launcher did not start: {self.process.stderr.read()}")

    def ask(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.url.rstrip("/") + path, data=data, method=method,
            headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(request, timeout=30) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def requests(self) -> list[str]:
        log = self.folder / LOG
        return log.read_text().splitlines() if log.exists() else []

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait(timeout=15)


@pytest.fixture
def launch(tmp_path):
    started: list[Launched] = []

    def start(credentials: bool) -> Launched:
        started.append(Launched(tmp_path / "fixture", credentials))
        return started[-1]

    yield start
    for one in started:
        one.stop()


def _spec_folder(launched: Launched) -> str:
    work = launched.folder / "project" / "docs" / "work"
    return next(p.name for p in work.iterdir() if (p / "spec" / "spec.md").is_file())


def test_without_credentials_the_board_falls_back_and_files_stay_editable(launch):
    launched = launch(credentials=False)
    status, board = launched.ask("GET", "/api/work")
    assert status == 200
    assert board["fallback"] is True
    assert EMAIL_ENV in board["unavailable"]
    folder = _spec_folder(launched)
    assert {row["path"].rsplit("/", 1)[-1] for row in board["items"]} >= {folder}

    path = f"/api/work/{folder}/files/spec/spec.md"
    status, read = launched.ask("GET", path)
    assert status == 200
    status, saved = launched.ask("PUT", path, {"content": "# Spec\n\nEdited.\n",
                                               "revision": read["revision"]})
    assert status == 200, saved
    spec = launched.folder / "project" / "docs" / "work" / folder / "spec" / "spec.md"
    assert spec.read_text() == "# Spec\n\nEdited.\n"
    assert launched.requests() == []


def test_with_credentials_the_board_is_one_search_and_no_user_request(launch):
    launched = launch(credentials=True)
    status, board = launched.ask("GET", "/api/work")
    assert status == 200, board
    assert board["fallback"] is False
    assert len(board["items"]) == 2
    assert set(board["people"].values()) >= {"Ann Author", "Dev Eloper"}
    searches = [line for line in launched.requests() if "/search" in line]
    assert len(searches) == 1, launched.requests()
    assert not [line for line in launched.requests() if "/user" in line.split("?")[0]
                and "/search" not in line]


def test_the_marker_makes_every_request_unreachable(launch):
    launched = launch(credentials=True)
    (launched.folder / MARKER).touch()
    status, board = launched.ask("GET", "/api/work")
    assert status == 200
    assert board["fallback"] is True
    assert "could not reach" in board["unavailable"]
    assert launched.requests() == []
