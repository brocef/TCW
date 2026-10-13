"""`tcw projects` — the projects this one is connected to (TCW-73 Design 2).

`tcw projects list` replaces the 2.8 command that listed parent and child
projects: one project ID per line, this project first, then its parent, its
children and the upstream projects it may read, each once, whether or not it
is on this machine.
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
    prints them, each as `{id, relation, present, path}`."""
    from tcw.store.project import FsProjectRegistry
    registry = FsProjectRegistry.open(root)
    here = registry.current
    rows = [{"id": here.id, "relation": "current", "present": True,
             "path": str(here.locator)}]
    seen = {here.id}

    def add(project_id: str | None, relation: str) -> None:
        if project_id is None or project_id in seen:
            return
        seen.add(project_id)
        project = registry.get(project_id)
        rows.append({"id": project_id, "relation": relation,
                     "present": project is not None,
                     "path": str(project.locator) if project is not None else None})

    add(registry.declared_parent_id(), "parent")
    for child in registry.declared_child_ids():
        add(child, "child")
    # An upstream declared by an ancestor is readable from here too, as the
    # registry reads it (`FsProjectRegistry.declared_upstream_ids`).
    for declarer in [here.id, *(a.id for a in registry.ancestors(here.id))]:
        for upstream in registry.declared_upstream_ids(declarer):
            add(upstream, "upstream")
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
                   help="print each project's relation, presence and path")
    p.set_defaults(func=_list)
