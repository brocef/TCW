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
