"""The files store's reading of a project's `parents:` and `children:`
(TCW-108 Design 1 and 2).

Each function takes a value already parsed from YAML and returns what it
holds and the problems found, as `(key path, message)` pairs; it reads no
file. Whose problem each one is depends on the project's place in the walk,
which only the registry knows, so nothing here decides it.
"""

from __future__ import annotations

from typing import Any

from tcw.project_files import validate_project_id
from tcw.store.base import AXES, ParentLink

_ENTRY_KEYS = ("id", "inherit")


def parse_parents(value: Any, file: str) -> tuple[list[ParentLink] | None,
                                                    list[tuple[str, str]]]:
    """The links of a `parents:` value, in order, and its problems.

    None for the links when the key is absent, and when there is any problem:
    a list read only in part would place the project in another load order
    than the one its file states, so its parents are unknown instead
    (Design 6.6). `file` is the file the value was read from, named in no
    message here; the caller adds it."""
    if value is None:
        return None, []
    if not isinstance(value, list):
        return None, [("parents", "must be a list of parents, each a project ID or a "
                                  "mapping with 'id' and optional 'inherit'")]
    found: list[ParentLink] = []
    problems: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        key = f"parents[{index}]"
        link = _parent(entry, key, problems)
        if link is None:
            continue
        if link.id in seen:
            problems.append((key, f"'{link.id}' is listed twice"))
            continue
        seen.add(link.id)
        found.append(link)
    return (None if problems else found), problems


def _parent(entry: Any, key: str, problems: list) -> ParentLink | None:
    if isinstance(entry, str):
        project_id = _project_id(entry, key, problems)
        return None if project_id is None else ParentLink(project_id)
    if not isinstance(entry, dict):
        problems.append((key, "must be a project ID or a mapping with 'id' and "
                              "optional 'inherit'"))
        return None
    unknown = [k for k in entry if k not in _ENTRY_KEYS]
    if unknown:
        problems.append((key, f"unknown key '{unknown[0]}'; an entry holds only "
                              f"'id' and 'inherit'"))
        return None
    if "id" not in entry:
        problems.append((f"{key}.id", "is required"))
        return None
    if not isinstance(entry["id"], str):
        problems.append((f"{key}.id", "must be a project ID"))
        return None
    project_id = _project_id(entry["id"], f"{key}.id", problems)
    if project_id is None:
        return None
    inherit = _inherit(entry.get("inherit", "all"), f"{key}.inherit", problems)
    return None if inherit is None else ParentLink(project_id, inherit)


def _inherit(value: Any, key: str, problems: list) -> frozenset | None:
    """Design 1.2: `all`, `none`, or a non-empty list of distinct axes."""
    if value == "all":
        return frozenset(AXES)
    if value == "none":
        return frozenset()
    if not isinstance(value, list):
        problems.append((key, f"must be 'all', 'none' or a list drawn from "
                              f"{', '.join(AXES)}"))
        return None
    if not value:
        problems.append((key, "an empty list passes nothing: write 'inherit: none'"))
        return None
    axes: set[str] = set()
    for axis in value:
        if axis not in AXES:
            problems.append((key, f"'{axis}' is not one of {', '.join(AXES)}"))
            return None
        if axis in axes:
            problems.append((key, f"'{axis}' is listed more than once"))
            return None
        axes.add(axis)
    return frozenset(axes)


def parse_children(value: Any, file: str, *, own_id: str) -> tuple[list[str],
                                                                   list[tuple[str, str]]]:
    """The IDs of a `children:` value, in order, and its problems. An entry
    that is not a valid project ID, a repeat, and the project's own ID are
    left out, each with a problem (Design 2.1)."""
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], [("children", "must be a list of project IDs")]
    found: list[str] = []
    problems: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        key = f"children[{index}]"
        if not isinstance(entry, str):
            problems.append((key, "must be a project ID"))
            continue
        project_id = _project_id(entry, key, problems)
        if project_id is None:
            continue
        if project_id == own_id:
            problems.append((key, f"'{own_id}' lists itself as a child"))
        elif project_id in found:
            problems.append((key, f"'{project_id}' is listed twice"))
        else:
            found.append(project_id)
    return found, problems


def _project_id(text: str, key: str, problems: list) -> str | None:
    try:
        return validate_project_id(text)
    except ValueError as error:
        problems.append((key, str(error)))
        return None
