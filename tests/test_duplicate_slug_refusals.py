"""A slug two folders hold is refused by every verb, naming both folders and
`tcw validate` — never a traceback — and the board still prints (spec:
2026-09-30-refuse-instead-of-crashing-when-a-slug-is-held-by-two-folders)."""

import shutil
import subprocess

import pytest

from test_cross_node_blocker_cycles import new, node, store, tcw

OLD = "slug resolves to"                   # the message that named no folder


@pytest.fixture
def project(tmp_path):
    root = node(tmp_path / "p", "p")
    st = store(tmp_path, "p")
    twice, other = new(st, "Twice"), new(st, "Other")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    work = root / "docs/work"
    (work / "active").mkdir(exist_ok=True)
    shutil.copytree(work / "backlog" / twice, work / "active" / twice)
    return root, twice, other


def refused(out):
    assert out.returncode == 1, (out.stdout, out.stderr)
    assert "Traceback" not in out.stderr, out.stderr


def test_the_board_still_prints(project):
    root, twice, other = project
    out = tcw(root, "list")
    assert out.returncode == 0, out.stderr
    assert "Traceback" not in out.stderr, out.stderr
    rows = out.stdout.splitlines()
    assert any(r.startswith(f"{other} | backlog |") for r in rows), out.stdout
    marked = [r for r in rows if r.startswith(twice)]
    assert marked and all("held by 2 folders" in r for r in marked), out.stdout


@pytest.mark.parametrize("verb", ["start", "submit"])
def test_moves_refuse_without_a_traceback(project, verb):
    root, twice, _ = project
    out = tcw(root, verb, twice)
    refused(out)
    assert "tcw validate" in out.stderr, out.stderr


def test_the_refusal_names_both_folders(project):
    root, twice, _ = project
    out = tcw(root, "show", twice)
    refused(out)
    assert f"docs/work/active/{twice}" in out.stderr, out.stderr
    assert f"docs/work/backlog/{twice}" in out.stderr, out.stderr
    assert "tcw validate" in out.stderr, out.stderr
    assert OLD not in out.stderr, out.stderr
    # Removing a copy before merging in what only it holds would lose files.
    assert "merge any files it lacks" in out.stderr, out.stderr


def test_a_blocker_on_the_duplicate_points_at_validate(project):
    root, twice, other = project
    out = tcw(root, "edit", other, "--blocked-by", twice)
    refused(out)
    assert "tcw validate" in out.stderr, out.stderr


def test_validate_still_reports_it(project):
    root, twice, _ = project
    out = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert out.returncode == 1
    assert f"{twice}: held by 2 folders" in out.stderr, out.stderr


@pytest.fixture
def blocked_by_the_duplicate(tmp_path):
    """`waiting` is blocked by `twice`, then `twice`'s folder is copied."""
    root = node(tmp_path / "p", "p")
    st = store(tmp_path, "p")
    twice, waiting, other = new(st, "Twice"), new(st, "Waiting"), new(st, "Other")
    st.add_blocker(waiting, twice)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    work = root / "docs/work"
    (work / "active").mkdir(exist_ok=True)
    shutil.copytree(work / "backlog" / twice, work / "active" / twice)
    return root, twice, waiting, other


def test_an_item_blocked_by_the_duplicate_still_prints(blocked_by_the_duplicate):
    root, twice, waiting, other = blocked_by_the_duplicate
    out = tcw(root, "list")
    assert out.returncode == 0, out.stderr
    assert "Traceback" not in out.stderr, out.stderr
    rows = out.stdout.splitlines()
    row = next((r for r in rows if r.startswith(f"{waiting} |")), None)
    assert row is not None and f"blocked-by: {twice}" in row, out.stdout
    assert any(r.startswith(f"{other} |") for r in rows), out.stdout


def test_a_duplicated_epic_does_not_take_the_descendant_board_down(tmp_path):
    root = node(tmp_path / "p", "p")
    st = store(tmp_path, "p")
    epic, child = new(st, "Epic"), new(st, "Child")
    assert tcw(root, "edit", epic, "--type", "epic").returncode == 0
    assert tcw(root, "edit", child, "--initiative", epic).returncode == 0
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    work = root / "docs/work"
    (work / "active").mkdir(exist_ok=True)
    shutil.copytree(work / "backlog" / epic, work / "active" / epic)
    for args in (["list"], ["list", "--include-descendants"]):
        out = tcw(root, *args)
        assert out.returncode == 0, (args, out.stderr)
        assert "Traceback" not in out.stderr, out.stderr
        assert child in out.stdout, out.stdout


def test_a_blocker_held_twice_says_so(blocked_by_the_duplicate):
    root, twice, waiting, _ = blocked_by_the_duplicate
    row = next(r for r in tcw(root, "list").stdout.splitlines()
               if r.startswith(f"{waiting} |"))
    assert f"{twice} (held by more than one folder)" in row, row
    out = tcw(root, "start", waiting)
    assert out.returncode == 1 and f"{twice} (held by more than one folder)" in out.stderr, out.stderr


def test_a_cycle_through_the_duplicate_points_at_validate(blocked_by_the_duplicate):
    """Checking `other` blocked by `waiting` for a cycle walks through `twice`,
    which cannot be read while two folders hold it."""
    root, twice, waiting, other = blocked_by_the_duplicate
    out = tcw(root, "edit", other, "--blocked-by", waiting)
    refused(out)
    assert twice in out.stderr, out.stderr
    assert "merge any files it lacks" in out.stderr, out.stderr
    assert "`tcw validate` names both folders" in out.stderr, out.stderr
