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


def left_out(unreadable: dict) -> int:
    """After a listing, each object it left out because its state file's
    version cannot be read, one `<file>: <problem>` line on stderr, and the
    exit code: 1 when there was one (TCW-111 Design 1.5), else 0."""
    for path, problem in sorted(unreadable.items()):
        say(f"{shown(path)}: {problem}")
    return 1 if unreadable else 0


def own_only_line(error: Exception, project_id: str) -> str:
    """The one line a reader prints when it shows a project's own objects
    without their inherited content (TCW-112 Design 3.4)."""
    return f"warning: {error}; showing only '{project_id}''s own declarations"


def own_only(error: Exception, project_id: str) -> None:
    say(own_only_line(error, project_id))


def print_json(key: str | None, value: Any) -> None:
    """Exactly one JSON object on stdout with `"schema": 2` first: `value`
    under `key`, or `value`'s own keys when `key` is None (Design 1.6).

    Schema 2 is TCW 4's: every record names its object by `full-id` and
    `owner` (TCW-110 Design 4.3)."""
    document: dict[str, Any] = {"schema": 2}
    if key is None:
        document.update(value)
    else:
        document[key] = value
    print(json.dumps(document, indent=2))
