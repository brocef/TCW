"""One lock on the work store for every writer (spec:
2026-09-29-hold-one-lock-on-the-work-store-for-every-transition-not-only-the-resolving-ones)."""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import tcw.store.fs as fs
from tcw.store.fs import FsWorkStore

from test_recursion import commit_all, mk_node

pytestmark = pytest.mark.skipif(fs.fcntl is None, reason="needs fcntl")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout


def store(tmp_path: Path) -> tuple[Path, FsWorkStore]:
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    return root, FsWorkStore.open(root)


def items(root: Path, st: FsWorkStore, n: int) -> list[str]:
    slugs = [st.create(f"Item {i}", created="2026-01-01").slug for i in range(n)]
    commit_all(root, "items")
    return slugs


HOLD = """
import sys, time
from pathlib import Path
from tcw.store.fs import FsWorkStore
st = FsWorkStore.open(Path(sys.argv[1]))
with st._store_lock():
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


def hold_in_another_process(root: Path, seconds: float, env: dict | None = None):
    proc = subprocess.Popen([sys.executable, "-c", HOLD, str(root), str(seconds)],
                            stdout=subprocess.PIPE, text=True, env=env)
    assert proc.stdout.readline().strip() == "held"
    return proc


# ── 1: racing transitions on different items ────────────────────────────────

RACE = """
import sys
from tcw.cli import main
sys.exit(main(["work", sys.argv[1], sys.argv[2]]))
"""


@pytest.mark.parametrize("verb", ["start", "submit"])
def test_two_processes_on_two_items_each_get_their_own_commit(tmp_path, verb):
    root, st = store(tmp_path)
    rounds = 20
    slugs = items(root, st, 2 * rounds)
    if verb == "submit":
        for s in slugs:
            st.start(s, owner="x")
    for i in range(rounds):
        pair = slugs[2 * i: 2 * i + 2]
        procs = [subprocess.Popen([sys.executable, "-c", RACE, verb, s], cwd=root,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True) for s in pair]
        for p in procs:
            _, err = p.communicate(timeout=120)
            assert p.returncode == 0, err
            assert "index.lock" not in err, err
        to = "active" if verb == "start" else "review"
        for s in pair:
            touched = git(root, "log", "-1", "--format=", "--name-only",
                          "--fixed-strings", "--grep", f"{s} → {to}")
            assert touched.strip(), f"no commit for {s}"
            assert all(f"/{s}/" in f"/{line}" or line.endswith(f"/{s}")
                       for line in touched.split()), touched
    assert git(root, "status", "--porcelain").strip() == ""


# ── 2, 3: where the lock lives, and what a waiter is told ───────────────────

def test_the_lock_is_in_the_git_folder_and_ignores_tmpdir(tmp_path, monkeypatch):
    root, st = store(tmp_path)
    common = Path(git(root, "rev-parse", "--path-format=absolute",
                      "--git-common-dir").strip())
    assert st._store_lock_path().parent == common
    env = {**os.environ, "TMPDIR": str(tmp_path / "elsewhere")}
    (tmp_path / "elsewhere").mkdir()
    proc = hold_in_another_process(root, 3, env)
    try:
        monkeypatch.setattr(FsWorkStore, "STORE_LOCK_TIMEOUT", 0.5)
        with pytest.raises(ValueError, match=f"process {proc.pid}") as info:
            with st._store_lock():
                pass
        assert "Nothing was changed" in str(info.value)
    finally:
        proc.wait()


def test_a_timed_out_transition_changes_nothing(tmp_path, monkeypatch, capsys):
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    head = git(root, "rev-parse", "HEAD")
    proc = hold_in_another_process(root, 3)
    try:
        monkeypatch.setattr(FsWorkStore, "STORE_LOCK_TIMEOUT", 0.5)
        with pytest.raises(ValueError, match="held the work store"):
            FsWorkStore.open(root).start(slug, owner="x")
    finally:
        proc.wait()
    assert FsWorkStore.open(root).get(slug).status == "backlog"
    assert git(root, "rev-parse", "HEAD") == head


# ── 4: reentrant in a thread, exclusive between threads ──────────────────────

def test_reentrant_in_one_thread_and_exclusive_across_threads(tmp_path, monkeypatch):
    root, st = store(tmp_path)
    monkeypatch.setattr(FsWorkStore, "STORE_LOCK_TIMEOUT", 0.5)
    other: list = []

    def contend():
        try:
            with st._store_lock():
                other.append("got it")
        except ValueError as e:
            other.append(e)

    with st._store_lock():
        with st._store_lock():                         # no wait, no timeout
            t = threading.Thread(target=contend)
            t.start()
            t.join()
    assert isinstance(other[0], ValueError), other
    t = threading.Thread(target=contend)
    t.start()
    t.join()
    assert other[1] == "got it"


# ── 5: the push is outside the lock ─────────────────────────────────────────

def test_the_push_after_a_transition_does_not_hold_the_lock(tmp_path, monkeypatch):
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    monkeypatch.setattr(FsWorkStore, "STORE_LOCK_TIMEOUT", 0.5)
    monkeypatch.setattr(FsWorkStore, "publishes", property(lambda self: True))
    seen: list = []

    def slow_publish(self):
        def other_session():
            try:
                with FsWorkStore.open(root)._store_lock():
                    seen.append("free")
            except ValueError as e:
                seen.append(e)
        t = threading.Thread(target=other_session)
        t.start()
        t.join()

    monkeypatch.setattr(FsWorkStore, "publish", slow_publish)
    monkeypatch.setattr(FsWorkStore, "_refresh_before_transition", lambda self: None)
    FsWorkStore.open(root).start(slug, owner="x")
    assert seen == ["free"], seen


# ── 6: another git process's index.lock ─────────────────────────────────────

def test_a_brief_foreign_index_lock_is_waited_out(tmp_path):
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    lock = root / ".git" / "index.lock"
    lock.write_text("")
    threading.Timer(0.5, lock.unlink).start()
    FsWorkStore.open(root).start(slug, owner="x")
    assert git(root, "status", "--porcelain").strip() == ""
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_a_stale_index_lock_is_named(tmp_path, monkeypatch):
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    monkeypatch.setattr(fs, "INDEX_LOCK_RETRY", 0.3)
    lock = root / ".git" / "index.lock"
    lock.write_text("")
    try:
        with pytest.raises(Exception) as info:
            FsWorkStore.open(root).start(slug, owner="x")
    finally:
        lock.unlink()
    text = str(info.value) + str(getattr(info.value, "stderr", ""))
    assert "index.lock" in text and "delete it by hand" in text, text


# ── review follow-ups ────────────────────────────────────────────────────────

def test_a_creation_kept_waiting_is_left_staged_not_reported_as_unchanged(
        tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root, st = store(tmp_path)
    monkeypatch.chdir(root)
    proc = hold_in_another_process(root, 3)
    try:
        monkeypatch.setattr(FsWorkStore, "STORE_LOCK_TIMEOUT", 0.5)
        assert main(["work", "new", "Made while waiting"]) == 0
    finally:
        proc.wait()
    out = capsys.readouterr()
    assert "left staged" in out.err and "Nothing was changed" not in out.err.split("left staged")[0]
    assert "made-while-waiting" in git(root, "diff", "--cached", "--name-only")


def test_a_stale_index_lock_is_named_on_the_terminal(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    monkeypatch.chdir(root)
    monkeypatch.setattr(fs, "INDEX_LOCK_RETRY", 0.3)
    lock = root / ".git" / "index.lock"
    lock.write_text("")
    try:
        main(["work", "start", slug])
    finally:
        lock.unlink()
    err = capsys.readouterr().err
    assert "index.lock" in err and "delete it by hand" in err, err


def test_two_stores_in_one_repository_share_the_lock(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    a, b = FsWorkStore.open(parent), FsWorkStore.open(child)
    same = git(parent, "rev-parse", "--absolute-git-dir") == git(child, "rev-parse", "--absolute-git-dir")
    assert (a._store_lock_path() == b._store_lock_path()) == same


def test_commit_claim_and_the_scans_are_not_abstract():
    from tcw.store.base import WorkStore
    assert "artifacts" in WorkStore.__abstractmethods__
    assert "commit_claim" not in WorkStore.__abstractmethods__
    assert "refresh_for_creation" not in WorkStore.__abstractmethods__


def test_a_lock_released_before_it_is_looked_for_is_still_retried(tmp_path, monkeypatch):
    """Found by hand: a plain `git commit` in another shell held `index.lock`
    and released it between the failure and the check, so nothing retried."""
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    real = fs._git
    failed = []

    def once(args, **kwargs):
        if "commit" in args and not failed:
            failed.append(True)
            return subprocess.CompletedProcess(args, 128, "", "fatal: Unable to create index.lock")
        return real(args, **kwargs)
    monkeypatch.setattr(fs, "_git", once)
    FsWorkStore.open(root).start(slug, owner="x")
    assert failed and git(root, "status", "--porcelain").strip() == ""


def test_a_refusing_hook_is_not_run_twice(tmp_path, monkeypatch):
    root, st = store(tmp_path)
    [slug] = items(root, st, 1)
    count = tmp_path / "count"
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho x >> {count}\nexit 1\n")
    hook.chmod(0o755)
    with pytest.raises(Exception):
        FsWorkStore.open(root).start(slug, owner="x")
    assert count.read_text().count("x") == 1
