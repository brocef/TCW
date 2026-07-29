"""`scripts/session_bootstrap.sh` — the SessionStart install reconcile.

Hermetic by construction: every run gets a PATH of `tmp_path/bin:/usr/bin:/bin`,
so the only `pipx`, `tcw`, and `python3` the script can find are stubs this file
wrote. **No test may invoke real pipx** — one that did would rebuild the
developer's own install.

The exception is `test_real_editable_checkout_is_left_alone`, which runs against
this repo with the real PATH on purpose: the guard it covers is the one whose
failure lands on the maintainer first.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "session_bootstrap.sh"

SYSTEM_PATH = "/usr/bin:/bin"


def _clone(tmp_path: Path, version: str = "9.9.9") -> Path:
    """A stand-in plugin clone root — only `tcw/__init__.py` matters."""
    root = tmp_path / "clone"
    (root / "tcw").mkdir(parents=True)
    (root / "tcw" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    return root


def _stub(bindir: Path, name: str, body: str) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    p = bindir / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(0o755)
    return p


def _recording_pipx(bindir: Path, log: Path, rc: int = 0, installs: Path | None = None) -> None:
    """A pipx that records its arguments instead of installing anything.

    On success it also drops a `tcw` stub, the way a real install would put the
    CLI on PATH — which is what lets the follow-up run reach the steady state.
    """
    body = f'printf "%s\\n" "$*" >> {log}\n'
    if installs is not None:
        body += f'printf "#!/bin/sh\\n" > {installs}\nchmod 755 {installs}\n'
    body += f"exit {rc}\n"
    _stub(bindir, "pipx", body)


def _run(root: Path, sentinel: Path, bindir: Path, path: str | None = None):
    env = {
        "PATH": path or f"{bindir}:{SYSTEM_PATH}",
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    return subprocess.run(
        [str(SCRIPT), str(root), str(sentinel)],
        capture_output=True, text=True, env=env, cwd=str(root.parent),
    )


def test_script_is_executable():
    assert os.access(SCRIPT, os.X_OK), "session_bootstrap.sh must be mode 755"


def test_steady_state_is_silent_and_never_calls_pipx(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "data" / "installed-version"
    sentinel.parent.mkdir()
    shutil.copy(root / "tcw" / "__init__.py", sentinel)
    bindir = tmp_path / "bin"
    _stub(bindir, "tcw", "exit 0\n")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "steady state must not invoke pipx"


def test_editable_install_is_left_alone(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"  # never written: nothing installed us
    bindir = tmp_path / "bin"
    _stub(bindir, "tcw", "exit 0\n")
    _stub(bindir, "python3", "exit 0\n")  # "yes, editable"
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "an editable install must never be force-installed over"
    assert not sentinel.exists()


def test_missing_pipx_is_silent_and_leaves_the_sentinel(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    sentinel.write_text('__version__ = "0.0.1"\n')  # stale: differs from the clone
    bindir = tmp_path / "bin"
    _stub(bindir, "tcw", "exit 0\n")
    _stub(bindir, "python3", "exit 1\n")  # not editable
    # no pipx stub — /usr/bin:/bin has none either

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert sentinel.read_text() == '__version__ = "0.0.1"\n'


def test_failed_install_prints_one_line_and_retries_next_time(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    sentinel.write_text('__version__ = "0.0.1"\n')
    bindir = tmp_path / "bin"
    _stub(bindir, "tcw", "exit 0\n")
    _stub(bindir, "python3", "exit 1\n")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log, rc=1)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0, "a failure must not surface as a hook error"
    assert r.stderr == "", "SessionStart shows the agent stdout, not stderr"
    lines = r.stdout.splitlines()
    assert len(lines) == 1 and "/tcw-doctor" in lines[0], r.stdout
    assert sentinel.read_text() == '__version__ = "0.0.1"\n', "a stale sentinel is what forces the retry"
    assert log.read_text().strip().endswith(str(root))


def test_successful_install_writes_the_sentinel_then_goes_quiet(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "data" / "installed-version"  # parent does not exist yet
    bindir = tmp_path / "bin"
    _stub(bindir, "python3", "exit 1\n")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log, installs=bindir / "tcw")

    first = _run(root, sentinel, bindir)

    assert first.returncode == 0
    assert first.stdout == ""
    assert log.read_text().strip() == f"install --force {root}"
    assert sentinel.read_bytes() == (root / "tcw" / "__init__.py").read_bytes()

    second = _run(root, sentinel, bindir)

    assert second.returncode == 0
    assert second.stdout == ""
    assert len(log.read_text().splitlines()) == 1, "the second run must take the silent path"


# --- the real thing ----------------------------------------------------------

_EDITABLE_PROBE = """
import json, sys
from importlib.metadata import distribution
raw = distribution("tcw").read_text("direct_url.json") or "{}"
sys.exit(0 if json.loads(raw).get("dir_info", {}).get("editable") else 1)
"""


def _this_machine_has_an_editable_tcw() -> bool:
    if shutil.which("tcw") is None:
        return False
    # From a neutral cwd: inside a TCW checkout the repo's own `tcw.egg-info`
    # would answer instead of the installed dist-info.
    return subprocess.run(
        [sys.executable, "-c", _EDITABLE_PROBE],
        cwd=tempfile.gettempdir(), capture_output=True,
    ).returncode == 0


@pytest.mark.skipif(
    not _this_machine_has_an_editable_tcw(),
    reason="no editable tcw install here — nothing for the guard to protect",
)
def test_real_editable_checkout_is_left_alone(tmp_path):
    """The fixture above proves the branch; this proves it fires for real.

    Runs with the real PATH (a stub pipx prepended, so a regression records an
    invocation instead of rebuilding the developer's install) and cwd set to the
    checkout, which is where a SessionStart hook would actually run.
    """
    sentinel = tmp_path / "installed-version"
    bindir = tmp_path / "bin"
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = subprocess.run(
        [str(SCRIPT), str(REPO), str(sentinel)],
        capture_output=True, text=True, cwd=str(REPO),
        env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"},
    )

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "the hook force-installed over the maintainer's dev checkout"
    assert not sentinel.exists()
