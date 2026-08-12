"""`scripts/session_bootstrap.sh` — the SessionStart install reconcile.

Hermetic by construction: every run gets a PATH of `tmp_path/bin:/usr/bin:/bin`,
so the only `pipx`, `tcw`, and `python3` the script can find are stubs this file
wrote, and `_run` asserts that no pipx outside `tmp_path/bin` is resolvable on
that PATH — a distro-packaged `/usr/bin/pipx` would otherwise make the claim
false without failing anything. **No test may invoke real pipx** — one that did
would rebuild the developer's own install.

The exception is `test_real_editable_checkout_is_left_alone`, which runs against
this repo with the real PATH on purpose: the guard it covers is the one whose
failure lands on the maintainer first.
"""
import json
import os
import re
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


def _stub(bindir: Path, name: str, body: str, shebang: str = "#!/bin/sh") -> Path:
    """A fake executable on the test PATH.

    `shebang` matters for the `tcw` stub specifically: the script identifies who
    owns the `tcw` on PATH by reading its shebang, so a stub standing in for a
    pip/pipx console script needs one naming a Python, and a stub standing in for
    a version manager's shim needs one that does not.
    """
    bindir.mkdir(parents=True, exist_ok=True)
    p = bindir / name
    p.write_text(shebang + "\n" + body)
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
    path = path or f"{bindir}:{SYSTEM_PATH}"
    # The docstring's hermeticity claim, made true by construction rather than by
    # assuming /usr/bin has no pipx — distro-packaged pipx lives exactly there,
    # and a run that reached it would rebuild the developer's real install.
    found = shutil.which("pipx", path=path)
    assert found is None or found.startswith(f"{bindir}/"), f"real pipx on the test PATH: {found}"
    env = {
        "PATH": path,
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
    owner = _stub(bindir, "python3.11", "exit 0\n")  # "yes, editable"
    _stub(bindir, "tcw", "exit 0\n", shebang=f"#!{owner}")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "an editable install must never be force-installed over"
    assert not sentinel.exists()


def test_editable_install_owned_by_another_interpreter_is_left_alone(tmp_path):
    """The D1 case: `pipx install -e`, or an editable install in a venv.

    The interpreter that owns `tcw` is not the `python3` on PATH, and asking the
    latter raises `PackageNotFoundError` — which, swallowed, reads as "not
    editable" and force-installs over the developer's checkout every session.
    """
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    bindir = tmp_path / "bin"
    owner = _stub(bindir, "python3.11", "exit 0\n")  # the venv's own: "editable"
    _stub(bindir, "python3", "exit 1\n")  # PATH's: never heard of tcw
    _stub(bindir, "tcw", "exit 0\n", shebang=f"#!{owner}")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "asked the PATH python3 instead of tcw's own interpreter"
    assert not sentinel.exists()


def test_install_we_cannot_identify_is_left_alone(tmp_path):
    """A version manager's shim (`#!/usr/bin/env bash`) names no interpreter.

    Nothing can be asked about it, so it is not ours to replace — the same
    default that covers wrappers and anything else non-Python on PATH.
    """
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    bindir = tmp_path / "bin"
    _stub(bindir, "python3", "exit 1\n")
    _stub(bindir, "tcw", "exit 0\n", shebang="#!/usr/bin/env bash")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert not log.exists(), "unknown provenance must never be force-installed over"
    assert not sentinel.exists()


def test_missing_pipx_is_silent_and_leaves_the_sentinel(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    sentinel.write_text('__version__ = "0.0.1"\n')  # stale: differs from the clone
    bindir = tmp_path / "bin"
    bindir.mkdir()
    # no tcw on PATH (so the provenance guard cannot pre-empt this), and no pipx
    # stub — the assert in `_run` proves /usr/bin:/bin has none either

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert r.stdout == ""
    assert sentinel.read_text() == '__version__ = "0.0.1"\n'


def test_failed_install_prints_one_line_and_retries_next_time(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    sentinel.write_text('__version__ = "0.0.1"\n')
    bindir = tmp_path / "bin"
    owner = _stub(bindir, "python3.11", "exit 1\n")  # a plain install: replaceable
    _stub(bindir, "tcw", "exit 0\n", shebang=f"#!{owner}")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log, rc=1)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0, "a failure must not surface as a hook error"
    assert r.stderr == "", "SessionStart shows the agent stdout, not stderr"
    lines = r.stdout.splitlines()
    assert len(lines) == 1 and "/tcw-doctor" in lines[0], r.stdout
    assert sentinel.read_text() == '__version__ = "0.0.1"\n', "a stale sentinel is what forces the retry"
    assert log.read_text().strip().endswith("tcw-cli")


def test_successful_install_writes_the_sentinel_then_goes_quiet(tmp_path):
    root = _clone(tmp_path)
    sentinel = tmp_path / "data" / "installed-version"  # parent does not exist yet
    bindir = tmp_path / "bin"
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log, installs=bindir / "tcw")  # nothing on PATH yet

    first = _run(root, sentinel, bindir)

    assert first.returncode == 0
    assert first.stdout == ""
    assert log.read_text().strip() == "install --force tcw-cli"
    assert sentinel.read_bytes() == (root / "tcw" / "__init__.py").read_bytes()

    second = _run(root, sentinel, bindir)

    assert second.returncode == 0
    assert second.stdout == ""
    assert len(log.read_text().splitlines()) == 1, "the second run must take the silent path"


# --- the probe itself --------------------------------------------------------
#
# The fixture tests above stub the owning interpreter with `exit 0` / `exit 1`,
# so they prove the script's *branches* without ever running the Python that
# decides which branch is right. These run that Python, against synthetic
# dist-info trees, so the decision is covered on any machine — including one
# where `test_real_editable_checkout_is_left_alone` takes the shebang branch and
# never reaches the probe at all.


def _editable_probe() -> str:
    """The probe, read out of the shell script rather than copied beside it.

    A second copy would need a test policing the two for drift; extracting it
    means the text these tests exercise is literally the text that ships.
    """
    blocks = re.findall(r"<<'PY'\n(.*?)\nPY\n", SCRIPT.read_text(encoding="utf-8"), re.DOTALL)
    assert len(blocks) == 1, f"expected one PY heredoc in {SCRIPT.name}, found {len(blocks)}"
    return blocks[0]


_EDITABLE_PROBE = _editable_probe()


def _dist_info(site: Path, dist: str, editable: bool | None) -> None:
    """A minimal installed-distribution record `importlib.metadata` resolves.

    `editable=None` writes no `direct_url.json` at all — a plain `pip install`,
    which is the case the guard must *not* protect.
    """
    d = site / f"{dist.replace('-', '_')}-1.0.dist-info"
    d.mkdir(parents=True)
    (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {dist}\nVersion: 1.0\n")
    if editable is not None:
        (d / "direct_url.json").write_text(
            json.dumps({"url": "file:///checkout", "dir_info": {"editable": editable}})
        )


def _run_probe(site: Path) -> int:
    # `-S` keeps the real site-packages out: this interpreter has its own `tcw`
    # installed, which would answer for every case below if it were visible.
    return subprocess.run(
        [sys.executable, "-S", "-c", _EDITABLE_PROBE],
        cwd=tempfile.gettempdir(),
        env={"PYTHONPATH": str(site), "PATH": SYSTEM_PATH},
        capture_output=True,
    ).returncode


@pytest.mark.parametrize(
    "installed, editable, why",
    [
        ([("tcw-cli", True)], True, "the post-rename checkout"),
        ([("tcw", True)], True, "a checkout that predates the rename"),
        ([("tcw-cli", False)], False, "dir_info says not editable"),
        ([("tcw-cli", None)], False, "a plain pip install: no direct_url.json"),
        ([], False, "nothing installed under either name"),
        ([("tcw-cli", True), ("tcw", False)], True, "current name wins, and it is editable"),
        ([("tcw-cli", False), ("tcw", True)], False, "current name wins, and it is not"),
    ],
)
def test_probe_resolves_the_distribution_under_either_name(tmp_path, installed, editable, why):
    """`tcw` was taken on PyPI, so the distribution ships as `tcw-cli`.

    Looking up one name only is not a benign miss: `PackageNotFoundError` reads
    as "not editable", and the caller force-installs over the checkout. The last
    two cases pin the precedence — first name found decides, so the answer never
    depends on `importlib.metadata` iteration order.
    """
    site = tmp_path / "site-packages"
    site.mkdir()
    for dist, ed in installed:
        _dist_info(site, dist, ed)

    assert (_run_probe(site) == 0) is editable, why


@pytest.mark.parametrize("editable, forced", [(True, False), (False, True)])
def test_script_and_probe_together_decide_on_a_tcw_cli_install(tmp_path, editable, forced):
    """The script, a real interpreter, and a real dist-info tree — end to end.

    The fixtures above stub the interpreter's verdict; the probe cases above run
    the probe with no script around it. Neither covers the seam, which is
    precisely where the distribution rename bit: the script asked a question the
    probe could no longer answer for `tcw-cli`.

    The stand-in interpreter is a shell script *named* `python3.11` — the
    shebang guard matches on the path pattern, not on the file being a real
    binary — so the script's own code path runs the real probe against a
    synthetic site-packages. The non-editable case is what proves the test
    discriminates rather than passing for free.
    """
    root = _clone(tmp_path)
    sentinel = tmp_path / "installed-version"
    bindir = tmp_path / "bin"
    site = tmp_path / "site-packages"
    site.mkdir()
    _dist_info(site, "tcw-cli", editable)

    owner = _stub(bindir, "python3.11", f'PYTHONPATH={site} exec {sys.executable} -S "$@"\n')
    _stub(bindir, "tcw", "exit 0\n", shebang=f"#!{owner}")
    log = tmp_path / "pipx.log"
    _recording_pipx(bindir, log)

    r = _run(root, sentinel, bindir)

    assert r.returncode == 0
    assert log.exists() is forced, (
        "an editable tcw-cli was force-installed over" if editable
        else "a plain tcw-cli install should have been replaced"
    )


# --- the real thing ----------------------------------------------------------


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
    """The fixtures above prove the branches; this proves one fires for real.

    Runs with the real PATH (a stub pipx prepended, so a regression records an
    invocation instead of rebuilding the developer's install) and cwd set to the
    checkout, which is where a SessionStart hook would actually run.

    Which branch fires depends on the machine, and either is a pass: an editable
    `tcw` installed straight into an interpreter is caught by the probe, while
    one reached through a version manager's shim is caught earlier, by the
    shebang naming no interpreter to ask.
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
