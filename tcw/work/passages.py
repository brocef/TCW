"""Backend passages: text in a prompt or procedure meant for one backend only
(TCW-74 Design 3).

A passage opens with a line holding exactly `<!-- backend: <name> -->` and
closes with a line holding exactly `<!-- /backend -->`. For the project's
backend the two marker lines are removed and the passage kept; for any other
backend the marker lines and the passage are both removed. Text outside every
passage is kept for every backend.

With no backend at all (outside a TCW project) every passage is removed, so
text meant for every situation has to sit outside passages.

The filter keys on the backend's name, not on how the backend stores
anything, so a third backend gets passages of its own without a change here.
"""

from __future__ import annotations

import re

from tcw.errors import BackendError

BACKEND_OPEN = re.compile(r"^<!-- backend: (?P<name>\S+) -->$")
BACKEND_CLOSE = "<!-- /backend -->"


def filter_backend(text: str, backend: str | None) -> str:
    """`text` with each passage kept or removed for `backend`.

    Raises `BackendError` (exit 1) for an unknown backend name, a passage
    inside another, a passage never closed, and a closing marker with no
    passage open, naming the line. A marker is recognised only as a whole
    line, after surrounding spaces are stripped, so a marker quoted inside a
    sentence is left alone. A whole line that starts with `<!--` and mentions
    `backend` but is neither marker exactly is a misspelled marker, and an
    error too: otherwise a misspelled pair would pass silently and reach every
    backend as an HTML comment.
    """
    from tcw.work.config import BACKENDS
    kept: list[str] = []
    inside: str | None = None
    opened_at = 0
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        marker = line.strip()
        opening = BACKEND_OPEN.match(marker)
        if opening:
            name = opening.group("name")
            if name not in BACKENDS:
                raise BackendError(
                    f"line {number}: unknown backend '{name}' in a passage "
                    f"marker; expected one of {', '.join(BACKENDS)}")
            if inside is not None:
                raise BackendError(
                    f"line {number}: a backend passage opens inside the one "
                    f"opened at line {opened_at}; close that one first")
            inside, opened_at = name, number
            continue
        if marker == BACKEND_CLOSE:
            if inside is None:
                raise BackendError(
                    f"line {number}: `{BACKEND_CLOSE}` closes no open backend "
                    f"passage")
            inside = None
            continue
        if marker.startswith("<!--") and "backend" in marker.lower():
            raise BackendError(
                f"line {number}: `{marker}` looks like a backend passage marker "
                f"but is neither `<!-- backend: <name> -->` nor "
                f"`{BACKEND_CLOSE}` exactly")
        if inside is None or inside == backend:
            kept.append(line)
    if inside is not None:
        raise BackendError(
            f"line {opened_at}: the backend passage opened here is never "
            f"closed with `{BACKEND_CLOSE}`")
    return "".join(kept)
