"""Suite-wide guards.

Nothing here shapes a test's subject; it only stops the suite from reaching out
of the process.
"""

import os
import subprocess

import pytest

# The two argv heads `_open_locator` can produce. Matching on these rather than
# replacing `Popen` wholesale is deliberate: `tcw.serve.subprocess` *is* the
# stdlib module, so a blanket stub also blocks the `git init` the node fixtures
# run.
_OPENERS = ("open", "xdg-open")

_real_popen = subprocess.Popen


@pytest.fixture(autouse=True)
def _no_desktop_opener(monkeypatch):
    """The desktop opener never runs during a test.

    `/api/work/<slug>/artifacts/<name>/open` exists to hand a file to the user's
    GUI editor, and `tcw/serve/__init__.py:90-97` reaches it through
    `subprocess.Popen([open|xdg-open, path])`, or `os.startfile` on Windows. A
    test that exercises the route and forgets to stub them launches the
    developer's editor for real, on a temp file, on every run — which is what
    `test_the_open_gate_agrees_with_what_the_payload_advertises` did with a
    `post-mortem.md`.

    Guarded here rather than in each test because the failure is silent: the
    test still passes, and the only symptom is a window opening on a machine
    nobody is watching. A test that *asserts* on the opener monkeypatches
    `Popen` itself and still wins, since its patch lands after this one.

    `monkeypatch.setattr` raises on a missing attribute, so renaming the
    browser call site fails here loudly instead of leaving an inert guard.

    **The browser half stops the launch but may not fail the test.**
    `tcw/serve/runtime.py` opens the browser from a daemon thread, and
    `pytest.fail` raised off the main thread surfaces as
    `PytestUnhandledThreadExceptionWarning` rather than a failure. Preventing
    the window is the point; treat a warning in the log as the signal.
    """
    def guarded(argv, *args, **kwargs):
        # basename, not argv[0]: the call site passes a bare command name today,
        # but resolving it through `shutil.which` would hand us an absolute path
        # and silently defeat the guard.
        if argv and os.path.basename(str(argv[0])) in _OPENERS:
            pytest.fail(f"test spawned the desktop opener: {argv}")
        return _real_popen(argv, *args, **kwargs)

    monkeypatch.setattr("tcw.serve.subprocess.Popen", guarded)
    monkeypatch.setattr("os.startfile", lambda path: pytest.fail(
        f"test spawned the desktop opener: {path}"), raising=False)
    monkeypatch.setattr("tcw.serve.runtime.webbrowser.open",
                        lambda url, **kw: pytest.fail(
                            f"test opened a browser: {url}"))


@pytest.fixture
def stub_desktop_opener(_no_desktop_opener, monkeypatch):
    """Let a test reach the opener's success path without launching anything.

    Returns the list of argv it would have spawned. Depends on
    `_no_desktop_opener` so this patch is applied *after* the guard and wins,
    and it delegates every non-opener argv to the real `Popen` — a blanket stub
    also breaks the `git` calls `FsWorkStore` makes, which is the trap this
    fixture exists to keep out of individual tests.
    """
    calls: list[list[str]] = []

    def recording(argv, *args, **kwargs):
        if argv and os.path.basename(str(argv[0])) in _OPENERS:
            calls.append(list(argv))
            return None
        return _real_popen(argv, *args, **kwargs)

    monkeypatch.setattr("tcw.serve.subprocess.Popen", recording)
    # `os.startfile` too, or this fixture only works on the POSIX branch:
    # `_open_locator` takes the `os.name == "nt"` path on Windows, where the
    # guard's `pytest.fail` would still fire and fail the very test that asked
    # to reach the success path.
    monkeypatch.setattr("os.startfile", lambda path: calls.append([str(path)]),
                        raising=False)
    return calls


# The four variables Git reads before it consults any config file. Set as
# environment rather than `git config --global`: config would also change how
# `tcw work start` resolves a claimant (it falls back to `user.email`/`user.name`
# via `git config --get`), so a global identity would silently satisfy a
# precondition some test means to exercise. The environment supplies a committer
# and nothing else.
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
