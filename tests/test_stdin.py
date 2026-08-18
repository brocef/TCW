"""The bounded stdin reader: every descriptor shape, every ending.

These drive real file descriptors rather than mocks, because the bug being fixed
is a property of descriptors — an `isatty()`-false pipe that no one will ever
close — and a mock cannot be that.
"""

import os
import socket
import threading
import time

import pytest

from tcw.stdin import DEFAULT_TIMEOUT, StdinTruncated, read_piped_stdin

FAST = 0.3          # long enough not to be flaky, short enough to keep the suite quick


class _Stdin:
    """The bare surface `read_piped_stdin` uses of `sys.stdin`."""

    def __init__(self, fd, tty=False):
        self._fd, self._tty = fd, tty

    def isatty(self):
        return self._tty

    def fileno(self):
        if self._fd is None:
            raise ValueError("redirected stdin is pseudofile, has no fileno()")
        return self._fd


@pytest.fixture
def at(monkeypatch):
    """Point `sys.stdin` at a descriptor for the duration of one test."""
    def _use(fd, tty=False):
        monkeypatch.setattr("sys.stdin", _Stdin(fd, tty))
    return _use


def _pipe():
    r, w = os.pipe()
    return r, w


# -- the three endings ------------------------------------------------------

def test_eof_returns_the_text_silently(at, capsys):
    r, w = _pipe()
    os.write(w, b"piped body\n")
    os.close(w)
    at(r)
    assert read_piped_stdin(FAST) == "piped body\n"
    assert capsys.readouterr().err == ""
    os.close(r)


def test_nothing_arrives_proceeds_with_a_warning(at, capsys):
    """Arm A: the hang. Must return empty, warn, and not raise."""
    r, w = _pipe()
    at(r)
    start = time.monotonic()
    assert read_piped_stdin(FAST) == ""
    elapsed = time.monotonic() - start
    assert FAST <= elapsed < FAST + 2       # it waited, then gave up
    err = capsys.readouterr().err
    assert "no piped input" in err and "TCW_STDIN_TIMEOUT" in err
    os.close(r)
    os.close(w)


def test_a_stalled_stream_is_refused_not_truncated(at, capsys):
    """The case a bounded read makes silent if you are not careful."""
    r, w = _pipe()
    os.write(w, b"first")                   # arrives, then the writer stalls
    at(r)
    with pytest.raises(StdinTruncated) as excinfo:
        read_piped_stdin(FAST)
    message = str(excinfo.value)
    assert "5 byte" in message              # names what it received
    assert "TCW_STDIN_TIMEOUT" in message   # names the way out
    os.close(r)
    os.close(w)


def test_truncation_is_a_valueerror_so_every_cli_already_handles_it():
    """The five intake call sites all catch ValueError; this is why no new
    error handling was needed anywhere."""
    assert issubclass(StdinTruncated, ValueError)


# -- descriptor shapes ------------------------------------------------------

def test_a_terminal_is_never_read(at, capsys):
    r, w = _pipe()
    os.write(w, b"should not be read")
    at(r, tty=True)
    assert read_piped_stdin(FAST) == ""
    assert capsys.readouterr().err == ""
    os.close(r)
    os.close(w)


def test_devnull_is_immediate_eof(at, capsys):
    fd = os.open(os.devnull, os.O_RDONLY)
    at(fd)
    start = time.monotonic()
    assert read_piped_stdin(FAST) == ""
    assert time.monotonic() - start < FAST  # EOF, not a timeout
    assert capsys.readouterr().err == ""    # and therefore no warning
    os.close(fd)


def test_a_regular_file_is_read_to_eof(at, tmp_path):
    p = tmp_path / "intake.txt"
    p.write_text("from a file\n", encoding="utf-8")
    fd = os.open(p, os.O_RDONLY)
    at(fd)
    assert read_piped_stdin(FAST) == "from a file\n"
    os.close(fd)


def test_a_socket_is_read_to_eof(at):
    a, b = socket.socketpair()
    a.sendall(b"sock body\n")
    a.close()
    at(b.fileno())
    assert read_piped_stdin(FAST) == "sock body\n"
    b.close()


def test_a_closed_descriptor_yields_no_intake(at, capsys):
    r, w = _pipe()
    os.close(r)
    os.close(w)
    at(r)
    assert read_piped_stdin(FAST) == ""


def test_stdin_without_a_descriptor_yields_no_intake(at):
    """What pytest's own captured stdin does."""
    at(None)
    assert read_piped_stdin(FAST) == ""


# -- streaming --------------------------------------------------------------

def test_a_slow_producer_within_the_gap_is_not_dropped(at):
    r, w = _pipe()

    def produce():
        time.sleep(FAST / 2)
        os.write(w, b"slow body\n")
        os.close(w)

    threading.Thread(target=produce, daemon=True).start()
    at(r)
    assert read_piped_stdin(FAST) == "slow body\n"
    os.close(r)


def test_total_duration_may_exceed_the_bound_if_the_gaps_do_not(at):
    """The timeout measures a gap in the stream, not how long the stream lasts —
    the whole reason a single up-front poll would be wrong."""
    r, w = _pipe()

    def produce():
        for i in range(3):
            time.sleep(FAST * 0.6)
            os.write(w, f"chunk{i} ".encode())
        os.close(w)

    threading.Thread(target=produce, daemon=True).start()
    at(r)
    start = time.monotonic()
    assert read_piped_stdin(FAST) == "chunk0 chunk1 chunk2 "
    assert time.monotonic() - start > FAST   # outlasted the bound, lost nothing
    os.close(r)


def test_a_multibyte_character_split_across_writes_survives(at):
    r, w = _pipe()
    payload = "héllo wörld ✓\n".encode("utf-8")

    def produce():
        os.write(w, payload[:5])             # cuts mid-sequence
        time.sleep(FAST / 6)
        os.write(w, payload[5:])
        os.close(w)

    threading.Thread(target=produce, daemon=True).start()
    at(r)
    assert read_piped_stdin(FAST) == "héllo wörld ✓\n"
    os.close(r)


def test_undecodable_bytes_do_not_crash(at):
    r, w = _pipe()
    os.write(w, b"ok \xff\xfe done")
    os.close(w)
    at(r)
    assert read_piped_stdin(FAST).startswith("ok ")
    os.close(r)


# -- the timeout knob -------------------------------------------------------

@pytest.mark.parametrize("raw", ["", "abc", "-1", "nan-ish"])
def test_an_unusable_timeout_setting_falls_back_to_the_default(at, monkeypatch, raw):
    monkeypatch.setenv("TCW_STDIN_TIMEOUT", raw)
    fd = os.open(os.devnull, os.O_RDONLY)
    at(fd)
    assert read_piped_stdin() == ""          # no crash, default applies
    os.close(fd)


def test_the_timeout_is_configurable(at, monkeypatch, capsys):
    monkeypatch.setenv("TCW_STDIN_TIMEOUT", "0")
    r, w = _pipe()
    at(r)
    start = time.monotonic()
    assert read_piped_stdin() == ""
    assert time.monotonic() - start < 0.2    # did not wait
    assert capsys.readouterr().err == ""     # 0 is an opt-out, not a mistake
    os.close(r)
    os.close(w)


def test_the_default_bound_is_two_seconds():
    assert DEFAULT_TIMEOUT == 2.0
