"""`tcw validate` warns when an override, set once for the machine, names the
primary checkout's copy of a project while running in a linked worktree (spec:
2026-09-29-warn-when-a-project-override-names-the-primary-checkout-s-copy-from-a-linked-worktree)."""

from test_worktree_sibling_nodes import git, validate, workspace  # noqa: F401
from tests.projectfiles import config_file

# Each test runs in `app-repo`, the parent of `pkg-b`, which looks `pkg-b` up:
# a sibling is never looked up from `pkg-a` (TCW-108 Design 3.1).


def linked(workspace):  # noqa: F811
    app = workspace / "app"
    git(app, "worktree", "add", "-q", ".worktrees/feature", "-b", "feature")
    return app, app / ".worktrees" / "feature"


def test_an_override_naming_the_primary_copy_is_warned_about(workspace, monkeypatch):  # noqa: F811
    app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(app / "pkg-b"))
    done = validate(wt)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "warning:" in out and "TCW_PROJECT_PKG_B" in out, out
    assert str(wt / "pkg-b") in out, out


def test_no_warning_from_the_primary_checkout(workspace, monkeypatch):  # noqa: F811
    app, _wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(app / "pkg-b"))
    done = validate(app)
    assert done.returncode == 0 and "warning:" not in done.stdout + done.stderr


def test_no_warning_for_the_worktree_s_own_copy(workspace, monkeypatch):  # noqa: F811
    _app, wt = linked(workspace)
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(wt / "pkg-b"))
    done = validate(wt)
    assert done.returncode == 0 and "warning:" not in done.stdout + done.stderr


def test_no_warning_when_the_copy_holds_another_project(workspace, monkeypatch):  # noqa: F811
    """The branch renamed the node: the copy is not the same project."""
    app, wt = linked(workspace)
    cfg = config_file(wt / "pkg-b")
    cfg.write_text(cfg.read_text().replace("id: pkg-b", "id: pkg-z"))
    monkeypatch.setenv("TCW_PROJECT_PKG_B", str(app / "pkg-b"))
    done = validate(wt)
    # Run in `app-repo`, its manifest's entry for `pkg-b` is reported as
    # overridden (TCW-107 Design 5.1); the override itself is not warned about.
    assert done.returncode == 0 and "primary checkout's copy" not in \
        done.stdout + done.stderr
