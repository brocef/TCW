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
from tcw.store.fs import FsWorkStore, git_commit_result, git_mv, git_stage, init


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

@pytest.mark.parametrize("slug", ["/etc/passwd", "", "a/b", ".."])
def test_a_path_shaped_slug_is_no_such_item(root, slug):
    st = FsWorkStore.open(root)
    assert st.get(slug) is None
    for call in (lambda: st.start(slug, owner="x"), lambda: st.submit(slug)):
        with pytest.raises(ValueError, match="no such work item"):
            call()


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


# ── criterion 2: a glob-named capability stages and commits only itself ─────

def test_writing_a_glob_named_capability_leaves_its_neighbour_alone(root, capsys):
    assert main(["capabilities", "add", "a*", "Star"]) == 0
    assert main(["capabilities", "add", "abc", "Abc"]) == 0
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    neighbour = root / "docs" / "capabilities" / "abc" / "meta.yaml"
    neighbour.write_text(neighbour.read_text() + "# mine, not yet saved\n")
    assert main(["capabilities", "set", "a*", "--field", "Status=Partial"]) == 0
    assert git(root, "diff", "--cached", "--name-only").split() == [
        "docs/capabilities/a*/meta.yaml"]
    assert "docs/capabilities/abc/meta.yaml" in git(root, "diff", "--name-only")


# ── criteria 3-4: the git helpers, directly ─────────────────────────────────

@pytest.fixture
def pair(root) -> tuple[Path, Path, Path]:
    for name in ("x[b]", "xb", "q?", "qz"):
        (root / "d" / name).mkdir(parents=True)
        (root / "d" / name / "f").write_text("1\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    return root, root / "d" / "x[b]", root / "d" / "xb"


def test_stage_and_commit_take_only_the_named_path(pair):
    root, glob_named, neighbour = pair
    for d in (glob_named, neighbour, root / "d" / "q?", root / "d" / "qz"):
        (d / "f").write_text("2\n")
    git_stage(root, glob_named / "f", root / "d" / "q?" / "f")
    assert sorted(git(root, "diff", "--cached", "--name-only").split()) == [
        "d/q?/f", "d/x[b]/f"]
    assert git_commit_result(root, "one", "d/x[b]", "d/q?") is None
    assert sorted(git(root, "show", "--name-only", "--format=", "HEAD").split()) == [
        "d/q?/f", "d/x[b]/f"]
    assert sorted(git(root, "diff", "--name-only").split()) == ["d/qz/f", "d/xb/f"]


def test_a_move_takes_only_the_named_folder(pair):
    root, glob_named, neighbour = pair
    (neighbour / "new").write_text("untracked\n")
    git_mv(root, glob_named, root / "d" / "moved")
    assert git(root, "diff", "--cached", "--name-status").split() == [
        "R100", "d/x[b]/f", "d/moved/f"]


@pytest.mark.parametrize("setting", ["1", "true"])
def test_an_inherited_literal_pathspecs_setting_still_writes(root, monkeypatch, setting):
    """Git exports GIT_LITERAL_PATHSPECS to hooks and aliases run under
    `git --literal-pathspecs`; with it on, git reads `:(literal)` as part of the
    file name, so the prefix must be left off."""
    monkeypatch.setenv("GIT_LITERAL_PATHSPECS", setting)
    assert main(["capabilities", "add", "a*", "Star"]) == 0
    assert main(["capabilities", "add", "abc", "Abc"]) == 0
    assert "docs/capabilities/a*/meta.yaml" in git(root, "diff", "--cached", "--name-only")
