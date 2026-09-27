"""One item's unreadable `capabilities.yaml` never takes down the board, the
projection or the web detail, and still refuses completion
(spec: 2026-09-15-make-the-capability-gate-honor-a-configured-ledger)."""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from tcw.cli import main
from tcw.serve import TcwServer
from tcw.store.base import SidecarError, declared_capabilities, sidecar_value_problem
from tcw.store.fs import FsWorkStore, init

# Nine levels of ten aliases each: 10 lines, 10⁹ values once expanded.
ANCHORS = "\n".join(
    ["a0: &a0 [x, x, x, x, x, x, x, x, x, x]"]
    + [f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 10)}]" for i in range(1, 9)]
    + ["new: []"]) + "\n"


@pytest.fixture
def node(tmp_path, monkeypatch, capsys):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root, "node")
    st = FsWorkStore.open(root)
    bad = st.create("Bad", created="2026-01-01").slug
    st.create("Good", created="2026-01-01")
    monkeypatch.chdir(root)
    capsys.readouterr()
    return root, st.path(bad) / "capabilities.yaml", bad


def board(root: Path) -> str:
    """In a child process, so a read that blocks fails the test instead of
    stalling the suite."""
    done = subprocess.run([sys.executable, "-m", "tcw.cli", "work", "list"],
                          cwd=root, capture_output=True, text=True, timeout=20)
    assert done.returncode == 0, done.stderr
    return done.stdout


def projected(root: Path, slug: str):
    """`show --json` in a child process, so a hang fails the test instead of
    stalling the suite."""
    started = time.monotonic()
    done = subprocess.run([sys.executable, "-m", "tcw.cli", "work", "show", slug, "--json"],
                          cwd=root, capture_output=True, text=True, timeout=20)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["capabilities"], time.monotonic() - started


# ── criterion 1: a file that cannot be read ──────────────────────────────────

def _not_utf8(p: Path):
    p.write_bytes(b"new:\n  - \xff\xfe\n")


def _folder(p: Path):
    p.mkdir()


def _pipe(p: Path):
    os.mkfifo(p)


@pytest.mark.parametrize("make", [_not_utf8, _folder, _pipe], ids=["not-utf8", "folder", "pipe"])
def test_an_unreadable_sidecar_leaves_the_board_whole(node, make):
    root, sidecar, slug = node
    make(sidecar)
    out = board(root)
    assert "Bad" in out and "Good" in out
    value, _ = projected(root, slug)
    assert "_tcw_parse_error" in value


# ── criteria 2-3: expansion ──────────────────────────────────────────────────

def test_an_alias_bomb_is_refused_quickly(node):
    root, sidecar, slug = node
    sidecar.write_text(ANCHORS)
    value, took = projected(root, slug)
    assert "10000" in value["_tcw_parse_error"] and took < 10


def test_aliases_nested_past_the_depth_limit_are_refused(node):
    """Each line nests 40 deep, which loads; through the aliases the value is
    120 deep with a few hundred values, which the count alone would pass and a
    recursive walk would later crash on."""
    root, sidecar, slug = node
    lines = ["a0: &a0 " + "[" * 40 + "x" + "]" * 40]
    lines += [f"a{i}: &a{i} " + "[" * 40 + f"*a{i - 1}" + "]" * 40 for i in (1, 2)]
    sidecar.write_text("\n".join(lines) + "\nnew: []\n")
    value, _ = projected(root, slug)
    assert "deeper than 100" in value["_tcw_parse_error"]


def test_a_missing_sidecar_is_no_sidecar(node):
    root, _sidecar, slug = node
    assert FsWorkStore.open(root).get(slug).capabilities is None


def test_a_self_referencing_sidecar_is_counted_without_hanging():
    looped: dict = {}
    looped["b"] = looped
    assert sidecar_value_problem(looped) is None
    assert sidecar_value_problem({"new": [looped] * 3}) is None


def test_the_limit_is_on_values_counted_through_aliases():
    shared = ["x"] * 100            # 101 values each, the list included
    assert sidecar_value_problem({"new": [shared] * 98}) is None      # 9,901
    assert "10000" in sidecar_value_problem({"new": [shared] * 100})  # 10,103


# ── criterion 4: sound files read as before ──────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("new:\n  - auth/login\nchanged: []\n", {"new": ["auth/login"], "changed": []}),
    ("- auth/login\n", ["auth/login"]),
    ("new: &p [auth/login]\nchanged: *p\n", {"new": ["auth/login"], "changed": ["auth/login"]}),
    ("", {}),
])
def test_a_sound_sidecar_reads_as_before(node, text, expected):
    root, sidecar, slug = node
    sidecar.write_text(text)
    assert FsWorkStore.open(root).get(slug).capabilities == expected


def test_a_sidecar_over_the_byte_limit_is_refused(node):
    root, sidecar, slug = node
    sidecar.write_text("new:\n" + "".join(f"  - p/{i:08}\n" for i in range(70_000)))
    value = FsWorkStore.open(root).get(slug).capabilities
    assert "1000000 bytes" in value["_tcw_parse_error"]


# ── criterion 5: the gate still refuses ──────────────────────────────────────

def test_an_unreadable_sidecar_still_refuses_completion(node):
    from tcw.work.recursion import capability_gate
    root, sidecar, slug = node
    _not_utf8(sidecar)
    st = FsWorkStore.open(root)
    item = st.get(slug)
    with pytest.raises(SidecarError):
        declared_capabilities(item.capabilities)
    assert capability_gate(st, item) == [
        "capabilities.yaml is unreadable: capabilities.yaml is not valid UTF-8"]


# ── criterion 6: the web detail ──────────────────────────────────────────────

def test_the_web_detail_of_an_item_with_a_bad_sidecar_loads(node):
    root, sidecar, slug = node
    _not_utf8(sidecar)
    httpd = TcwServer(("127.0.0.1", 0), root)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    try:
        with urlopen(f"{base}/api/work/{slug}") as res:
            assert res.status == 200
        with pytest.raises(HTTPError) as refused:
            urlopen(f"{base}/api/work/{slug}/sidecars/capabilities.yaml")
        assert refused.value.code == 400
        assert b"capabilities.yaml is not valid UTF-8" in refused.value.read()
    finally:
        httpd.shutdown()
        httpd.server_close()


# ── found by the combined review with the validate sidecar check ────────────

@pytest.mark.parametrize("make", [_not_utf8, _folder, _pipe], ids=["not-utf8", "folder", "pipe"])
def test_validate_reports_an_unreadable_file_instead_of_crashing(node, make):
    """`tcw validate` scans every `.yaml` and `.md` in the store, and is a `pre`
    hook on `complete` in some projects: one bad file must be a problem line."""
    root, sidecar, _slug = node
    make(sidecar)
    done = subprocess.run([sys.executable, "-m", "tcw.cli", "validate", "--no-recurse"],
                          cwd=root, capture_output=True, text=True, timeout=20)
    assert done.returncode == 1 and "Traceback" not in done.stderr, done.stderr
    assert "capabilities.yaml: not " in done.stdout + done.stderr, done.stdout


def test_validate_reports_an_unreadable_markdown_file(node):
    root, sidecar, _slug = node
    (sidecar.parent / "notes.md").write_bytes(b"\xff\xfe\n")
    done = subprocess.run([sys.executable, "-m", "tcw.cli", "validate", "--no-recurse"],
                          cwd=root, capture_output=True, text=True, timeout=20)
    assert "notes.md: not valid UTF-8" in done.stdout + done.stderr, done.stderr
