"""Suite-wide guards.

Nothing here shapes a test's subject; it only stops the suite from reaching out
of the process.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Every `tcw` the suite starts as a process is this interpreter's.

    Tests run `subprocess.run(["tcw", ...])`, which takes the first `tcw` on
    `PATH`. That is often an installed release rather than the code under
    test, which then passes or fails for reasons that have nothing to do with
    the change. So the folder holding `sys.executable` goes first on `PATH`
    whenever it holds a `tcw` script: the one installed with this interpreter,
    from this checkout. Done here rather than in a fixture so it is in place
    before any fixture runs, session-scoped ones included; with no `tcw`
    beside the interpreter `PATH` is left as it is.
    """
    here = Path(sys.executable).parent
    if shutil.which("tcw", path=str(here)):
        os.environ["PATH"] = os.pathsep.join([str(here), os.environ.get("PATH", "")])


@pytest.fixture
def tmp_path(tmp_path):
    """A test's folder alone in the folder holding it.

    TCW looks for a related project in the folders next to a project's root
    (TCW-107 Design 2.4), so it lists the folder holding that root. pytest
    makes every test's folder inside one shared folder, so a fixture project
    made at `tmp_path` would be searched for among every other test's
    projects, and found there. This returns a new folder `w` inside the one
    pytest made for the test, so the folder holding a project made at
    `tmp_path` holds that project only. `tests/test_projectfiles_helper.py`
    goes red without it.
    """
    folder = tmp_path / "w"
    folder.mkdir()
    return folder


@pytest.fixture(autouse=True)
def _no_desktop_opener(monkeypatch):
    """No test opens a browser.

    `tcw/serve/server.py` opens the browser from a daemon thread, and
    `pytest.fail` raised off the main thread surfaces as
    `PytestUnhandledThreadExceptionWarning` rather than a failure. Preventing
    the window is the point; treat a warning in the log as the signal.
    `monkeypatch.setattr` raises on a missing attribute, so renaming the
    browser call site fails here loudly instead of leaving an inert guard.
    """
    monkeypatch.setattr("tcw.serve.server.webbrowser.open",
                        lambda url, **kw: pytest.fail(
                            f"test opened a browser: {url}"))


# The four variables Git reads before it consults any config file. Set as
# environment rather than `git config --global`: config would also change what
# any command reading `user.email`/`user.name` through `git config --get`
# answers, so a global identity would silently satisfy a precondition some test
# means to exercise. The environment supplies a committer and nothing else.
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "TCW Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "TCW Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch):
    """Every `git commit` the suite provokes has a committer.

    Most fixtures `git config` an identity into the repositories they build
    themselves, but that cannot cover the ones TCW *clones* — `tcw provision`
    checks a store out, and a clone inherits no local config from its source.
    Those commits fell back to the developer's global identity, which a bare CI
    runner does not have: `fatal: empty ident name (for <runner@...>) not
    allowed`, and thirteen `test_store_publication` failures that never
    reproduced on a workstation.

    Suite-wide for the same reason the opener guard is: the dependency is
    invisible until it runs somewhere unconfigured, so no individual test can be
    trusted to remember it.
    """
    for key, value in _GIT_IDENTITY.items():
        monkeypatch.setenv(key, value)


# Git's own background maintenance, switched off for the whole suite. Supplied
# through `GIT_CONFIG_*` rather than `git config --global`: the suite runs `git`
# both directly and through TCW, in repositories it creates *and* in ones
# `tcw provision` clones, and only the environment reaches all of them without a
# fixture having to remember.
_GIT_NO_MAINTENANCE = {
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "gc.auto",
    "GIT_CONFIG_VALUE_0": "0",
    "GIT_CONFIG_KEY_1": "maintenance.auto",
    "GIT_CONFIG_VALUE_1": "false",
}


@pytest.fixture(autouse=True)
def _no_git_background_maintenance(monkeypatch):
    """No repository the suite builds runs maintenance behind the test.

    **`git fetch` starts it**, not `git commit` — observable in `GIT_TRACE`:

        trace: run_command: git maintenance run --auto --no-quiet

    That subprocess writes `.git/maintenance.lock`, which then vanishes between
    the `scandir` and the `unlink` of `tmp_path`'s teardown, and the *test* is
    reported as an error after it has already passed:

        ERROR tests/test_non_git_writes.py::test_every_cli_write_refuses…
        FileNotFoundError: [Errno 2] No such file or directory: 'maintenance.lock'

    Nothing about that error involves the test that carries it — it is whichever
    one happened to be holding the temp directory when the race landed, which is
    why it moves around and why it appears on one Python version and not
    another. The suite only began fetching when `tcw provision` gained a store
    to clone, which is why this had never fired before.

    `maintenance.auto` is the key that matters; `gc.auto` covers the other
    background process for the same reason. Turning both off removes the second
    process rather than teaching the cleanup to tolerate it, because a cleanup
    that ignores a missing file would also ignore a real one.
    """
    for key, value in _GIT_NO_MAINTENANCE.items():
        monkeypatch.setenv(key, value)


@pytest.fixture(autouse=True)
def _no_project_overrides(monkeypatch):
    """No test sees a `TCW_PROJECT_*` variable from the developer's shell.

    `override_variable` maps a project id to `TCW_PROJECT_<ID>`, and the
    registry treats such a variable as the authoritative statement of where that
    project sits — above the declared locator. A suite that inherits one
    resolves a different graph than the one its fixture built, and the failure
    is arbitrary: it depends on which ids the shell happens to name.

    The acceptance criterion this exists for is "with no variable set, nothing
    changes". A process that cannot say whether a variable is set cannot assert
    it. So this is a correctness guard, not tidiness — the same register as the
    desktop-opener guard above.

    A test that *wants* an override sets it with `monkeypatch.setenv`, which
    lands after this fixture and wins.
    """
    for name in [k for k in os.environ if k.startswith("TCW_PROJECT_")]:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _cache_in_tmp(tmp_path, monkeypatch):
    """No test writes to the developer's real `~/.cache/tcw/stores`.

    Suite-wide, for the reason the guards above give: the dependency is
    invisible until a test happens to provision something, so no individual file
    can be trusted to remember it. This lived as a local fixture in
    `test_store_provisioning.py` and covered only that file — a test added to
    `test_validate.py` called `ensure_available()`, and four working copies
    landed in the developer's real cache before anyone noticed.

    `tmp_path / "cache"` specifically, because tests assert the negative —
    `not (tmp_path / "cache" / "tcw").exists()` is how "resolution must not even
    look in the cache" is stated — and those assertions are only worth something
    if this is the directory the code would have used.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


@pytest.fixture(autouse=True)
def _no_personal_config(tmp_path, monkeypatch):
    """No test reads the developer's own personal configuration (TCW-72 AC 19).

    `TCW_NO_PERSONAL_CONFIG=1` skips both personal files, and
    `XDG_CONFIG_HOME` points the user-wide file into the test's own folder, so
    a test that switches personal files back on (`monkeypatch.delenv`) still
    reads nothing from the real home folder. A test of the home-folder path
    sets `HOME` itself.
    """
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))


def pytest_collection_modifyitems(config, items):
    """Skip the 2.x work tests TCW-70 did not port (`tests/not_ported.py`)."""
    from tests.not_ported import NOT_PORTED, REASON
    for item in items:
        if item.nodeid in NOT_PORTED:
            item.add_marker(pytest.mark.skip(reason=REASON))
