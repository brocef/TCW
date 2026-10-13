"""A store name is a name: never a pattern to git, never a path to `glob`
(spec: 2026-09-15-refuse-glob-and-path-characters-in-store-names)."""

import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from tcw.cli import main
from tcw.serve import TcwServer
from tcw.store.fs import init


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def root(tmp_path, monkeypatch, capsys) -> Path:
    root = tmp_path / "node"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    init(["work", "capabilities"], root, "node")
    monkeypatch.chdir(root)
    capsys.readouterr()
    return root


# ── criterion 1: a slug that is not one path segment ────────────────────────


def test_the_web_answers_404_for_an_encoded_slash(root):
    httpd = TcwServer(("127.0.0.1", 0), root)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with pytest.raises(HTTPError) as got:
            urlopen(f"http://127.0.0.1:{httpd.server_port}/api/work/%2Fetc%2Fpasswd")
        assert got.value.code == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


# ── criterion 2: a glob-named capability writes only itself ─────────────────
#
# Its staging half went with TCW-73, which stages nothing: what is left is that
# writing `a*` changes `a*` and never its neighbour.

def test_writing_a_glob_named_capability_leaves_its_neighbour_alone(root, capsys):
    assert main(["capabilities", "add", "a*", "Star"]) == 0
    assert main(["capabilities", "add", "abc", "Abc"]) == 0
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    neighbour = root / "docs" / "capabilities" / "abc" / "meta.yaml"
    neighbour.write_text(neighbour.read_text() + "# mine, not yet saved\n")
    assert main(["capabilities", "set", "a*", "--field", "Status=Partial"]) == 0
    assert git(root, "diff", "--cached", "--name-only") == ""
    assert sorted(git(root, "diff", "--name-only").split()) == [
        "docs/capabilities/a*/meta.yaml", "docs/capabilities/abc/meta.yaml"]
    assert neighbour.read_text().endswith("# mine, not yet saved\n")
