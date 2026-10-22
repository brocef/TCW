"""A project's manifests: where other projects are, by ID (TCW-107 Design 1).

`.tcw/tcw-manifest.yaml` is shared and committed; `.tcw/tcw-manifest.local.yaml`
is personal to this machine. Each maps a project ID to the folder holding that
project's `.tcw/`, optionally with the repository it is fetched from:

    tcw-version: 4.0.0
    projects:
      shared: packages/shared                 # a path alone
      core:
        path: ../core
        repository: https://github.com/example/core.git#release
      server:
        path: ../app/apps/server
        repository: git@github.com:example/app.git
        subfolder: apps/server

An entry says where a project is, and nothing else: listing a project here
does not connect it.

This is the deployment layer of the TCW-99 design: a store that is not a
folder of files has no manifest. The parser reads no file and imports nothing
from `tcw` but `tcw.project_files`; the files store's project registry reads
the files and records the problems.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from tcw.project_files import (LOCAL_MANIFEST, VERSION_KEY, validate_project_id,
                               version_line, version_problem)

_ENTRY_KEYS = ("path", "repository", "subfolder")
_TOP_KEYS = (VERSION_KEY, "projects")


@dataclass(frozen=True)
class ManifestEntry:
    """One project's entry. `path` is as written; `url` and `branch` are the
    two halves of `repository`, split at its first `#`; `file` is the manifest
    holding the entry, as TCW names it in messages."""

    id: str
    path: str
    url: str | None = None
    branch: str | None = None
    subfolder: str | None = None
    file: Any = None

    @property
    def repository(self) -> str | None:
        """The repository as written: `<url>` or `<url>#<branch>`."""
        if self.url is None:
            return None
        return self.url if self.branch is None else f"{self.url}#{self.branch}"


def parse_manifest(mapping: Any, file: Any, *,
                   personal: bool) -> tuple[dict[str, ManifestEntry], list[str]]:
    """The entries of a manifest read as `mapping`, and its problems.

    `mapping` is the parsed YAML (None for an empty file, which has no
    entries). `personal` is true for `tcw-manifest.local.yaml`, the one file
    in which a path may be absolute or start with `~`. **Any problem means no
    entries at all**: a manifest with a problem is not used (Design 1.8). The
    problems do not name the file; the caller records them against it.
    """
    if mapping is None:
        return {}, []
    if not isinstance(mapping, dict):
        return {}, [f"a manifest must be a mapping, got {type(mapping).__name__}"]
    problems: list[str] = []
    if VERSION_KEY not in mapping:
        # `version_problem` reads a missing version as a 3.x file and names
        # `tcw migrate`, but 3.x had no manifests (Design 1.8).
        problems.append(f"has no {VERSION_KEY}; a manifest starts with "
                        f"'{version_line().strip()}'")
    elif (version := version_problem(mapping)) is not None:
        problems.append(version)
    for key in mapping:
        if key not in _TOP_KEYS:
            problems.append(f"unknown key '{key}'; a manifest holds only "
                            f"'{VERSION_KEY}' and 'projects'")
    projects = mapping.get("projects")
    entries: dict[str, ManifestEntry] = {}
    if projects is not None and not isinstance(projects, dict):
        problems.append("projects must be a mapping from project ID to entry")
        projects = None
    for raw_id, raw in (projects or {}).items():
        try:
            project_id = validate_project_id(raw_id if isinstance(raw_id, str) else "")
        except ValueError as error:
            problems.append(f"projects: {raw_id!r}: {error}")
            continue
        entry, entry_problems = _entry(project_id, raw, file, personal=personal)
        problems += [f"projects.{project_id}: {p}" for p in entry_problems]
        if entry is not None:
            entries[project_id] = entry
    if problems:
        return {}, problems
    return entries, []


def _entry(project_id: str, raw: Any, file: Any, *,
           personal: bool) -> tuple[ManifestEntry | None, list[str]]:
    if isinstance(raw, str) or raw is None or not isinstance(raw, dict):
        raw = {"path": raw}
    problems = [f"unknown key '{key}'; an entry holds "
                f"{', '.join(repr(k) for k in _ENTRY_KEYS)}"
                for key in raw if key not in _ENTRY_KEYS]
    path = raw.get("path")
    if not isinstance(path, str) or not path.strip():
        problems.append("needs a path, written as nonempty text: the folder "
                        "holding the project's .tcw/")
        path = None
    elif not personal and (path.startswith(("/", "~", "\\"))
                           or (len(path) > 1 and path[1] == ":")):
        problems.append(f"path {path!r} must be relative to this project's root: "
                        f"this file is shared by every machine; an absolute path "
                        f"or one starting with '~' goes in {LOCAL_MANIFEST}")
    url = branch = None
    if "repository" in raw:
        url, branch, repository_problems = _repository(raw["repository"])
        problems += repository_problems
    subfolder = None
    if "subfolder" in raw:
        subfolder, subfolder_problems = _subfolder(raw["subfolder"], path,
                                                   with_repository="repository" in raw)
        problems += subfolder_problems
    if problems:
        return None, problems
    return ManifestEntry(id=project_id, path=path, url=url, branch=branch,
                         subfolder=subfolder, file=file), []


def _repository(value: Any) -> tuple[str | None, str | None, list[str]]:
    """`<url>` or `<url>#<branch>` split at the first `#` (Design 1.5)."""
    if not isinstance(value, str) or not value.strip():
        return None, None, ["repository must be nonempty text: '<address>' or "
                            "'<address>#<name>'"]
    url, hash_, branch = value.strip().partition("#")
    problems = []
    if not url:
        problems.append(f"repository {value!r}: the address before '#' is empty")
    elif url.startswith("-"):
        problems.append(f"repository {value!r}: the address must not begin with '-'")
    if hash_:
        if not branch:
            problems.append(f"repository {value!r}: the name after '#' is empty")
        elif "#" in branch:
            problems.append(f"repository {value!r}: a second '#'; the name after "
                            f"the first '#' cannot hold another")
        elif any(c.isspace() for c in branch):
            problems.append(f"repository {value!r}: the name after '#' holds a space")
        elif branch.startswith("-"):
            problems.append(f"repository {value!r}: the name after '#' must not "
                            f"begin with '-'")
    if problems:
        return None, None, problems
    return url, (branch if hash_ else None), []


def _subfolder(value: Any, path: str | None, *,
               with_repository: bool) -> tuple[str | None, list[str]]:
    """Where the project sits inside its repository (Design 1.6): relative,
    no `.` or `..` parts, and the last folders of `path`."""
    if not with_repository:
        return None, ["subfolder is where the project sits inside its repository, "
                      "so it needs a repository"]
    text = value.strip().strip("/") if isinstance(value, str) else ""
    if not isinstance(value, str) or value.strip().startswith(("/", "~", "\\")) \
            or not text:
        return None, [f"subfolder {value!r} must be a relative folder inside the "
                      f"repository"]
    parts = text.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None, [f"subfolder {value!r} must not hold '.' or '..' parts"]
    if path is not None and PurePosixPath(path).parts[-len(parts):] != tuple(parts):
        return None, [f"subfolder {text!r} must be how path {path!r} ends: the "
                      f"repository's own folder is path with subfolder removed"]
    return text, []
