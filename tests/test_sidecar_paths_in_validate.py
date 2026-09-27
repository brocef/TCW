"""`tcw validate` reports a capabilities.yaml path that cannot be right while
the item is still being worked, never on a finished one
(spec: 2026-09-09-resolve-capabilities-yaml-sidecar-paths-while-an-item-is-still-being-worked)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init
from tcw.validate import validate


@pytest.fixture
def root(tmp_path, monkeypatch, capsys) -> Path:
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root, "node")
    monkeypatch.chdir(root)
    assert main(["capabilities", "add", "auth/login", "Log in"]) == 0
    assert main(["capabilities", "add", "auth/logout", "Log out"]) == 0
    capsys.readouterr()
    return root


def item(root: Path, status: str, sidecar: str) -> tuple[str, str]:
    st = FsWorkStore.open(root)
    slug = st.create("Item", created="2026-01-01").slug
    st.write_sidecar(slug, "capabilities.yaml", sidecar)
    if status in ("active", "review", "completed"):
        st.start(slug, owner="me", force=True)
    if status in ("review", "completed"):
        st.submit(slug)
    if status == "completed":
        st.complete(slug, "done", [], force=True)
    where = str((st.path(slug) / "capabilities.yaml").relative_to(root)) if st.path(slug) else ""
    return slug, where


def sidecar_problems(root: Path) -> list[str]:
    return [p for p in validate(root) if "capabilities.yaml" in p]


def test_an_unresolved_new_path_in_active_work_is_reported(root):
    _, where = item(root, "active", "new:\n  - auth/login\n  - shared/x\n")
    assert sidecar_problems(root) == [
        f"{where}:3: shared/x: declared (new) but does not resolve"]


@pytest.mark.parametrize("status", ["active", "review"])
def test_a_bad_changed_path_is_reported_while_worked(root, status):
    _, where = item(root, status, "changed:\n  - shared/x\n")
    assert sidecar_problems(root) == [
        f"{where}:2: shared/x: declared (changed) but does not resolve"]


def test_backlog_reports_changed_but_not_new(root):
    _, where = item(root, "backlog", "new:\n  - shared/y\nchanged:\n  - shared/x\n")
    assert sidecar_problems(root) == [
        f"{where}:4: shared/x: declared (changed) but does not resolve"]


def test_completion_only_states_are_not_reported_mid_work(root):
    # auth/login is Missing (new, not yet flipped); auth/logout still resolves.
    item(root, "active", "new:\n  - auth/login\nremoved:\n  - auth/logout\n")
    assert sidecar_problems(root) == []


def test_a_completed_item_is_never_checked(root):
    item(root, "completed", "changed:\n  - shared/x\n")
    assert sidecar_problems(root) == []


def test_an_unreadable_sidecar_is_reported(root):
    slug, _ = item(root, "active", "new:\n  - auth/login\n")
    st = FsWorkStore.open(root)
    (st.path(slug) / "capabilities.yaml").write_text("new: [unclosed\n")
    assert any("capabilities.yaml" in p for p in validate(root)), validate(root)
