"""`scripts/remote_session_setup.sh` — the remote-session contributor provisioning.

Hermetic by construction, the way `tests/test_session_bootstrap.py` is: every run
gets a PATH of `tmp_path/bin:/usr/bin:/bin`, so the only `python3`, `claude`, and
`tcw` the script can find are stubs this file wrote, and `_run` asserts that the
`python3` resolvable on that PATH is one of them. **No test may run a real `pip`
or a real `claude`** — one that did would reinstall the developer's own checkout
or rewrite their plugin state.

The stubs are argv recorders: each appends its arguments to a log and exits with
a status the test chose through the environment, so every assertion is about
*what the script decided to run*, never about what an install did.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "remote_session_setup.sh"

SYSTEM_PATH = "/usr/bin:/bin"


def _stub(bindir: Path, name: str, body: str) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    p = bindir / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(0o755)
    return p


def _python3(bindir: Path, log: Path) -> None:
    """A `python3` that records argv and answers the three calls the script makes.

    `-` is the already-installed guard (heredoc on stdin), `-m pip` the install,
    `-m site --user-base` the PATH repair. Return codes come from the
    environment so a test can make any one of them fail without a new stub.
    """
    _stub(
        bindir,
        "python3",
        f'printf "%s\\n" "$*" >> "{log}"\n'
        "case \"$1\" in\n"
        '  -) exit "${STUB_GUARD_RC:-1}" ;;\n'
        "  -m)\n"
        '    case "$2" in\n'
        '      pip) exit "${STUB_PIP_RC:-0}" ;;\n'
        '      site) printf "%s\\n" "${STUB_USER_BASE:-/nonexistent}"; exit 0 ;;\n'
        "    esac ;;\n"
        "esac\n"
        "exit 0\n",
    )


def _claude(bindir: Path, log: Path) -> None:
    """A `claude` that records argv; `marketplace add` and `install` fail separately."""
    _stub(
        bindir,
        "claude",
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'case "$2" in\n'
        '  marketplace) exit "${STUB_MARKETPLACE_RC:-0}" ;;\n'
        '  install) exit "${STUB_INSTALL_RC:-0}" ;;\n'
        "esac\n"
        "exit 0\n",
    )


def _project(tmp_path: Path, pyproject: bool = True) -> Path:
    root = tmp_path / "checkout"
    root.mkdir()
    if pyproject:
        (root / "pyproject.toml").write_text('[project]\nname = "tcw-cli"\n')
    return root


def _run(tmp_path: Path, root: Path, *args: str, **env_overrides: str):
    bindir = tmp_path / "bin"
    log = tmp_path / "argv.log"
    log.touch()
    _python3(bindir, log)
    if env_overrides.pop("_no_claude", None) is None:
        _claude(bindir, log)
    if env_overrides.pop("_tcw_on_path", None) is not None:
        _stub(bindir, "tcw", "exit 0\n")

    path = f"{bindir}:{SYSTEM_PATH}"
    # The docstring's hermeticity claim, made true rather than assumed: a run
    # that reached the real python3 would install into the developer's own
    # interpreter.
    found = shutil.which("python3", path=path)
    assert found is not None and found.startswith(f"{bindir}/"), f"real python3 on the test PATH: {found}"

    env = {
        "PATH": path,
        "HOME": str(tmp_path / "home"),
        "CLAUDE_PROJECT_DIR": str(root),
    }
    env.update({k: v for k, v in env_overrides.items() if v is not None})
    proc = subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )
    return proc, log.read_text().splitlines()


# --- the script itself ------------------------------------------------------


def test_script_parses_and_is_executable():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    assert SCRIPT.stat().st_mode & stat.S_IXUSR, f"{SCRIPT} is not executable"


# --- the gate ---------------------------------------------------------------


def test_local_session_does_nothing(tmp_path):
    proc, log = _run(tmp_path, _project(tmp_path))
    assert proc.returncode == 0
    assert log == [], f"a local session ran something: {log}"
    assert proc.stdout == ""


def test_claude_code_remote_false_does_nothing(tmp_path):
    proc, log = _run(tmp_path, _project(tmp_path), CLAUDE_CODE_REMOTE="false")
    assert proc.returncode == 0
    assert log == []


def test_remote_session_installs_package_then_plugin(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true")
    assert proc.returncode == 0
    assert proc.stdout == "", proc.stdout
    assert log[0] == f"-m pip install -e {root}[dev]"
    assert log[1] == f"plugin marketplace add {root}"
    assert log[2] == "plugin install tcw@tcw -y"


def test_force_runs_outside_a_remote_session(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(tmp_path, root, "--force")
    assert proc.returncode == 0
    assert any(line.startswith("-m pip install") for line in log), log
    assert any(line.startswith("plugin install") for line in log), log


def test_unknown_argument_reports_and_does_nothing(tmp_path):
    proc, log = _run(tmp_path, _project(tmp_path), "--yolo", CLAUDE_CODE_REMOTE="true")
    assert proc.returncode == 0
    assert len(proc.stdout.strip().splitlines()) == 1
    assert "--force" in proc.stdout
    assert log == []


def test_a_root_without_pyproject_is_not_this_checkout(tmp_path):
    root = _project(tmp_path, pyproject=False)
    proc, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true")
    assert proc.returncode == 0
    assert log == []


# --- the already-installed guard -------------------------------------------


def test_installed_checkout_skips_pip_but_still_ensures_the_plugin(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(
        tmp_path,
        root,
        CLAUDE_CODE_REMOTE="true",
        STUB_GUARD_RC="0",
        _tcw_on_path="yes",
    )
    assert proc.returncode == 0
    assert not any("pip install" in line for line in log), log
    assert log[0] == f"- {root}", log
    assert log[1] == f"plugin marketplace add {root}"


def test_guard_is_not_consulted_without_a_tcw_on_path(tmp_path):
    """No `tcw` to identify means nothing is installed — ask pip, not the guard."""
    root = _project(tmp_path)
    _, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true", STUB_GUARD_RC="0")
    assert log[0] == f"-m pip install -e {root}[dev]", log


# --- failure paths: one line each, and the session still starts -------------


def test_failing_pip_retries_once_then_reports(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true", STUB_PIP_RC="1")
    assert proc.returncode == 0
    installs = [line for line in log if "pip install" in line]
    assert len(installs) == 2, installs
    assert installs[1].endswith("--break-system-packages")
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1, proc.stdout
    assert "pip install" in lines[0]


def test_a_failing_marketplace_add_does_not_attempt_the_install(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true", STUB_MARKETPLACE_RC="1")
    assert proc.returncode == 0
    assert not any(line.startswith("plugin install") for line in log), log
    assert len(proc.stdout.strip().splitlines()) == 1


def test_a_failing_plugin_install_reports_once(tmp_path):
    proc, _ = _run(tmp_path, _project(tmp_path), CLAUDE_CODE_REMOTE="true", STUB_INSTALL_RC="1")
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1 and "plugin install" in lines[0]


def test_a_missing_claude_still_installs_the_package(tmp_path):
    root = _project(tmp_path)
    proc, log = _run(tmp_path, root, CLAUDE_CODE_REMOTE="true", _no_claude="yes")
    assert proc.returncode == 0
    assert log == [f"-m pip install -e {root}[dev]"], log
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1 and "claude" in lines[0]


# --- invariants -------------------------------------------------------------


@pytest.mark.parametrize("scope", ["--scope project", "--scope local"])
def test_the_plugin_is_never_installed_into_the_checkout(tmp_path, scope):
    """Project or local scope would write the marketplace into the repository's
    own .claude/settings.json — a session start that dirties the working tree."""
    _, log = _run(tmp_path, _project(tmp_path), CLAUDE_CODE_REMOTE="true")
    assert not any(scope in line for line in log), log


def test_path_repair_is_written_to_the_harness_env_file(tmp_path):
    """An install that lands outside PATH is installed and unusable."""
    root = _project(tmp_path)
    user_base = tmp_path / "userbase"
    (user_base / "bin").mkdir(parents=True)
    installed = user_base / "bin" / "tcw"
    installed.write_text("#!/bin/sh\nexit 0\n")
    installed.chmod(0o755)
    env_file = tmp_path / "env"
    env_file.touch()

    proc, _ = _run(
        tmp_path,
        root,
        CLAUDE_CODE_REMOTE="true",
        STUB_USER_BASE=str(user_base),
        CLAUDE_ENV_FILE=str(env_file),
    )
    assert proc.returncode == 0
    assert env_file.read_text().strip() == f'export PATH="{user_base}/bin:$PATH"'


def test_no_path_repair_when_the_user_base_holds_nothing(tmp_path):
    root = _project(tmp_path)
    env_file = tmp_path / "env"
    env_file.touch()
    _run(
        tmp_path,
        root,
        CLAUDE_CODE_REMOTE="true",
        STUB_USER_BASE=str(tmp_path / "empty"),
        CLAUDE_ENV_FILE=str(env_file),
    )
    assert env_file.read_text() == ""


def test_the_plugin_bootstrap_is_untouched_by_this_script():
    """The published install path stays the plugin's own; this one must not
    mention pipx or the PyPI distribution at all."""
    text = SCRIPT.read_text()
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "pipx" not in body
    assert "tcw-cli" not in body


# --- the hook that calls it -------------------------------------------------

SETTINGS = REPO / ".claude" / "settings.json"


def test_settings_registers_the_script_as_a_session_start_hook():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for matcher in settings["hooks"]["SessionStart"]
        for hook in matcher["hooks"]
        if hook.get("type") == "command"
    ]
    assert any("scripts/remote_session_setup.sh" in c for c in commands), commands


def test_settings_still_enables_the_tcw_plugin():
    """The hook installs `tcw@tcw`; settings enabling it is the other half."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert settings["enabledPlugins"]["tcw@tcw"] is True
