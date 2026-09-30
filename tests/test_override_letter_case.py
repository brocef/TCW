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


@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_an_override_in_other_letter_case_works_from_the_worktree(workspace, monkeypatch):  # noqa: F811
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(app / "pkg-b", app)))
    out = _clean(validate(wt / "pkg-a"))
    assert "warning:" in out and "TCW_PROJECT_PKG_B" in out, out


@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_an_override_upper_cased_throughout_works_from_the_worktree(workspace, monkeypatch):  # noqa: F811
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(app / "pkg-b").upper())
    _clean(validate(wt / "pkg-a"))


def test_an_override_in_other_letter_case_from_the_primary_checkout(workspace, monkeypatch):  # noqa: F811
    app, _wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(_upper_app(app / "pkg-b", app)))
    out = _clean(validate(app / "pkg-a"))
    assert "warning:" not in out, out


@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_a_store_path_escaping_the_worktree_is_anchored_in_any_letter_case(workspace):  # noqa: F811
    app, wt = linked(workspace)
    escaping = Path("../../../elsewhere")
    as_git = anchor_configured_path(wt / "pkg-a", escaping)
    as_typed = anchor_configured_path(_upper_app(wt / "pkg-a", app), escaping)
    assert as_git.samefile(app / "pkg-a")
    assert as_typed.samefile(as_git), (as_typed, as_git)


@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_the_worktree_node_root_is_found_in_any_letter_case(workspace):  # noqa: F811
    app, _wt = linked(workspace)
    typed = _upper_app(app / "pkg-a", app)
    found = worktree_node_root(typed, ".worktrees/x")
    expected = worktree_node_root(app / "pkg-a", ".worktrees/x")
    assert found is not None and expected is not None
    assert str(found).lower() == str(expected).lower(), (found, expected)
