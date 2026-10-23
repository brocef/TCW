"""`tcw projects` — the projects this one is connected to (TCW-73 Design 2).

`tcw projects list` prints one project ID per line: this project first, then
its parents in listing order, then its children (TCW-108 Design 8.1), each
once, whether or not it is on this machine.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tcw import exit as codes
from tcw.errors import NO_PROJECT, BackendError
from tcw.output import print_json

NAME = "projects"


def connected(root: Path) -> list[dict]:
    """This project and the ones it is connected to, in the order `list`
    prints them, each as `{id, relation, present, path, found}`; `found` says
    how TCW found a project on this machine other than this one (TCW-107
    Design 6.1), and is None for this one and for one not here."""
    from tcw.store.project import FsProjectRegistry
    # A registry problem — an invalid ID, a listed child that does not name
    # this project back — is an error, as `validate` reports it, never a project
    # quietly left off the list.
    registry = FsProjectRegistry.open(root).require_valid()
    here = registry.current
    rows = [{"id": here.id, "relation": "current", "present": True,
             "path": str(here.locator), "found": None}]
    seen = {here.id}

    def add(project_id: str | None, relation: str) -> None:
        if project_id is None or project_id in seen:
            return
        seen.add(project_id)
        project = registry.get(project_id)
        rows.append({"id": project_id, "relation": relation,
                     "present": project is not None,
                     "path": str(project.locator) if project is not None else None,
                     "found": registry.found(project_id)})

    for link in registry.parents():
        add(link.id, "parent")
    for child in registry.declared_child_ids():
        add(child, "child")
    return rows


def _list(args: argparse.Namespace) -> int:
    from tcw.store.fs import find_project_root
    root = find_project_root(Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    rows = connected(root)
    if args.json:
        print_json("projects", rows)
        return codes.OK
    for row in rows:
        print(row["id"])
    return codes.OK


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw.cli_help import command, group
    p = group(sub, NAME, help="the projects this one is connected to")
    verbs = p.add_subparsers(dest="projects_verb", required=True)
    p = command(verbs, "list", help="this project and its connected projects",
                prints="one project ID per line, this project first, or --json",
                writes="nothing", examples=["projects list", "projects list --json"])
    p.add_argument("--json", action="store_true",
                   help="print each project's relation, presence, path, and how "
                        "it was found")
    p.set_defaults(func=_list)
