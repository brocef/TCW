"""One item's damaged `state.yaml` or artifact never takes down the board, `show`
or the web detail, and a guarded save can replace a damaged file
(spec: 2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail)."""

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tcw.serve import TcwServer
from tcw.store.fs import FsWorkStore, _revision, init


@pytest.fixture
def node(tmp_path, monkeypatch):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root, "node")
    st = FsWorkStore.open(root)
    bad = st.create("Bad", created="2026-01-01").slug
    good = st.create("Good", created="2026-01-01").slug
    monkeypatch.chdir(root)
    return root, st.path(bad), bad, good


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    """In a child process, so a read that blocks fails the test instead of
    stalling the suite."""
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=root, capture_output=True, text=True, timeout=20)


def assert_board_whole(root: Path, bad: str, good: str) -> None:
    done = cli(root, "work", "list")
    assert done.returncode == 0, done.stderr
    assert "codec can't decode" not in done.stderr and "Traceback" not in done.stderr
    assert bad in done.stdout and good in done.stdout, done.stdout


class served:
    def __init__(self, root: Path):
        self.httpd = TcwServer(("127.0.0.1", 0), root)
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def get(self, path: str):
        with urlopen(f"{self.base}{path}") as res:
            return res.status, json.loads(res.read())

    def put(self, path: str, body: dict) -> int:
        req = Request(f"{self.base}{path}", data=json.dumps(body).encode(),
                      method="PUT", headers={"Content-Type": "application/json"})
        try:
            with urlopen(req) as res:
                return res.status
        except HTTPError as e:
            return e.code


def not_utf8(p: Path):
    if p.is_dir():
        shutil.rmtree(p)
    p.write_bytes(b"title: \xff\xfe\n")


def folder(p: Path):
    p.unlink()
    p.mkdir()


def pipe(p: Path):
    p.unlink()
    os.mkfifo(p)


# ── criterion 1: state.yaml ──────────────────────────────────────────────────

@pytest.mark.parametrize("damage", [not_utf8, folder, pipe], ids=["not-utf8", "folder", "pipe"])
def test_a_damaged_state_file_leaves_the_board_whole(node, damage):
    root, item, bad, good = node
    damage(item / "state.yaml")
    assert_board_whole(root, bad, good)


# ── criterion 2: the request text ────────────────────────────────────────────

@pytest.mark.parametrize("name", ["intake.md", "initial-request.md"])
def test_a_damaged_request_text_leaves_the_board_and_show_whole(node, name):
    root, item, bad, good = node
    (item / name).write_bytes(b"# hi \xff\n")
    assert_board_whole(root, bad, good)
    shown = cli(root, "work", "show", bad)
    assert shown.returncode == 0, shown.stderr
    assert "codec can't decode" not in shown.stderr


# ── criterion 3: the web detail ──────────────────────────────────────────────

@pytest.mark.parametrize("name", ["state.yaml", "spec.md"])
def test_the_web_detail_of_a_damaged_item_loads(node, name):
    root, item, bad, _good = node
    (item / name).write_bytes(b"x: \xff\xfe\n")
    with served(root) as web:
        status, _body = web.get(f"/api/work/{bad}")
    assert status == 200


# ── criterion 4: a guarded save may replace a damaged file ───────────────────

@pytest.mark.parametrize("kind,name", [("artifacts", "spec"), ("sidecars", "capabilities.yaml")])
def test_a_guarded_save_replaces_a_damaged_file(node, kind, name):
    root, item, bad, _good = node
    path = item / (f"{name}.md" if kind == "artifacts" else name)
    path.write_bytes(b"new: \xff\xfe\n")
    with served(root) as web:
        _status, detail = web.get(f"/api/work/{bad}")
        listed = detail["artifacts"] if kind == "artifacts" else detail["sidecars"]
        [entry] = [e for e in listed if e["name"] == name]
        assert web.put(f"/api/work/{bad}/{kind}/{name}",
                       {"content": "new: []\n", "revision": "0" * 16}) == 409
        assert web.put(f"/api/work/{bad}/{kind}/{name}",
                       {"content": "new: []\n", "revision": entry["revision"]}) == 200
    assert path.read_text(encoding="utf-8") == "new: []\n"


def test_opening_a_damaged_artifact_names_the_file(node):
    root, item, bad, _good = node
    (item / "spec.md").write_bytes(b"# Spec \xff\n")
    with served(root) as web:
        with pytest.raises(HTTPError) as refused:
            urlopen(f"{web.base}/api/work/{bad}/artifacts/spec")
    body = refused.value.read()
    assert refused.value.code == 400
    assert b"spec is not valid UTF-8" in body and b"position" not in body


# ── criterion 5: no existing revision changes ────────────────────────────────

def test_a_valid_crlf_file_keeps_its_revision_and_its_guarded_save(node):
    """The payload's revision comes from `read_artifact`, the guard's from its
    own re-read: both must still see a CRLF file the way they did before."""
    root, item, bad, _good = node
    spec = item / "spec.md"
    spec.write_bytes(b"# Spec\r\n\r\nline\r\n")
    with served(root) as web:
        _status, detail = web.get(f"/api/work/{bad}")
        [entry] = [e for e in detail["artifacts"] if e["name"] == "spec"]
        assert entry["revision"] == _revision(spec.read_text(encoding="utf-8"))
        assert web.put(f"/api/work/{bad}/artifacts/spec",
                       {"content": "# Spec\n", "revision": entry["revision"]}) == 200


# ── criterion 6: a folder moved mid-read is still noticed ────────────────────

def test_a_state_file_that_vanishes_mid_read_still_raises(node, monkeypatch):
    """`_item_from_dir` and the in-flight scan tell a folder moved by a claim
    from a damaged one by this exception; tolerance must not swallow it."""
    import tcw.store.fs as fs
    _root, item, _bad, _good = node

    def vanished(path, *args, **kwargs):
        raise FileNotFoundError(path)

    monkeypatch.setattr(fs, "load_yaml", vanished)
    with pytest.raises(FileNotFoundError):
        FsWorkStore._safe_yaml(item / "state.yaml")


# ── review fold-in: a damaged item is refused before anything moves ──────────

def git_commit(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "items"], check=True)


@pytest.mark.parametrize("damage", [not_utf8, folder, pipe], ids=["not-utf8", "folder", "pipe"])
def test_start_refuses_a_damaged_item_before_moving_it(node, damage):
    root, item, bad, _good = node
    git_commit(root)
    damage(item / "state.yaml")
    done = cli(root, "work", "start", bad, "--owner", "me")
    assert done.returncode == 1, done.stderr
    assert "state.yaml cannot be read" in done.stderr, done.stderr
    assert "codec can't decode" not in done.stderr
    assert item.is_dir() and item.parent.name == "backlog"
    st = FsWorkStore.open(root)
    assert not (st.root / ".claiming").exists() or not list((st.root / ".claiming").iterdir())


@pytest.mark.parametrize("to", ["submit", "complete"])
def test_a_transition_refuses_a_damaged_item_before_moving_it(node, to):
    root, _item, bad, _good = node
    git_commit(root)
    st = FsWorkStore.open(root)
    st.start(bad, owner="me")
    active = st.path(bad)
    not_utf8(active / "state.yaml")
    args = ["work", to, bad] + (["--resolution", "done", "--confirm", "--force"]
                                if to == "complete" else [])
    done = cli(root, *args)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "state.yaml cannot be read" in done.stderr, done.stderr
    assert active.is_dir() and active.parent.name == "active"


def test_two_differently_damaged_bodies_have_different_revisions(node):
    _root, item, bad, _good = node
    st = FsWorkStore.open(_root)
    (item / "intake.md").write_bytes(b"# hi \xff\n")
    first = st.get_detail(bad).core_revision
    (item / "intake.md").write_bytes(b"# hi \xfe\n")
    assert st.get_detail(bad).core_revision != first
