"""Writing a fixture project's configuration where TCW 4 reads it (TCW-106).

A project's configuration is `<root>/.tcw/tcw-config.yaml` and its personal
file `<root>/.tcw/tcw-config.local.yaml`, and each starts with the version of
the TCW that wrote it. A fixture that wrote `<root>/tcw-config.yaml` now calls
one of these.

**The version line is added only to text that is a mapping** (or empty, or
only comments): a
test writing a deliberately broken file, a list, or bytes that are not UTF-8
gets exactly what it wrote, so it still tests the failure it names. A text
that already holds a `tcw-version` line is written unchanged, so a test of a
wrong version controls it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tcw.project_files import (CONFIG_NAME, LOCAL_CONFIG_NAME, TCW_FOLDER,
                               VERSION_KEY, version_line)

_CONFIG_NAMES = (CONFIG_NAME, LOCAL_CONFIG_NAME)


def config_file(root) -> Path:
    """`<root>/.tcw/tcw-config.yaml`, with its folder made."""
    folder = Path(root) / TCW_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder / CONFIG_NAME


def local_config_file(root) -> Path:
    """`<root>/.tcw/tcw-config.local.yaml`, with its folder made."""
    folder = Path(root) / TCW_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder / LOCAL_CONFIG_NAME


def _versioned(data):
    """`data` with the version line in front, when it is a mapping's text."""
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return data
        out = _versioned(text)
        return out.encode("utf-8") if isinstance(out, str) else out
    try:
        parsed = yaml.safe_load(data)
    except yaml.YAMLError:
        return data
    if parsed is None or (isinstance(parsed, dict) and VERSION_KEY not in parsed):
        # A null document such as `---` or `~` cannot take a line in front and
        # stay one mapping; it is written as it is, a file with no version.
        try:
            joined = yaml.safe_load(version_line() + data)
        except yaml.YAMLError:
            return data
        return version_line() + data if isinstance(joined, dict) else data
    return data


def write_config_file(path, data="", encoding: str | None = "utf-8", **_) -> Path:
    """Write `data` to `path`; when `path` is a configuration file, with the
    version line in front as the module says."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.name in _CONFIG_NAMES:
        data = _versioned(data)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding=encoding or "utf-8")
    return path


def write_config(root, data="", encoding: str | None = "utf-8", **kw) -> Path:
    """Write a project's `.tcw/tcw-config.yaml`."""
    return write_config_file(config_file(root), data, encoding, **kw)


def write_local_config(root, data="", encoding: str | None = "utf-8", **kw) -> Path:
    """Write a project's `.tcw/tcw-config.local.yaml`."""
    return write_config_file(local_config_file(root), data, encoding, **kw)
