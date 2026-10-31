"""Expected identifiers, as TCW 4 prints them (TCW-110).

A test that compares a printed or stored name builds the expected text here,
so the one form `tcw.ids.FullId` prints is written in one place, as
`tests/projectfiles.py` does for where a configuration lives.
"""

from __future__ import annotations

from tcw.ids import FullId


def fid(project: str, namespace: str, id_path: str) -> str:
    """`<project>.<namespace>/<id-path>`."""
    return str(FullId(project, namespace, id_path))


def wid(project: str, folder: str) -> str:
    """A work item's full identifier, `<project>.work/<folder>`."""
    return fid(project, "work", folder)


def addr(project: str, namespace: str, id_path: str) -> str:
    """An object's `tcw://` address."""
    return FullId(project, namespace, id_path).address()
