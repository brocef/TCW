"""YAML text that remembers which file it came from."""

from __future__ import annotations

import io
from pathlib import Path


def named(text: str, path: Path | str) -> io.StringIO:
    """`text` as a stream PyYAML reports under `path`'s name.

    Handed a plain string, PyYAML calls it `"<unicode string>"` in every error
    position, so a syntax error names no file. A stream's `name` is used instead.
    The text is still read by the caller, so decoding is exactly what it was."""
    stream = io.StringIO(text)
    stream.name = str(path)
    return stream
