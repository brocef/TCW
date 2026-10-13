"""How every `tcw` command shapes what it prints (TCW-73 Design 1).

stdout carries a command's product and nothing else; everything said to a
person goes to stderr through `say`. A file a command writes or removes is
named on stderr, one line each, with the path as `shown` gives it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def say(line: str) -> None:
    """One line of narration on stderr."""
    print(line, file=sys.stderr)


def shown(path: str | os.PathLike) -> str:
    """`path` relative to the current directory when it is inside it, else
    absolute."""
    path = Path(path)
    absolute = path if path.is_absolute() else Path.cwd() / path
    try:
        return str(absolute.relative_to(Path.cwd()))
    except ValueError:
        return str(absolute)


def wrote(path: str | os.PathLike) -> None:
    say(f"wrote {shown(path)}")


def removed(path: str | os.PathLike) -> None:
    say(f"removed {shown(path)}")


def created(path: str | os.PathLike) -> None:
    """A folder created empty."""
    say(f"created {shown(path).rstrip('/')}/")


def changed(lines: list[tuple[str, Path]]) -> None:
    """Each `(verb, path)` a store recorded, as `wrote`, `removed` or
    `created` lines."""
    for verb, path in lines:
        {"wrote": wrote, "removed": removed, "created": created}[verb](path)


def print_json(key: str | None, value: Any) -> None:
    """Exactly one JSON object on stdout with `"schema": 1` first: `value`
    under `key`, or `value`'s own keys when `key` is None (Design 1.6)."""
    document: dict[str, Any] = {"schema": 1}
    if key is None:
        document.update(value)
    else:
        document[key] = value
    print(json.dumps(document, indent=2))
