"""Reading piped intake without ever blocking on a stdin nobody will close.

`sys.stdin.isatty()` being false does **not** mean "a pipe carrying data". It
means "not a terminal", which also covers a pipe an ancestor process holds open
and never writes to — a subprocess, a CI runner, a hook. A bare
`sys.stdin.read()` on one of those waits for an EOF that never arrives, which is
how an automated caller gets stranded rather than failed.

So the read is bounded, and the bound is a **gap in the stream**, not a total
duration: `select` is polled before every chunk, so a producer that streams for a
minute is read in full while one that never starts gives up after one interval.

Three endings, deliberately distinct — conflating any two of them loses data:

* **EOF** — the producer finished. Return the text.
* **Nothing arrived** — ambiguous (usually no intake was intended), so proceed
  without it and say so on stderr.
* **Something arrived, then it stalled** — unambiguous: intake *was* intended and
  the rest is gone. Refuse, rather than store a fragment as though it were the
  document.

**This module owns file descriptor 0.** Call `read_piped_stdin()` before anything
touches `sys.stdin`, and do not read `sys.stdin` afterwards: bytes are taken with
`os.read` off the raw descriptor, so anything already pulled into the text
layer's buffer would be lost.

**Two paths, split on whether a real descriptor exists.** Everything above
describes the descriptor path. A `sys.stdin` with no `fileno()` — an embedder
substituting `io.StringIO`, pytest's captured stdin — is not an operating-system
stream at all, so it cannot be the inherited pipe this module guards against, and
it is read plainly. Getting that wrong is not theoretical: requiring a descriptor
silently broke in-process `main()` callers, and the suite caught it.
"""

from __future__ import annotations

import os
import select
import sys

DEFAULT_TIMEOUT = 2.0
TIMEOUT_ENV = "TCW_STDIN_TIMEOUT"
_CHUNK = 65536


class StdinTruncated(ValueError):
    """Piped input stopped arriving before EOF.

    A `ValueError` subclass on purpose. Every command that reads intake already
    runs inside a `try` that catches `ValueError` — `tcw/work/cli.py`'s
    `_ERRORS`, and the `except` clauses in the taxonomy and capabilities `add`
    verbs — so refusing a partial read reports as `tcw <command>: <message>` with
    exit 1 and creates nothing, without a line of new error handling.
    """


def _configured_timeout() -> float:
    """Seconds to wait for the next chunk. A malformed setting must not break
    item creation, so anything unusable falls back to the default."""
    raw = os.environ.get(TIMEOUT_ENV)
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT
    # NaN fails both comparisons, so this also rejects it.
    return value if value >= 0 else DEFAULT_TIMEOUT


def read_piped_stdin(timeout: float | None = None) -> str:
    """Piped intake, or `""` when there is none. Never blocks indefinitely.

    Raises `StdinTruncated` when bytes arrived and then stopped without EOF.
    """
    wait = _configured_timeout() if timeout is None else timeout

    try:
        stdin = sys.stdin
        if stdin is None or stdin.isatty():
            return ""                    # a terminal is never intake
    except (OSError, ValueError):
        return ""

    try:
        fd = stdin.fileno()
    except (OSError, ValueError):
        # No operating-system descriptor, so this cannot be the inherited pipe
        # this module exists to survive — it is an in-memory or synthetic stream
        # (an embedder substituting `io.StringIO`, pytest's captured stdin).
        # Reading it cannot wait on an EOF from another process, so the plain
        # read is both safe and the only thing that works.
        #
        # This is the *only* fallback to a blocking read, and the distinction is
        # exact: a descriptor that exists but cannot be polled is still an OS
        # stream and must never be read this way. Ceiling: a synthetic object
        # that hides a real pipe behind a `read()` and no `fileno()` would still
        # block. Nothing in TCW does that, and no caller can reach it by accident.
        try:
            return stdin.read()
        except (AttributeError, OSError, ValueError):
            return ""     # not readable at all

    chunks = bytearray()
    while True:
        try:
            if not select.select([fd], [], [], wait)[0]:
                break                    # the bound expired
            block = os.read(fd, _CHUNK)
        except (OSError, ValueError):
            # An unusable descriptor. Never retry with a blocking read: a
            # fallback that reintroduces the hang is not a fallback.
            break
        if not block:
            return chunks.decode("utf-8", "replace")     # EOF: the complete end
        chunks += block

    if chunks:
        raise StdinTruncated(
            f"piped input stopped after {len(chunks)} byte(s) without ending — "
            f"refusing to store a truncated intake. If the producer is simply "
            f"slow, raise {TIMEOUT_ENV} (seconds, currently {wait:g}).")
    if wait:                             # 0 is an explicit opt-out, not a mistake
        print(f"tcw: no piped input after {wait:g}s — proceeding without it "
              f"(close stdin, or set {TIMEOUT_ENV} to wait longer)",
              file=sys.stderr)
    return ""
