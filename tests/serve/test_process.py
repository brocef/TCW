"""`tcw serve` as a process: one Python process, no Node, stdout carrying the
URL alone, and the exit codes (TCW-77 criteria 1 and 2, the parts that need no
work route)."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tcw.errors import NO_PROJECT

REPO = Path(__file__).resolve().parents[2]
SERVE = REPO / "tcw" / "serve"
URL_LINE = re.compile(r"^http://127\.0\.0\.1:(\d+)/$")


def serve_modules() -> list[Path]:
    return sorted(SERVE.rglob("*.py"))


# -- criterion 1: what is gone, and what no module does ------------------------------------


def test_the_node_server_is_gone():
    assert not (SERVE / "dist" / "server.cjs").exists()
    assert not (SERVE / "runtime.py").exists()
    assert not (REPO / "web" / "server").exists()
    package = json.loads((REPO / "package.json").read_text())
    assert "fastify" not in package.get("dependencies", {})
    assert "fastify" not in package.get("devDependencies", {})


def test_no_serve_module_starts_a_process():
    assert serve_modules(), "tcw/serve/ holds no module: the scan would be vacuous"
    found = []
    for path in serve_modules():
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found += [(path.name, a.name) for a in node.names
                          if a.name.split(".")[0] == "subprocess"]
            elif isinstance(node, ast.ImportFrom) and node.module and \
                    node.module.split(".")[0] == "subprocess":
                found.append((path.name, node.module))
            elif isinstance(node, ast.Attribute) and node.attr in ("system", "popen") \
                    and isinstance(node.value, ast.Name) and node.value.id == "os":
                found.append((path.name, f"os.{node.attr}"))
    assert found == []


# -- the server started as a real child process --------------------------------------------


def _env(tmp_path: Path, path: str | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    if path is not None:
        env["PATH"] = path
    return env


def _launch(cwd: Path, tmp_path: Path, *args: str, path: str | None = None):
    return subprocess.Popen(
        [sys.executable, "-m", "tcw.cli", "serve", "--no-open", *args],
        cwd=cwd, env=_env(tmp_path, path), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _first_line(process) -> str:
    line = process.stdout.readline()
    assert line, process.stderr.read()
    return line


def _stop(process) -> tuple[int, str, str]:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        out, err = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
    return process.returncode, out, err


@pytest.fixture
def project(tmp_path):
    from tests.serve.conftest import fs_project
    return fs_project(tmp_path, user=None)


def _python_only_path(tmp_path: Path) -> str:
    """A PATH holding git and this Python, and no `node`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("git",):
        found = shutil.which(name)
        assert found
        (bin_dir / name).symlink_to(found)
    return str(bin_dir)


def test_stdout_is_the_url_alone_and_sigterm_exits_0(project, tmp_path):
    process = _launch(project, tmp_path, "--port", "0",
                      path=_python_only_path(tmp_path))
    try:
        line = _first_line(process)
        match = URL_LINE.match(line.rstrip("\n"))
        assert match, line
        with urllib.request.urlopen(line.strip()) as answer:
            page = answer.read().decode()
        assert answer.status == 200 and "<div id=\"root\"" in page
    finally:
        code, out, err = _stop(process)
    assert code == 0, err
    assert out == ""                       # nothing after the URL line
    assert err.strip().splitlines() == ["stopped"]
    assert "Serving TCW at" not in line + out + err   # the 2.x line it replaces


def test_no_child_process_after_start(project, tmp_path):
    process = _launch(project, tmp_path, "--port", "0")
    try:
        url = _first_line(process).strip()
        urllib.request.urlopen(url + "api/taxonomy").read()
        children = subprocess.run(["pgrep", "-P", str(process.pid)],
                                  capture_output=True, text=True)
        assert children.stdout.strip() == "", children.stdout
    finally:
        _stop(process)


def test_a_port_in_use_exits_1_naming_it(project, tmp_path):
    first = _launch(project, tmp_path, "--port", "0")
    try:
        port = URL_LINE.match(_first_line(first).strip()).group(1)
        second = _launch(project, tmp_path, "--port", port)
        out, err = second.communicate(timeout=30)
        assert second.returncode == 1, err
        assert out == ""
        assert port in err and err.startswith("tcw serve: ")
    finally:
        _stop(first)


def test_outside_a_project_exits_1_with_the_one_message(tmp_path):
    outside = tmp_path / "nowhere"
    outside.mkdir()
    process = _launch(outside, tmp_path, "--port", "0")
    out, err = process.communicate(timeout=30)
    assert process.returncode == 1
    assert out == ""
    assert NO_PROJECT in err
    assert "no tcw node here" not in err.lower()


def test_missing_client_assets_exit_1(project, tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.serve import server
    monkeypatch.setattr(server, "files", lambda _package: _Missing(tmp_path / "empty"))
    monkeypatch.chdir(project)
    code = main(["serve", "--no-open", "--port", "0"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert server.MISSING_ASSETS in captured.err


class _Missing:
    def __init__(self, path: Path):
        self.path = path

    def joinpath(self, *parts):
        return self.path.joinpath(*parts)


def test_the_url_is_flushed_before_serving(project, monkeypatch, capsys):
    """In-process: `serve` prints the URL and flushes it before it blocks, so
    a reader of a pipe sees it at once."""
    from tcw.serve import server
    seen = {}

    def forever(self, *args, **kwargs):
        seen["out"] = capsys.readouterr().out
        raise KeyboardInterrupt

    monkeypatch.setattr(server.TcwServer, "serve_forever", forever)
    assert server.serve(project, port=0, open_browser=False) == 0
    assert URL_LINE.match(seen["out"].rstrip("\n"))
    assert capsys.readouterr().err == "stopped\n"


def test_the_browser_opens_unless_no_open(project, monkeypatch):
    from tcw.serve import server
    opened = []
    monkeypatch.setattr(server.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(server.TcwServer, "serve_forever",
                        lambda self, *a, **k: (time.sleep(0.2), _raise())[1])
    server.serve(project, port=0, open_browser=True)
    assert len(opened) == 1 and URL_LINE.match(opened[0])


def _raise():
    raise KeyboardInterrupt


def test_only_loopback_can_be_bound(project):
    from tcw.serve.server import TcwServer
    with pytest.raises(ValueError):
        TcwServer(("0.0.0.0", 0), project)
