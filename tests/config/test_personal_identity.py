"""Who is running the command: `list --mine` and `--assign-me` (TCW-72
Design 9; AC 9's delegation case, 13 and 14)."""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.work.model import Changes
from tcw.work.open import open_backend
from tests.config.conftest import tcw
from tests.work.memory_backend import MemoryBackend
from tests.work.projects import commit_all, connect, make_project

PACKAGE = Path(__file__).resolve().parents[2] / "tcw"


def project(personal) -> Path:
    (personal.root / "docs" / "work").mkdir(parents=True, exist_ok=True)
    return personal.root


def assignee(root: Path, slug: str) -> str | None:
    folder = slug.split("/", 1)[1]
    record = yaml.safe_load((root / "docs" / "work" / folder / "item.yaml").read_text())
    return record.get("assignee")


# -- filesystem mode -------------------------------------------------------------------


def test_mine_matches_user_name_exactly(personal):
    root = project(personal)
    personal.local({"user": {"name": "Brian"}})
    exact = tcw(root, "work", "new", "Exact", "--assignee", "Brian").out.strip()
    tcw(root, "work", "new", "Lower", "--assignee", "brian")
    listed = tcw(root, "work", "list", "--mine")
    assert (listed.code, listed.out) == (0, exact + "\n"), listed


def test_assign_me_writes_user_name(personal):
    root = project(personal)
    personal.user({"user": {"name": "Brian"}})
    made = tcw(root, "work", "new", "X", "--assign-me")
    assert made.code == 0, made
    assert assignee(root, made.out.strip()) == "Brian"


@pytest.mark.parametrize("argv", [
    ["list", "--mine", "--assignee", "x"],
    ["new", "X", "--assign-me", "--assignee", "x"],
])
def test_two_ways_of_saying_who_is_a_usage_error(personal, argv):
    root = project(personal)
    personal.local({"user": {"name": "Brian"}})
    result = tcw(root, "work", *argv)
    assert result.code == 2 and result.out == "", result


@pytest.fixture
def no_identity(personal, monkeypatch):
    """No `user.name`, but every 2.x source of one present."""
    root = project(personal)
    monkeypatch.setenv("TCW_WORK_OWNER", "Brian")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.name", "Brian"), ("user.email", "b@example.test")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    return root


def _says_how_to_fix_it(personal, err: str) -> None:
    for words in ("user.name", str(personal.user_file), "tcw-config.local.yaml",
                  "work.jira.credentials"):
        assert words in err, (words, err)


def test_no_identity_is_none_without_raising(no_identity):
    assert open_backend(no_identity).current_user() is None


def test_list_mine_without_an_identity(personal, no_identity):
    result = tcw(no_identity, "work", "list", "--mine")
    assert (result.code, result.out) == (1, ""), result
    assert result.err.startswith("tcw work list: no identity is configured: ")
    _says_how_to_fix_it(personal, result.err)


def test_assign_me_without_an_identity_creates_nothing(personal, no_identity):
    before = sorted((no_identity / "docs" / "work").rglob("*"))
    result = tcw(no_identity, "work", "new", "X", "--assign-me")
    assert (result.code, result.out) == (1, ""), result
    _says_how_to_fix_it(personal, result.err)
    assert sorted((no_identity / "docs" / "work").rglob("*")) == before


def test_edit_of_a_missing_item_says_it_is_missing_before_who(personal, no_identity):
    # Review finding C8: the item is read before the identity is asked for.
    result = tcw(no_identity, "work", "edit", "p/2026-01-01-nothing-here", "--assign-me")
    assert (result.code, result.out) == (4, ""), result
    assert "no identity" not in result.err


def test_a_project_usage_error_does_not_wait_for_piped_input(tmp_path):
    # Review finding C8: `--project` is checked before any wait for a pipe
    # that is open but silent.
    import os
    import time
    from tests.config.conftest import SOURCE
    root = make_project(tmp_path, "p")
    env = {**os.environ, "PYTHONPATH": SOURCE, "TCW_STDIN_TIMEOUT": "5"}
    started = time.monotonic()
    with subprocess.Popen([sys.executable, "-m", "tcw.cli", "work", "new", "X",
                           "--assign-me", "--project", "other"], cwd=root, env=env,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True) as child:
        # stdin stays open and silent until the command has exited.
        code = child.wait(timeout=30)
        elapsed = time.monotonic() - started
        out, err = child.stdout.read(), child.stderr.read()
        child.stdin.close()
    assert (code, out) == (2, ""), err
    assert "--assign-me cannot be used with --project" in err
    assert elapsed < 3, elapsed


# -- through the interface ---------------------------------------------------------------


class Recording(MemoryBackend):
    """The in-memory backend, remembering every query and every create."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queries = []
        self.created = []

    def list(self, query):
        self.queries.append(query)
        return super().list(query)

    def create(self, title, changes, **kwargs):
        self.created.append(changes)
        return super().create(title, changes, **kwargs)


@pytest.fixture
def recording(personal, monkeypatch, capsys):
    root = project(personal)
    backend = Recording(root / "docs" / "work", project="p", user="acct-1")
    monkeypatch.setattr("tcw.work.cli.open_backend", lambda *a, **k: backend)
    monkeypatch.chdir(root)

    def call(*argv: str):
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        try:
            code = main(["work", *argv])
        except SystemExit as stop:
            code = stop.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err
    call.backend = backend
    return call


def test_list_mine_asks_the_backend_and_prints_what_it_returns(recording):
    backend = recording.backend
    theirs = backend.create("Theirs", Changes(assignee="someone"),
                            stage="request", request=None)
    # The backend decides what matches: an item whose assignee is not the
    # identity, returned by the backend, is printed all the same.
    backend.list = lambda query: (backend.queries.append(query), [theirs])[1]
    code, out, _ = recording("list", "--mine")
    assert (code, out) == (0, f"{theirs.slug}\n")
    assert backend.queries[-1].assignee == "acct-1"


def test_assign_me_passes_the_identity_in_changes(recording):
    code, out, _ = recording("new", "X", "--assign-me")
    assert code == 0 and out.strip()
    assert recording.backend.created[-1].assignee == "acct-1"


def test_a_backend_with_no_identity(recording):
    recording.backend.user = None
    code, out, err = recording("list", "--mine")
    assert (code, out) == (1, "")
    assert err.startswith("tcw work list: no identity is configured: ")


# -- AC 9: identity stays in the acting project ---------------------------------------


def test_assign_me_with_another_project_is_a_usage_error(tmp_path, monkeypatch):
    parent = make_project(tmp_path, "parent")
    child = make_project(tmp_path, "child")
    connect(parent, child, "children")
    connect(child, parent, "parent")
    commit_all(parent)
    commit_all(child)
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    (parent / "tcw-config.local.yaml").write_text("user:\n  name: Brian\n")
    before = sorted((child / "docs" / "work").rglob("*"))
    result = tcw(parent, "work", "new", "--project", "child", "--assign-me", "x")
    assert (result.code, result.out) == (2, ""), result
    assert "child" in result.err
    assert sorted((child / "docs" / "work").rglob("*")) == before


# -- AC 14: no fallback left -------------------------------------------------------------


def test_nothing_under_tcw_names_the_2x_owner_variable():
    hits = [str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob("*.py")
            if "TCW_WORK_OWNER" in p.read_text(encoding="utf-8")]
    assert hits == []


GIT_IDENTITY = re.compile(r"""["']config["'][^)\]]*["']user\.(name|email)["']""")


def test_nothing_under_tcw_reads_the_version_control_identity():
    hits = [str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob("*.py")
            if GIT_IDENTITY.search(p.read_text(encoding="utf-8"))]
    assert hits == []


def test_the_identity_check_sees_a_reader_put_back():
    source = 'subprocess.run(["git", "config", "user.name"])'
    assert GIT_IDENTITY.search(source)
