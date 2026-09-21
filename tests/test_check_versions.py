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
import os
import re
import shutil
import signal
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


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize("ignores_term", [False, True], ids=["hangs", "hangs and ignores TERM"])
def test_a_hanging_cli_is_abandoned_silently(tmp_path, ignores_term):
    """Session start must not wait on a `tcw` that never answers, and the
    abandoned command must not outlive the check — a wrapper's child included,
    which is why the stub's `sleep` is a separate process from the stub. A
    `tcw` that ignores TERM must not stretch the deadline either: the output
    pipe stays open, and so the check waits, for as long as it runs.

    The stub records its own PID and its child's, so the test checks and
    cleans up exactly those processes and nothing else."""
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    pids = tmp_path / "pids"
    _tcw(tmp_path / "bin",
         ('trap "" TERM\n' if ignores_term else "")
         + f"echo $$ > {pids}\nsleep 37 &\necho $! >> {pids}\nwait\n")

    started = time.monotonic()
    r = _run(plugin, tmp_path / "bin")
    elapsed = time.monotonic() - started

    time.sleep(0.5)
    left = [pid for pid in map(int, pids.read_text().split()) if _alive(pid)]
    for pid in left:
        os.kill(pid, signal.SIGKILL)
    _assert_silent(r)
    assert elapsed < 4, f"the check waited {elapsed:.1f}s on a hanging tcw"
    assert not left, f"the abandoned tcw is still running: {left}"


def test_a_child_left_holding_the_output_does_not_delay_the_warning(tmp_path):
    """`tcw` answers and exits, but a background child it started still holds
    the output pipe open. The substitution would wait for that child, so the
    check stops the whole process group once `tcw` itself has finished."""
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    pids = tmp_path / "pids"
    _tcw(tmp_path / "bin",
         f'echo "tcw 2.5.0"\nsleep 37 &\necho $! > {pids}\n')

    started = time.monotonic()
    r = _run(plugin, tmp_path / "bin")
    elapsed = time.monotonic() - started

    time.sleep(0.5)
    left = [pid for pid in map(int, pids.read_text().split()) if _alive(pid)]
    for pid in left:
        os.kill(pid, signal.SIGKILL)
    _assert_warns(r, "2.5.0", "2.4.0", "newer")
    assert elapsed < 4, f"the check waited {elapsed:.1f}s on tcw's leftover child"
    assert not left, f"tcw's leftover child is still running: {left}"


# Denies every file write except to /dev/null, like Codex's read-only sandbox.
READ_ONLY_PROFILE = '(version 1)(allow default)(deny file-write*)(allow file-write* (literal "/dev/null"))'


@pytest.mark.parametrize("how", ["mktemp fails", "writes denied"])
def test_works_where_no_file_can_be_written(tmp_path, how):
    """Codex's read-only sandbox refuses every file write, temporary files
    included; a check that needed one fell silent there (found at verify).

    The first case is portable: a `mktemp` that fails, as it does in that
    sandbox. The second runs the check under macOS's own sandbox with writes
    denied, which also catches any other write.
    """
    plugin = _plugin(tmp_path / "plugin", "2.4.0")
    bindir = tmp_path / "bin"
    _prints(bindir, "2.5.0")
    command = ["/bin/bash", str(plugin / "scripts" / "check_versions.sh")]
    if how == "mktemp fails":
        (bindir / "mktemp").write_text("#!/bin/sh\nexit 1\n")
        (bindir / "mktemp").chmod(0o755)
    else:
        if shutil.which("sandbox-exec") is None:
            pytest.skip("macOS sandbox-exec is not available here")
        command = ["sandbox-exec", "-p", READ_ONLY_PROFILE, *command]
    r = subprocess.run(command, capture_output=True, text=True, cwd=str(plugin),
                       env={"PATH": f"{bindir}:{SYSTEM_PATH}"})
    _assert_warns(r, "2.5.0", "2.4.0", "newer")


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
    other = _plugin(tmp_path / "other root", "2.5.0")
    _prints(tmp_path / "bin", "2.5.0")
    _assert_silent(_run(plugin, tmp_path / "bin", str(other)))
    _assert_warns(_run(plugin, tmp_path / "bin"), "2.5.0", "2.4.0", "newer")


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


# --- the instruction every skill carries -------------------------------------
#
# Under Claude the SessionStart hook runs the check. Codex may not run the hook,
# so each skill asks the agent to. Any one skill may be the only tcw skill a
# session loads, so every one carries the line. This proves the words are there,
# not that an agent acts on them; that was checked by hand at verify.

VERSION_CHECK_LINE = (
    "**Version check.** Under Claude Code, skip this: the session-start hook "
    "already ran it. Under any other harness, once per session before your first "
    "`tcw` command, run `bash \"<plugin>/scripts/check_versions.sh\"`, where "
    "`<plugin>` is two folders above the folder holding this `SKILL.md`, and pass "
    "on anything it prints to the user.")

SKILL_FILES = sorted((REPO / "skills").glob("*/SKILL.md"))


def test_every_shipped_skill_is_covered():
    """A new skill is caught here rather than silently joining the list below."""
    assert len(SKILL_FILES) == 17, [p.parent.name for p in SKILL_FILES]


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_every_skill_starts_with_the_version_check(skill):
    lines = skill.read_text(encoding="utf-8").splitlines()
    first_body_line = lines[lines.index("---", 1) + 1]
    assert first_body_line == VERSION_CHECK_LINE, (
        f"{skill.parent.name}/SKILL.md does not open with the version-check line")
