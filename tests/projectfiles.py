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
wrong version controls it. The two manifest files (TCW-107) follow the same
rule.

**Where another project is goes in a manifest** (TCW-107 Design 3), not under
`projects:`. `write_manifest` writes one; `write_connected_config` writes a
configuration that may still hold 3.x locations under `projects:`, moving each
into the root's shared manifest, so a test converted from 3.x says at its call
site that its locations are now in a manifest.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from tcw.project_files import (CONFIG_NAME, LOCAL_CONFIG_NAME, LOCAL_MANIFEST_NAME,
                               MANIFEST_NAME, TCW_FOLDER, VERSION_KEY, version_line)

_CONFIG_NAMES = (CONFIG_NAME, LOCAL_CONFIG_NAME, MANIFEST_NAME, LOCAL_MANIFEST_NAME)


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


def manifest_file(root, *, local: bool = False) -> Path:
    """`<root>/.tcw/tcw-manifest.yaml`, or the `.local` one, with its folder
    made."""
    folder = Path(root) / TCW_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder / (LOCAL_MANIFEST_NAME if local else MANIFEST_NAME)


def write_manifest(root, entries, *, local: bool = False) -> Path:
    """Write a project's manifest. `entries` as a mapping is written under
    `projects:` and merged into a manifest already there; as text it is
    written as given, with the version line added by the module's rule, so a
    test of a broken manifest still tests that file."""
    path = manifest_file(root, local=local)
    if isinstance(entries, (str, bytes)):
        return write_config_file(path, entries)
    document = {}
    if path.is_file():
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    projects = {**(document.get("projects") or {}), **entries}
    body = {k: v for k, v in document.items() if k != VERSION_KEY}
    body["projects"] = projects
    return write_config_file(path, yaml.safe_dump(body, sort_keys=False))


def _moved(root: Path, raw) -> tuple[dict, dict] | None:
    """`raw`'s `projects:` with every location taken out, and the manifest
    entries they become; None when there is nothing to move."""
    if not isinstance(raw, dict) or not isinstance(raw.get("projects"), dict):
        return None
    entries = {}
    projects = {}
    for relation, section in raw["projects"].items():
        if not isinstance(section, dict):
            projects[relation] = section
            continue
        kept = {}
        for project_id, entry in section.items():
            moved = _location(root, project_id, entry)
            if moved is None:
                kept[project_id] = entry
                continue
            entries[project_id], kept[project_id] = moved
        projects[relation] = kept
    if not entries:
        return None
    return {**raw, "projects": projects}, entries


def _location(root: Path, project_id, entry):
    """`(manifest entry, what the configuration keeps)` for one 3.x entry, or
    None when it holds no location."""
    if isinstance(entry, str):
        return _relative(root, entry), None
    if not isinstance(entry, dict) or not ({"path", "repository"} & set(entry)):
        return None
    repository = entry.get("repository")
    if "path" not in entry or (isinstance(repository, dict) and "checkout" in repository):
        raise AssertionError(
            f"projects entry {project_id!r} gives a repository and no path, or a "
            f"repository.checkout: 3.x found such a project in its cache, so the "
            f"test must be converted by hand")
    moved = {"path": _relative(root, entry["path"])}
    if isinstance(repository, dict):
        url = repository.get("url")
        moved["repository"] = f"{url}#{repository['ref']}" if repository.get("ref") else url
        if repository.get("path"):
            moved["subfolder"] = repository["path"]
    elif repository is not None:
        moved["repository"] = repository
    kept = {k: v for k, v in entry.items() if k not in ("path", "repository")} or None
    return (moved if len(moved) > 1 else moved["path"]), kept


def _relative(root: Path, locator):
    if isinstance(locator, str) and os.path.isabs(locator):
        return os.path.relpath(locator, root)
    return locator


def write_connected_config_file(path, data="", encoding: str | None = "utf-8",
                                **kw) -> Path:
    """`write_config_file`, for a `.tcw/tcw-config.yaml` that may still give
    other projects' locations under `projects:`: each location moves into the
    root's shared manifest (a locator as its `path`, an absolute one made
    relative to the root; `repository: {url, ref, path}` as `repository:
    <url>#<ref>` and `subfolder: <path>`), and the configuration keeps the ID
    (and any `jira` block). Re-written through YAML only when something moved.

    TCW-108 replaces `projects:` and will retire this helper."""
    path = Path(path)
    if path.name == CONFIG_NAME and path.parent.name == TCW_FOLDER \
            and isinstance(data, str):
        try:
            raw = yaml.safe_load(data)
        except yaml.YAMLError:
            raw = None
        root = path.parent.parent
        moved = _moved(root, raw)
        if moved is not None:
            config, entries = moved
            write_manifest(root, entries)
            data = yaml.safe_dump(config, sort_keys=False)
    return write_config_file(path, data, encoding, **kw)


def write_connected_config(root, data="", encoding: str | None = "utf-8", **kw) -> Path:
    """`write_config`, moving 3.x locations into a manifest as
    `write_connected_config_file` does."""
    return write_connected_config_file(config_file(root), data, encoding, **kw)
