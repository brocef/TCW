"""Running a `generate` hook, with the resource contract actually enforced.

**Why this is not `subprocess.run`.** `run(capture_output=True)` buffers all of a
child's output before returning, so an output cap checked afterwards is a cap on
the *result* and not on memory: a script printing forever exhausts the machine
before any check fires. Bounding it means reading incrementally and killing the
child the moment it goes over, which is `Popen` plus two reader threads.

The other three things that go wrong here, each addressed below: draining only
stdout deadlocks as soon as the child fills the stderr pipe; a `shell=True`
pipeline leaves grandchildren behind unless the whole process *group* is killed;
and a script that exits without reading stdin makes the parent's write raise
`BrokenPipeError`, which is the script's business and not a crash.

Trust model unchanged (`hooks.py:11-14`): `tcw-config.yaml` is the user's own
file and runs as they do. None of this is a sandbox — it is a bound on
accidents.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path


class GenerateError(Exception):
    """A `generate` hook did not produce usable text. The message says why."""


@dataclass(frozen=True)
class GenerateResult:
    text: str
    stderr: str


def _drain(stream, limit: int, out: list[bytes], overflow: threading.Event,
           stop_at_limit: bool) -> None:
    """Read `stream`, retaining at most `limit` bytes and flagging the overflow.

    Runs in its own thread per stream so neither pipe can fill while the other is
    being read — the deadlock a stdout-only reader hits against a chatty script.

    `stop_at_limit` is the difference between the two streams, and it matters:

    - **stdout** stops. Exceeding the cap is a hard failure, the caller kills the
      process group immediately, and reading further would be reading output
      nobody will use.
    - **stderr** keeps reading to EOF and throws the excess away. Closing the
      pipe on a script that is still writing diagnostics sends it `SIGPIPE`, so
      a merely chatty generator would die with exit -13 and its perfectly good
      stdout would be discarded for it.
    """
    total = 0
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            total += len(chunk)
            if total > limit:
                if not overflow.is_set():
                    out.append(chunk[:max(0, limit - (total - len(chunk)))])
                    overflow.set()
                if stop_at_limit:
                    return
                continue                # keep draining; drop the excess
            out.append(chunk)
    except (OSError, ValueError):
        return                      # pipe closed under us by the kill below
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _kill_group(proc: subprocess.Popen) -> None:
    """Kill the child *and* anything it started.

    `shell=True` means the child is a shell; its pipeline members are separate
    processes that survive killing the shell alone, keeping the pipes open and
    hanging the reader threads.
    """
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def run_generate(command: str, node_root: Path, env: dict[str, str],
                 stdin_text: str, timeout: int, output_cap: int) -> GenerateResult:
    """Run one `generate` hook and return its text, or raise `GenerateError`.

    Every failure mode is a raise, never a partial result: a script that writes
    half a prompt and then dies contributes nothing rather than something
    plausible.
    """
    try:
        proc = subprocess.Popen(
            command, shell=True, cwd=str(node_root), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True)     # its own process group, for the kill
    except OSError as e:
        raise GenerateError(f"`{command}` could not be started: {e}")

    out_chunks: list[bytes] = []
    err_chunks: list[bytes] = []
    out_over, err_over = threading.Event(), threading.Event()
    readers = [
        threading.Thread(target=_drain, daemon=True,
                         args=(proc.stdout, output_cap, out_chunks, out_over, True)),
        threading.Thread(target=_drain, daemon=True,
                         args=(proc.stderr, output_cap, err_chunks, err_over, False)),
    ]
    for t in readers:
        t.start()

    def _write_stdin() -> None:
        try:
            proc.stdin.write(stdin_text.encode("utf-8"))
        except (BrokenPipeError, OSError, ValueError):
            pass                      # the script exited without reading; fine
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    writer = threading.Thread(target=_write_stdin, daemon=True)
    writer.start()

    # Wait for the cap or the child, whichever comes first. Polling rather than
    # `proc.wait(timeout)` because the cap has to end the run *while* the child
    # is still happily printing — that is the whole point of bounding it.
    deadline = timeout
    step = 0.02
    waited = 0.0
    killed_for = ""
    while True:
        if out_over.is_set():
            killed_for = "cap"
            _kill_group(proc)
            break
        if proc.poll() is not None:
            break
        if waited >= deadline:
            killed_for = "timeout"
            _kill_group(proc)
            break
        # `wait` with a short timeout sleeps *and* reaps, so a child exiting
        # between polls is noticed immediately rather than after the next tick.
        try:
            proc.wait(timeout=step)
        except subprocess.TimeoutExpired:
            waited += step

    for t in (*readers, writer):
        t.join(timeout=5)
    returncode = proc.poll()
    if returncode is None:
        try:
            returncode = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            returncode = -1

    stderr_text = b"".join(err_chunks).decode("utf-8", errors="replace")

    if killed_for == "cap" or out_over.is_set():
        raise GenerateError(
            f"`{command}` produced more than the {output_cap}-byte output cap "
            f"(work.lifecycle.output-cap); nothing was used")
    if killed_for == "timeout":
        raise GenerateError(
            f"`{command}` exceeded the {timeout}s timeout "
            f"(work.lifecycle.timeout); nothing was used")
    if returncode != 0:
        # Everything is discarded, deliberately. Half a prompt reads like a
        # whole one to whoever gets it next.
        raise GenerateError(
            f"`{command}` failed (exit {returncode}); its output was discarded")

    if stderr_text:
        # Forwarded, not swallowed — a generator's diagnostics are how its
        # author debugs it, and this is what `run_bindings` already does.
        sys.stderr.write(stderr_text)
    # UTF-8 with replacement: failing on one bad byte in an otherwise fine
    # prompt trades a usable result for a purity nobody asked for.
    return GenerateResult(
        text=b"".join(out_chunks).decode("utf-8", errors="replace"),
        stderr=stderr_text)
