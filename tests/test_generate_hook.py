"""The `generate` resource contract.

These are the criteria the spec called the riskiest in C3, and they are written
so the failure modes that do not announce themselves — unbounded memory, a
deadlocked drain, an orphaned grandchild — fail loudly rather than hang.
"""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tcw.work.generate import GenerateError, run_generate

ENV = dict(os.environ)


def _run(command, tmp_path, *, stdin="", timeout=10, cap=64 * 1024):
    return run_generate(command, tmp_path, ENV, stdin, timeout, cap)


def test_stdout_becomes_the_text(tmp_path):
    assert _run("printf 'hello'", tmp_path).text == "hello"


def test_stdin_is_delivered(tmp_path):
    assert _run("cat", tmp_path, stdin='{"item": 1}').text == '{"item": 1}'


def test_a_script_that_never_reads_stdin_does_not_raise_brokenpipe(tmp_path):
    """The parent writes into a pipe nobody is reading. That is the script's
    choice, not a TCW crash."""
    big = "x" * (1024 * 1024)          # larger than a pipe buffer, so the write blocks
    assert _run("printf 'done'", tmp_path, stdin=big).text == "done"


def test_a_non_zero_exit_discards_everything_it_printed(tmp_path):
    with pytest.raises(GenerateError) as e:
        _run("printf 'half a prompt'; exit 3", tmp_path)
    assert "exit 3" in str(e.value)
    assert "discarded" in str(e.value)
    # The failure carries no text at all — an implementation that returned the
    # partial output *and* raised would pass a status-only check.
    assert not hasattr(e.value, "text")


def test_exactly_the_cap_succeeds_and_one_byte_over_fails(tmp_path):
    cap = 1024
    assert len(_run(f"printf 'a%.0s' $(seq {cap})", tmp_path, cap=cap).text) == cap
    with pytest.raises(GenerateError) as e:
        _run(f"printf 'a%.0s' $(seq {cap + 1})", tmp_path, cap=cap)
    assert str(cap) in str(e.value) and "output cap" in str(e.value)


def test_the_cap_counts_bytes_not_characters(tmp_path):
    """A cap on characters is not a cap on memory. Three-byte characters make
    the difference observable: 400 of them are 1200 bytes."""
    with pytest.raises(GenerateError):
        _run("printf '好%.0s' $(seq 400)", tmp_path, cap=1000)
    assert _run("printf '好%.0s' $(seq 400)", tmp_path, cap=2000).text == "好" * 400


def test_an_unbounded_generator_fails_promptly_instead_of_buffering(tmp_path):
    """The property no functional assertion catches.

    `yes` never ends. An implementation that buffers until the child exits — what
    `subprocess.run(capture_output=True)` does — never returns here, so the
    wall-clock bound turns a hang into a failure. The timeout is far longer than
    the bound, so passing this means the *cap* ended it, not the clock.
    """
    started = time.monotonic()
    with pytest.raises(GenerateError) as e:
        _run("yes 'aaaaaaaaaaaaaaaa'", tmp_path, timeout=60, cap=64 * 1024)
    elapsed = time.monotonic() - started
    assert "output cap" in str(e.value), "ended by the timeout, not the cap"
    assert elapsed < 15, f"took {elapsed:.1f}s — output is being buffered"


def test_a_chatty_stderr_does_not_deadlock(tmp_path):
    """Draining stdout alone blocks forever once the child fills the stderr pipe.

    512 KiB is comfortably past any platform's pipe buffer (64 KiB on Linux,
    smaller on macOS), so a single-stream reader hangs here and a concurrent one
    does not.
    """
    script = tmp_path / "chatty.sh"
    script.write_text(
        "#!/bin/sh\n"
        "i=0; while [ $i -lt 8192 ]; do "
        "printf 'noisy diagnostics line %d\\n' $i >&2; i=$((i+1)); done\n"
        "printf 'the prompt'\n")
    script.chmod(0o755)
    assert _run(str(script), tmp_path, timeout=60).text == "the prompt"


def test_the_timeout_fails_rather_than_truncating(tmp_path):
    with pytest.raises(GenerateError) as e:
        _run("printf 'started'; sleep 30", tmp_path, timeout=1)
    assert "timeout" in str(e.value)


def test_a_grandchild_does_not_survive_the_timeout(tmp_path):
    """`shell=True` means the child is a shell; killing it alone leaves the
    pipeline it started running, holding the pipes open."""
    marker = tmp_path / "grandchild.pid"
    script = tmp_path / "spawner.sh"
    script.write_text(
        f"#!/bin/sh\n"
        f"sh -c 'echo $$ > {marker}; sleep 30' &\n"
        f"sleep 30\n")
    script.chmod(0o755)
    with pytest.raises(GenerateError):
        _run(str(script), tmp_path, timeout=2)

    assert marker.is_file(), "the grandchild never started; the test proves nothing"
    pid = int(marker.read_text().strip())
    time.sleep(0.5)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)               # raises only if the process is gone


def test_invalid_utf8_is_replaced_rather_than_fatal(tmp_path):
    out = _run(r"printf 'ok\xff\xfe'", tmp_path).text
    assert out.startswith("ok")
    assert "�" in out


def test_stderr_is_forwarded_not_swallowed(tmp_path, capfd):
    _run("printf 'text'; printf 'a warning' >&2", tmp_path)
    assert "a warning" in capfd.readouterr().err


def test_a_command_that_cannot_start_is_an_error_not_a_traceback(tmp_path):
    with pytest.raises(GenerateError):
        _run("this-command-does-not-exist-anywhere; exit 127", tmp_path)
