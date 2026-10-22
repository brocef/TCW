"""A TCW project's own files, and the rules every `tcw-*.yaml` file follows
(TCW-106).

A project is a folder holding `.tcw/tcw-config.yaml`; the folder holding
`.tcw/` is the project root, and every path in the configuration is read from
there, not from `.tcw/`. A TCW 3.x project instead has `tcw-config.yaml` at
its root, and is recognised only to be refused.

Every `tcw-*.yaml` file records, in `tcw-version`, the version of the TCW that
created it or last migrated it, so a reader knows which format it follows.
`version_problem` is the one check every reader calls.

Every configuration key, like a project ID, is lowercase letters and digits
joined by single hyphens, so that every key has one environment-variable name
(TCW-99 design, "Personal overrides and environment variables").

This is the deployment layer of the TCW-99 design: how a folder of files is
recognised as a project. It imports nothing from `tcw` but the version, so
every module can use it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

from tcw import __version__

TCW_FOLDER = ".tcw"
CONFIG_NAME = "tcw-config.yaml"
LOCAL_CONFIG_NAME = "tcw-config.local.yaml"
#: Relative to a project root: `root / SENTINEL` is the configuration file.
SENTINEL = f"{TCW_FOLDER}/{CONFIG_NAME}"
LOCAL_SENTINEL = f"{TCW_FOLDER}/{LOCAL_CONFIG_NAME}"
#: Where a TCW 3.x project keeps its configuration, at its root.
LEGACY_SENTINEL = CONFIG_NAME

VERSION_KEY = "tcw-version"
_VERSION = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")

KEY_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_KEY_RULE = "lowercase letters and digits joined by single hyphens"
#: Keys renamed to follow the rule, and what to write instead.
_RENAMED_KEYS = {"not_tags": "not-tags"}

V4 = "4"
V3 = "3"


def config_path(root: Path) -> Path:
    return Path(root) / SENTINEL


def local_config_path(root: Path) -> Path:
    return Path(root) / LOCAL_SENTINEL


def root_of(path: Path) -> Path:
    """The project root for a path to a file in its `.tcw/` folder."""
    return Path(path).parent.parent


def find_marker(start: Path | None = None) -> tuple[Path, str] | None:
    """The nearest folder, `start` included, that marks a project, and which
    kind: `V4` for one holding `.tcw/tcw-config.yaml`, `V3` for one holding
    only a root `tcw-config.yaml`. None when no folder up to the filesystem
    root does.

    A folder named `.tcw` is never a 3.x project: it is a 4.0 project's own
    folder, holding its `tcw-config.yaml`, and the walk goes on to its parent.
    `start` is resolved first, so a symlinked folder walks the real path.
    """
    d = (start or Path.cwd()).resolve()
    while True:
        if (d / SENTINEL).is_file():
            return d, V4
        if d.name != TCW_FOLDER and (d / LEGACY_SENTINEL).is_file():
            return d, V3
        if d == d.parent:
            return None
        d = d.parent


def legacy_message(folder: Path) -> str:
    return (f"{folder} is a TCW 3.x project ({LEGACY_SENTINEL} at its root, no "
            f"{TCW_FOLDER}/ folder); run 'tcw migrate' in it to move it to TCW 4")


# ---------------------------------------------------------------------------
# The version every `tcw-*.yaml` file records


def version_line() -> str:
    """The line TCW writes first in every `tcw-*.yaml` file it creates."""
    return f"{VERSION_KEY}: {__version__}\n"


def _pair(version: str) -> tuple[int, int]:
    major, minor, *_ = version.split(".")
    return int(major), int(minor)


def version_problem(mapping: Any) -> str | None:
    """What is wrong with the `tcw-version` of a file read as `mapping`, or
    None when this TCW reads its format. The first that applies of: missing
    (read as a 3.x file), not a version written as text, older than 4, and
    newer than this TCW (major and minor compared as a pair; the patch number
    never changes a format)."""
    if not isinstance(mapping, dict) or VERSION_KEY not in mapping:
        return (f"has no {VERSION_KEY}, so it is read as a TCW 3.x file; run "
                f"'tcw migrate' in this project (a file written by hand for TCW 4 "
                f"starts with '{version_line().strip()}')")
    value = mapping[VERSION_KEY]
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        return f"{VERSION_KEY} must be a TCW version written as text, such as '{__version__}'"
    major, minor = _pair(value)
    if major < 4:
        return (f"{VERSION_KEY} {value} is in the format of TCW {major}.{minor}; run "
                f"'tcw migrate' in this project")
    if (major, minor) > _pair(__version__):
        return (f"was written by TCW {major}.{minor} ({VERSION_KEY} {value}), newer "
                f"than this TCW ({__version__}); upgrade TCW")
    return None


def without_version(mapping: dict) -> dict:
    """`mapping` without its `tcw-version`: file information, not
    configuration, so it is never merged or shown."""
    return {k: v for k, v in mapping.items() if k != VERSION_KEY}


# ---------------------------------------------------------------------------
# The naming rule


def key_problems(value: Any, path: tuple = ()) -> list[tuple[tuple, str]]:
    """Every mapping key under `value` that breaks the naming rule, with its
    key path, list entries included. Values are not checked."""
    return list(_key_problems(value, path))


def _key_problems(value: Any, path: tuple) -> Iterator[tuple[tuple, str]]:
    if isinstance(value, dict):
        for key, inner in value.items():
            here = (*path, key)
            if not isinstance(key, str):
                yield here, f"key {key!r} must be text: {_KEY_RULE}"
            elif not KEY_PATTERN.fullmatch(key):
                message = f"key '{key}' must be {_KEY_RULE}"
                if key in _RENAMED_KEYS:
                    message += f"; write '{_RENAMED_KEYS[key]}'"
                yield here, message
            yield from _key_problems(inner, here)
    elif isinstance(value, list):
        for i, entry in enumerate(value):
            yield from _key_problems(entry, (*path, i))
