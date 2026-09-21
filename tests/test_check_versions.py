"""`scripts/check_versions.sh` — the warning that the CLI and the skills differ.

The script ships with the plugin, not the CLI, because the CLI cannot know which
skills an agent loaded, and a check inside the CLI would be missing exactly when
the CLI is the older side. So these tests treat the CLI as a black box: a stub
`tcw` on a PATH of `tmp_path/bin:/usr/bin:/bin` that prints a chosen
`--version` line, and a throwaway plugin folder holding a copy of the script
and a manifest.

Every run goes through `/bin/bash` explicitly: on macOS that is bash 3.2, the
oldest shell the script has to work under.
"""
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import tcw

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "check_versions.sh"
SYSTEM_PATH = "/usr/bin:/bin"

# The first words of the warning. Tests recognize the message by it.
PREFIX = "tcw: the `tcw` CLI on your PATH is"
NEWER_ADVICE = "claude plugin update tcw@tcw"
OLDER_ADVICE = "pipx upgrade tcw-cli"


def _plugin(folder: Path, version: str | None, manifest: str = ".claude-plugin") -> Path:
    """A plugin folder with a copy of the script and, if asked, a manifest."""
    (folder / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, folder / "scripts" / "check_versions.sh")
    if version is not None:
        (folder / manifest).mkdir()
        (folder / manifest / "plugin.json").write_text(
            f'{{\n    "name": "tcw",\n    "version": "{version}",\n    "skills": "./skills/"\n}}\n')
    return folder


def _tcw(bindir: Path, body: str) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "tcw"
    stub.write_text("#!/bin/sh\n" + body)
    stub.chmod(0o755)


def _prints(bindir: Path, version: str) -> None:
    _tcw(bindir, f'echo "tcw {version}"\n')


def _run(plugin: Path, bindir: Path, *args: str, cwd: Path | None = None):
    return subprocess.run(
        ["/bin/bash", str(plugin / "scripts" / "check_versions.sh"), *args],
        capture_output=True, text=True, cwd=str(cwd or plugin),
        env={"PATH": f"{bindir}:{SYSTEM_PATH}"},
    )


def _assert_silent(r) -> None:
    assert r.returncode == 0, r
    assert r.stdout == "", r.stdout
    assert r.stderr == "", r.stderr


def _assert_warns(r, cli: str, skills: str, direction: str) -> None:
    """One property, one helper: a warning naming both versions and the right advice."""
    assert r.returncode == 0, r
    assert r.stderr == "", r.stderr
    first = r.stdout.splitlines()[0] if r.stdout else ""
    assert first.startswith(f"{PREFIX} {cli},"), r.stdout
    assert f"loaded in this session are from {skills}." in first, r.stdout
    wanted, unwanted = ((NEWER_ADVICE, OLDER_ADVICE) if direction == "newer"
                        else (OLDER_ADVICE, NEWER_ADVICE))
    assert wanted in r.stdout, r.stdout
    assert unwanted not in r.stdout, r.stdout


def test_matching_versions_print_nothing(tmp_path):
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    _prints(tmp_path / "bin", "2.4.0")
    _assert_silent(_run(plugin, tmp_path / "bin"))


def test_cli_newer(tmp_path):
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    _prints(tmp_path / "bin", "2.5.0")
    r = _run(plugin, tmp_path / "bin")
    _assert_warns(r, "2.5.0", "2.4.0", "newer")
    assert "pipx install --force tcw-cli==2.4.0" in r.stdout


def test_cli_older(tmp_path):
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    _prints(tmp_path / "bin", "2.3.0")
    r = _run(plugin, tmp_path / "bin")
    _assert_warns(r, "2.3.0", "2.4.0", "older")
    assert "If that does not reach 2.4.0" in r.stdout


@pytest.mark.parametrize("skills, cli, direction", [
    ("2.4.0", "2.4.1", "newer"),
    ("2.4.1", "2.4.0", "older"),
])
def test_patch_only_mismatch_in_both_directions(tmp_path, skills, cli, direction):
    plugin = _plugin(tmp_path / "plugin", skills)
    _prints(tmp_path / "bin", cli)
    _assert_warns(_run(plugin, tmp_path / "bin"), cli, skills, direction)


def test_comparison_is_numeric(tmp_path):
    """As text, "2.10.0" sorts before "2.9.0"; as a version it is newer."""
    plugin = _plugin(tmp_path / "plugin", "2.9.0")
    _prints(tmp_path / "bin", "2.10.0")
    _assert_warns(_run(plugin, tmp_path / "bin"), "2.10.0", "2.9.0", "newer")


@pytest.mark.parametrize("case", [
    "no tcw on PATH",
    "tcw fails",
    "tcw prints something else",
    "no manifest",
    "manifest without a version",
])
def test_cannot_tell_means_silent(tmp_path, case):
    """A missing or broken CLI is the setup skill's job, not a mismatch."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    plugin = _plugin(tmp_path / "plugin", None if case.startswith(("no manifest", "manifest"))
                     else "2.4.0")
    if case == "manifest without a version":
        (plugin / ".claude-plugin").mkdir()
        (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "tcw"}\n')
    if case == "tcw fails":
        _tcw(bindir, 'echo "tcw 2.5.0"\nexit 3\n')
    elif case == "tcw prints something else":
        _tcw(bindir, "echo something else\n")
    elif case != "no tcw on PATH":
        _prints(bindir, "2.5.0")
    assert shutil.which("tcw", path=f"{bindir}:{SYSTEM_PATH}") is None or case != "no tcw on PATH"
    _assert_silent(_run(plugin, bindir))


def test_a_hanging_cli_is_abandoned_silently(tmp_path):
    """Session start must not wait on a `tcw` that never answers, and the
    abandoned command must not outlive the check — a wrapper's child included,
    which is why the stub's `sleep` is a separate process from the stub."""
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    _tcw(tmp_path / "bin", "sleep 37.4\n")

    started = time.monotonic()
    r = _run(plugin, tmp_path / "bin")
    elapsed = time.monotonic() - started

    _assert_silent(r)
    assert elapsed < 4, f"the check waited {elapsed:.1f}s on a hanging tcw"
    time.sleep(0.5)
    left = subprocess.run(["pgrep", "-f", "sleep 37.4"], capture_output=True, text=True)
    if left.stdout.strip():
        subprocess.run(["pkill", "-f", "sleep 37.4"])
    assert left.stdout.strip() == "", "the abandoned tcw is still running"


def test_codex_manifest_alone_is_enough(tmp_path):
    plugin = _plugin(tmp_path / "plugin", "2.4.0", manifest=".codex-plugin")
    _prints(tmp_path / "bin", "2.5.0")
    _assert_warns(_run(plugin, tmp_path / "bin"), "2.5.0", "2.4.0", "newer")


def test_root_is_found_from_the_script_location(tmp_path):
    """No argument, an unrelated working directory, and a space in the path."""
    plugin = _plugin(tmp_path / "plugin root with space", "2.4.0")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    _prints(tmp_path / "bin", "2.5.0")
    _assert_warns(_run(plugin, tmp_path / "bin", cwd=elsewhere), "2.5.0", "2.4.0", "newer")


def test_an_explicit_root_wins(tmp_path):
    """The bootstrap passes the plugin root it was given; that one is read."""
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    other = tmp_path / "other root"
    (other / ".claude-plugin").mkdir(parents=True)
    (other / ".claude-plugin" / "plugin.json").write_text('{"version": "2.5.0"}\n')
    _prints(tmp_path / "bin", "2.5.0")
    _assert_silent(_run(plugin, tmp_path / "bin", str(other)))


def test_the_real_manifests_parse(tmp_path):
    """The shipped manifests, not only the tests' minimal one."""
    ver = tcw.__version__
    major, minor, patch = (int(p) for p in ver.split("."))
    bindir = tmp_path / "bin"
    _prints(bindir, ver)
    _assert_silent(_run(REPO, bindir, str(REPO)))
    higher = f"{major}.{minor}.{patch + 1}"
    _prints(bindir, higher)
    _assert_warns(_run(REPO, bindir, str(REPO)), higher, ver, "newer")


def test_script_uses_no_forbidden_tools():
    """No `python3` (the PATH one is the wrong interpreter to ask anything), no
    `jq` (not installed everywhere), no `timeout` (macOS has none)."""
    code = "\n".join(line.split("#", 1)[0] for line in SCRIPT.read_text().splitlines())
    for tool in (r"\bpython3?\b", r"\bjq\b", r"\btimeout\b"):
        assert not re.search(tool, code), f"check_versions.sh calls {tool}"
