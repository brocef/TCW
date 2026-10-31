"""What the viewer never does while it answers: start a process other than the
read-only git checks of the operations it calls, or move an item (TCW-77
criteria 1's run-time parts, and 5)."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from tests.processes import allowed_read_only_git, git_command
from tests.serve.conftest import Served, fs_project
from tests.serve.memory import RecordingBackend
from tests.serve.test_process import URL_LINE, _launch, _stop
from tests.serve.test_work_read import new
from tests.serve.test_work_write import family  # noqa: F401  (a fixture)
from tests.statefiles import ITEM_STATE

SERVE = Path(__file__).resolve().parents[2] / "tcw" / "serve"


def every_route(served, folder: str) -> list:
    """One valid request to every route, a create in the served project
    included."""
    calls = [
        ("GET", "/api/project", None), ("GET", "/api/work", None),
        ("GET", "/api/work?all=1&tag=ui", None), ("GET", f"/api/work/{folder}", None),
        ("PUT", f"/api/work/{folder}/files/spec/spec.md",
         {"content": "# Spec\n", "revision": None}),
        ("GET", f"/api/work/{folder}/files/spec/spec.md", None),
        ("POST", f"/api/work/{folder}/files", {"stage": "implement", "kind": "handoff"}),
        ("PUT", f"/api/work/{folder}/declaration",
         {"capabilities": {"new": ["x"]}, "revision": None}),
        ("GET", f"/api/work/{folder}/declaration", None),
        ("PATCH", f"/api/work/{folder}", {"changes": {"priority": "high"},
                                          "expected": {"priority": "medium"}}),
        ("POST", f"/api/work/{folder}/comments", {"text": "hi"}),
        ("POST", "/api/work", {"title": "Here"}),
        ("GET", "/api/tickets", None),
        ("GET", "/api/options/work?q=a", None),
        ("GET", "/api/taxonomy", None), ("GET", "/api/capabilities", None),
        ("POST", "/api/resolve", {"uris": [f"tcw://W/{folder}"]}),
        ("GET", "/", None), ("GET", "/work/x", None),
    ]
    answers = []
    for method, path, body in calls:
        answer = served.request(method, path) if body is None else \
            served.request(method, path, body)
        answers.append((method, path, answer.status, answer.body))
    return answers


def expected_failures(answers) -> list:
    """Every route answered as a valid request should, except the tickets
    route, which is a usage error in filesystem mode by design."""
    return [a for a in answers if a[2] >= 400 and a[1] != "/api/tickets"]


@pytest.fixture
def prepared(family, tcw):
    mine = new(tcw, family.p, "Mine")
    return family, mine


def _allowed(argv) -> bool:
    """`git rev-parse` (the shared rule, `tests/processes.py`), or
    `git --no-optional-locks status`, each allowed a `-C <folder>` before
    the command: the read-only checks the operations the viewer calls make.
    Anything else, `git add` and `git commit` included, is not."""
    if allowed_read_only_git(argv):
        return True
    command, options = git_command(argv)
    return command == "status" and "--no-optional-locks" in options


def test_the_git_rule():
    assert _allowed(["git", "-C", "/x", "rev-parse", "--show-toplevel"])
    assert _allowed(["git", "--no-optional-locks", "-C", "/x", "status", "--porcelain"])
    assert not _allowed(["git", "-C", "/x", "status"])
    for refused in (["git", "add", "-A"], ["git", "-C", "/x", "commit", "-m", "x"],
                    ["node", "x.js"], ["open", "x"], ["xdg-open", "x"]):
        assert not _allowed(refused), refused


def test_the_shared_read_only_git_rule():
    """The rule a move and `tcw -C` are held to (TCW-114 Design 4.6): only
    `git rev-parse`, with any options before it; never `status`."""
    assert allowed_read_only_git(["git", "-C", "/x", "rev-parse", "--show-toplevel"])
    assert allowed_read_only_git(["git", "rev-parse", "--git-common-dir"])
    for refused in (["git", "status"], ["git", "--no-optional-locks", "status"],
                    ["git", "-C", "/x", "add", "."], ["git", "commit"], ["ls"]):
        assert not allowed_read_only_git(refused), refused


def test_only_read_only_git_runs_while_answering(prepared, monkeypatch):
    family, mine = prepared
    started: list = []
    real = subprocess.Popen

    class Recording(real):
        def __init__(self, args, *rest, **kwargs):
            started.append(list(args) if not isinstance(args, str) else [args])
            super().__init__(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    answers = every_route(family.served, mine)
    monkeypatch.undo()
    assert expected_failures(answers) == []
    assert started, "no git check ran: the create route was not reached"
    assert [a for a in started if not _allowed(a)] == []


def test_the_child_process_starts_no_child(prepared, tmp_path):
    family, mine = prepared
    process = _launch(family.p, tmp_path, "--port", "0")
    try:
        port = int(URL_LINE.match(process.stdout.readline().strip()).group(1))
        children = subprocess.run(["pgrep", "-P", str(process.pid)],
                                  capture_output=True, text=True)
        assert children.stdout.strip() == ""
        answers = every_route(Served(family.p, None, port), mine)
        children = subprocess.run(["pgrep", "-P", str(process.pid)],
                                  capture_output=True, text=True)
        assert children.stdout.strip() == "", children.stdout
    finally:
        code, _, err = _stop(process)
    assert expected_failures(answers) == [], answers
    assert code == 0, err


# -- no lifecycle ----------------------------------------------------------------------------


def test_lifecycle_routes_do_not_exist(fs, tcw):
    folder = new(tcw, fs.root, "Thing")
    item = fs.root / "docs" / "work" / folder / ITEM_STATE
    before = item.read_text()
    for method, path in (("POST", f"/api/work/{folder}/actions/start"),
                         ("POST", f"/api/work/{folder}/actions/complete"),
                         ("POST", f"/api/work/{folder}/advance"),
                         ("DELETE", f"/api/work/{folder}")):
        answer = fs.request(method, path, {}) if method == "POST" else \
            fs.request(method, path)
        assert answer.status == 404, (method, path)
    assert item.read_text() == before


def test_no_route_moves_an_item(tmp_path, personal_on, serve_project, tcw):
    from tcw.serve.services import Services
    from tcw.work.open import work_path
    root = fs_project(tmp_path)
    backend = RecordingBackend(work_path(root), "p", external=frozenset(),
                               inbox_items=True)
    backend.seed("2026-10-01-thing", "Thing")
    served = serve_project(root, Services(open_backend=lambda _root: backend))
    for method, path, body in [
            ("GET", "/api/project", None), ("GET", "/api/work", None),
            ("GET", "/api/work/2026-10-01-thing", None),
            ("PATCH", "/api/work/2026-10-01-thing", {
                "changes": {"priority": "high"}, "expected": {"priority": "medium"}}),
            ("POST", "/api/work/2026-10-01-thing/comments", {"text": "x"}),
            ("POST", "/api/work", {"title": "New"}),
            ("PUT", "/api/work/2026-10-01-thing/files/spec/spec.md",
             {"content": "x", "revision": None})]:
        answer = served.request(method, path) if body is None else \
            served.request(method, path, body)
        assert answer.status < 400, (path, answer.body)
    assert backend.named("update") and backend.named("comment")
    assert backend.named("set_stage") == []


def test_no_serve_module_imports_the_lifecycle():
    found = []
    for path in sorted(SERVE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(), str(path))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if isinstance(node, ast.ImportFrom) and node.module == "tcw.work":
                names += [f"tcw.work.{a.name}" for a in node.names]
            found += [(path.name, n) for n in names if n == "tcw.work.advance"]
    assert found == []

