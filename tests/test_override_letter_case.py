"""On a disk that ignores letter case, a path spelled in other letter case is the
same folder to the worktree mapping (spec:
2026-09-29-accept-a-project-override-spelled-in-other-letter-case-from-a-linked-worktree)."""

import tempfile
from pathlib import Path

import pytest

from tcw.store.fs import anchor_configured_path, worktree_node_root
from test_override_in_linked_worktree import linked
from test_worktree_sibling_nodes import validate, workspace  # noqa: F401


def _case_insensitive() -> bool:
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "Probe"
        probe.mkdir()
        return (Path(d) / "pROBE").exists()


pytestmark = pytest.mark.skipif(not _case_insensitive(),
                                reason="the disk distinguishes letter case")


def _upper_app(path: Path, app: Path) -> Path:
    """`path` with the `app` folder's own name upper-cased."""
    return app.parent / app.name.upper() / path.relative_to(app)


def _clean(done) -> str:
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "duplicate" not in out and "nonreciprocal" not in out, out
    return out


def test_an_override_in_other_letter_case_works_from_the_worktree(workspace, monkeypatch):  # noqa: F811
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(app / "pkg-b", app)))
    out = _clean(validate(wt / "pkg-a"))
    assert "warning:" in out and "TCW_PROJECT_PKG_B" in out, out


def test_an_override_upper_cased_throughout_works_from_the_worktree(workspace, monkeypatch):  # noqa: F811
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(app / "pkg-b").upper())
    _clean(validate(wt / "pkg-a"))


def test_an_override_in_other_letter_case_from_the_primary_checkout(workspace, monkeypatch):  # noqa: F811
    app, _wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(app / "pkg-b", app)))
    out = _clean(validate(app / "pkg-a"))
    assert "warning:" not in out, out


def test_a_store_path_escaping_the_worktree_is_anchored_in_any_letter_case(workspace):  # noqa: F811
    app, wt = linked(workspace)
    escaping = Path("../../../elsewhere")
    as_git = anchor_configured_path(wt / "pkg-a", escaping)
    as_typed = anchor_configured_path(_upper_app(wt / "pkg-a", app), escaping)
    assert as_git.samefile(app / "pkg-a")
    assert as_typed.samefile(as_git), (as_typed, as_git)


def test_the_worktree_node_root_is_found_in_any_letter_case(workspace):  # noqa: F811
    app, _wt = linked(workspace)
    typed = _upper_app(app / "pkg-a", app)
    found = worktree_node_root(typed, ".worktrees/x")
    expected = worktree_node_root(app / "pkg-a", ".worktrees/x")
    assert found is not None and expected is not None
    assert str(found).lower() == str(expected).lower(), (found, expected)



def test_an_override_naming_the_worktree_copy_in_other_letter_case(workspace, monkeypatch):  # noqa: F811
    """The override names this worktree's own copy of a package, spelled
    differently. Its `..` stays inside the worktree, so this guards the
    mapping, not Rule 1 — it passes on the code before this change too."""
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(wt / "pkg-b", app)))
    out = _clean(validate(wt / "pkg-a"))
    assert "warning:" not in out, out


def test_a_worktree_root_override_in_other_letter_case_reaches_its_parent(workspace, monkeypatch):  # noqa: F811
    """Rule 1: the worktree's own root, named in other letter case; its parent
    locator `..` leaves the worktree and must be re-anchored under the primary
    checkout. Before the change the parent silently dropped out of the graph."""
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_APP_REPO", str(_upper_app(wt, app)))
    out = _clean(validate(wt / "pkg-a"))
    assert "not reachable" not in out, out


def test_completing_an_item_of_a_project_reached_in_other_letter_case(workspace, monkeypatch):  # noqa: F811
    """`complete`'s guard against running inside the item's own worktree finds
    the node's place under the checkout by folder identity too: the override
    names this worktree's `pkg-b` in other letter case, and the item has a
    worktree of its own."""
    import subprocess
    import sys

    from tcw.store.fs import init
    _app, wt = linked(workspace)
    init(["work"], wt / "pkg-a", "pkg-a")
    init(["work"], wt / "pkg-b", "pkg-b")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "board"], check=True)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(wt / "pkg-b", _app)))

    def tcw(*args):
        return subprocess.run([sys.executable, "-m", "tcw.cli", "work", *args],
                              cwd=wt / "pkg-a", capture_output=True, text=True, timeout=120)

    made = subprocess.run([sys.executable, "-m", "tcw.cli", "work", "new", "Thing"],
                          cwd=wt / "pkg-b", capture_output=True, text=True, timeout=120)
    assert made.returncode == 0, made.stdout + made.stderr
    slug = made.stdout.strip().splitlines()[-1]
    started = tcw("start", f"pkg-b/{slug}", "--worktree")
    assert started.returncode == 0, started.stdout + started.stderr
    done = tcw("complete", f"pkg-b/{slug}", "--resolution", "done", "--confirm", "--force")
    assert "is not in the subpath" not in done.stderr, done.stderr
    assert done.returncode == 0, done.stdout + done.stderr
