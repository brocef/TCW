"""`tcw project` — everything about a project itself, rather than its records
(TCW-115 Design 1): making it (`new`), the projects it is connected to
(`list`), the configuration it runs with (`config`), fetching what it
names but does not have here (`provision`), where a project is on this
machine (`path`), and how this one is assembled (`info`).

The verbs' code stays where it was written: `run_init` and `run_provision` in
`tcw/cli.py`, `connected` and `_list` in `tcw/projects_cli.py`, `render` and
`_show` in `tcw/config_cli.py`. This module only registers them.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

NAME = "project"

#: The settings `info` shows (TCW-115 Design 6.1 (5)); the two `work.jira`
#: keys only in Jira mode.
SETTINGS = ("work.backend", "work.jira.site", "work.jira.project")

#: The axes whose own objects can override an inherited one (Design 6.1 (7)).
TREE_AXES = ("taxonomy", "capabilities")


def _path(args: argparse.Namespace) -> int:
    """`tcw project path [<id>]` (TCW-115 Design 5): the folder of project
    `<id>` on this machine, as every other command here would find it."""
    from tcw import exit as codes
    from tcw.errors import NO_PROJECT, BackendError, UsageError
    from tcw.project_files import validate_project_id
    from tcw.store.fs import find_project_root
    from tcw.store.project import FsProjectRegistry
    if args.id is not None:
        try:
            validate_project_id(args.id)
        except ValueError as error:
            raise UsageError(str(error)) from None
    root = find_project_root(Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    registry = FsProjectRegistry.open(root).require_valid()
    # `project_folder` raises `Unreachable` (exit 5), `UnknownProject` and
    # `ProjectGraphError` (exit 1), each with its own message.
    print(root if args.id is None else registry.project_folder(args.id, root))
    return codes.OK


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw import config_cli, projects_cli
    from tcw.cli import PROVISION_COMPONENTS, _cmd_init, _cmd_provision
    from tcw.cli_help import command, group
    from tcw.store.fs import COMPONENTS
    p = group(sub, NAME, help="everything about this project itself: making it, "
              "where related projects are, how it is assembled")
    verbs = p.add_subparsers(dest="project_verb", required=True)

    p_new = command(
        verbs, "new", help="make this folder a TCW project, or add the named "
        "stores to it",
        prints="nothing", writes=".tcw/tcw-config.yaml, .tcw/.gitignore and each "
        "store's folder, each named on stderr",
        examples=["project new --id my-app",
                  "project new work --id my-app --work-path ../board"])
    p_new.add_argument("components", nargs="*", metavar="axis",
                       help=f"any of: {', '.join(COMPONENTS)} (default: all)")
    p_new.add_argument("--id", help="the project's ID; required for a new project")
    p_new.add_argument("--work-path", help="where the work store lives")
    p_new.add_argument("--taxonomy-path", help="where the taxonomy store lives")
    p_new.add_argument("--capabilities-path", help="where the capabilities store lives")
    p_new.set_defaults(own_config=True, func=_cmd_init)

    p_list = command(verbs, "list", help="this project and its connected projects",
                     prints="one project ID per line, this project first, or --json",
                     writes="nothing", examples=["project list", "project list --json"])
    p_list.add_argument("--json", action="store_true",
                        help="print each project's relation, presence, path, how it "
                             "was found, what a parent passes down ('inherit'), "
                             "whether a child is listed only in the personal file "
                             "('personal'); then 'load-order', 'load-order-complete' "
                             "and 'load-order-warning'")
    p_list.set_defaults(func=projects_cli._list)

    p_config = command(
        verbs, "config",
        help="the effective configuration: TCW's defaults, what the project's "
             "parents pass down, .tcw/tcw-config.yaml, your personal files and "
             "override variables, merged",
        prints="the effective configuration as YAML; with --origin, where each "
               "value came from",
        writes="nothing", examples=["project config", "project config --origin"])
    p_config.add_argument("--origin", action="store_true",
                          help="name the project, the layer and the file or variable "
                               "of every value, and list what your personal files "
                               "set that was not used; prints even when one of the "
                               "project's own files has a problem, but an inherited "
                               "setting a parent cannot give, because it is missing "
                               "or broken, stops it")
    p_config.set_defaults(own_config=True, func=config_cli._show)

    p_provision = command(
        verbs, "provision", help="fetch the stores this project declares, and the "
        "projects its family names, that are not on this machine",
        prints="nothing; its plan and every remote, before it is contacted, on stderr",
        writes="a clone of each missing store and project, where its manifest entry "
               "places it",
        examples=["project provision", "project provision core --dry-run",
                  "project provision --component work"])
    p_provision.add_argument(
        "id", nargs="?", help="only this project and the projects it inherits from "
        "(its load order), and no store")
    p_provision.add_argument(
        "--component", action="append", choices=list(PROVISION_COMPONENTS),
        help="only this axis's store, and no project; repeat for more "
             "(default: every declared one)")
    p_provision.add_argument("--dry-run", action="store_true",
                             help="print the plan; contact nothing")
    p_provision.set_defaults(own_config=True, func=_cmd_provision)

    p_path = command(
        verbs, "path", help="the folder a project is in on this machine",
        prints="one absolute folder: the project's root, the folder holding its .tcw/",
        writes="nothing", examples=["project path", "project path core"])
    p_path.add_argument("id", nargs="?", help="the project's ID (default: this project)")
    p_path.set_defaults(func=_path)

    p_info = command(
        verbs, "info", help="how this project is assembled: its parents, children, "
        "load order, where its settings come from, its stores and its overrides",
        prints="one fact per line, or --json; what is missing is shown, never an error",
        writes="nothing", examples=["project info", "project info --json"])
    p_info.add_argument("--json", action="store_true",
                        help="print the same facts as one JSON document")
    p_info.set_defaults(func=_info)


# -- `tcw project info` (TCW-115 Design 6) ----------------------------------------

@dataclass
class ProjectInfo:
    """Everything `tcw project info` shows about the active project. What is
    missing or unavailable is a value here, never an exception, so the
    command exits 0 for all of it (Design 6.2)."""

    id: str
    path: Path
    parents: list = field(default_factory=list)       # `connected`'s rows
    children: list = field(default_factory=list)      # `connected`'s rows
    order: object = None                              # a `LoadOrder`
    #: Each key of `SETTINGS` shown: `("value", value, origin)`,
    #: `("undecided", message)` or `("broken", message)`.
    settings: dict = field(default_factory=dict)
    #: Each axis: `("path", folder)` or `("unavailable", message)`.
    stores: dict = field(default_factory=dict)
    #: Each of `TREE_AXES`: `("list", [(full id, overridden id)], count)` or
    #: `("unavailable", message)`.
    overrides: dict = field(default_factory=dict)


def _inherit_text(axes: list) -> str:
    from tcw.store.base import AXES
    if list(axes) == list(AXES):
        return "all"
    return ", ".join(axes) if axes else "none"


def store_folder(axis: str, root: Path) -> Path:
    """The folder `tcw <axis> path` prints for the project at `root`, raising
    what that command would raise (plan choice 17)."""
    from tcw.store.fs import STORE_CLASSES, find_component_project, no_store_here
    if axis == "work":
        from tcw.work.open import project_facts
        return project_facts(root).path
    project = find_component_project(axis, root)
    if project is None:
        raise no_store_here(axis, root)
    return STORE_CLASSES[axis].open(project).root


def _setting(config, key: str):
    from tcw.errors import InheritedUnavailable
    from tcw.config import BUILT_IN
    path = tuple(key.split("."))
    held = config.withheld.get(".".join(path[:2])) if path[:2] == ("work", "jira") else None
    if held is not None:
        # Plan choice 15: both `work.jira` lines read the one message the
        # commands that read the key stop with.
        error = held.error()
        kind = "undecided" if isinstance(error, InheritedUnavailable) else "broken"
        return (kind, str(error))
    value = config.values
    for part in path:
        value = value.get(part) if isinstance(value, dict) else None
    if value is None and key == "work.backend":
        from tcw.work.config import DEFAULT_BACKEND
        value = DEFAULT_BACKEND
    return ("value", value, config.origins.get(path, BUILT_IN))


def _overrides(axis: str, root: Path):
    from tcw.errors import TcwError
    from tcw.store.fs import STORE_CLASSES, find_component_project
    try:
        project = find_component_project(axis, root)
    except (TcwError, ValueError) as error:
        return ("unavailable", str(error))
    if project is None:
        return ("list", [], 0)
    try:
        store = STORE_CLASSES[axis].open(project)
        warnings = store.view_warnings()
        found = [(str(obj.full_id), str(obj.overrides))
                 for obj in store.list_all(local_only=True)
                 if getattr(obj, "overrides", None) is not None]
    except (TcwError, ValueError) as error:
        return ("unavailable", str(error))
    return ("list", found, len(warnings))


def project_info(root: Path) -> ProjectInfo:
    from tcw.config import load_config
    from tcw.errors import TcwError
    from tcw.projects_cli import connected
    from tcw.store.fs import COMPONENTS
    from tcw.store.project import FsProjectRegistry
    registry = FsProjectRegistry.open(root).require_valid()
    rows = connected(root, registry)
    info = ProjectInfo(id=rows[0]["id"], path=Path(rows[0]["path"]),
                       parents=[r for r in rows if r["relation"] == "parent"],
                       children=[r for r in rows if r["relation"] == "child"],
                       order=registry.load_order())
    config = load_config(root, registry=registry)
    jira = config.work is not None and config.work.backend == "jira"
    for key in SETTINGS:
        if key == "work.backend" or jira:
            info.settings[key] = _setting(config, key)
    for axis in COMPONENTS:
        try:
            info.stores[axis] = ("path", store_folder(axis, root))
        except (TcwError, ValueError) as error:
            info.stores[axis] = ("unavailable", str(error))
    for axis in TREE_AXES:
        info.overrides[axis] = _overrides(axis, root)
    return info


def render_text(info: ProjectInfo) -> str:
    """Design 6.3's lines, in order."""
    from tcw.config_cli import origin_label
    lines = [f"id: {info.id}", f"path: {info.path}"]

    def listing(label: str, rows: list, notes) -> None:
        if not rows:
            lines.append(f"{label}: none")
            return
        lines.append(f"{label}:")
        for row in rows:
            parts = notes(row) + ([] if row["present"] else ["not on this machine"])
            lines.append(f"  {row['id']}" + (f" ({'; '.join(parts)})" if parts else ""))

    listing("parents", info.parents, lambda r: [f"inherit: {_inherit_text(r['inherit'])}"])
    listing("children", info.children, lambda r: ["personal"] if r["personal"] else [])
    order = info.order
    lines.append(f"load order: {', '.join(order.ids)}")
    if not order.complete:
        parts = []
        if order.missing:
            parts.append(f"not on this machine: {', '.join(order.missing)}")
        if order.unreadable:
            parts.append(f"links unreadable: {', '.join(order.unreadable)}")
        lines.append(f"load order incomplete: {'; '.join(parts)}")
    if order.warning:
        lines.append(f"load order warning: {order.warning}")
    lines.append("settings:")
    for key, shown in info.settings.items():
        if shown[0] == "value":
            _, value, origin = shown
            label = origin_label(origin, info.path, info.id)
            if origin.layer != "built-in" and (origin.project or info.id) != info.id:
                label += "; inherited"
            lines.append(f"  {key}: {value} ({label})")
        else:
            lines.append(f"  {key}: {shown[0]}: {shown[1]}")
    lines.append("stores:")
    for axis, (_, where) in info.stores.items():
        lines.append(f"  {axis}: {where}")
    lines.append("overrides:")
    counts = []
    for axis, shown in info.overrides.items():
        if shown[0] == "unavailable":
            lines.append(f"  {axis}: could not check: {shown[1]}")
            counts.append(f"{axis} ?")
            continue
        _, found, count = shown
        counts.append(f"{axis} {count}")
        if not found:
            lines.append(f"  {axis}: none")
            continue
        lines.append(f"  {axis}:")
        lines += [f"    {full_id} overrides {overridden}" for full_id, overridden in found]
    lines.append(f"same path in two unrelated projects: {', '.join(counts)}")
    return "\n".join(lines) + "\n"


def render_json(info: ProjectInfo) -> dict:
    """Design 6.4's document, under `project`."""
    from tcw.config_cli import origin_json
    settings = {}
    for key, shown in info.settings.items():
        if shown[0] == "value":
            _, value, origin = shown
            settings[key] = {"value": value, "origin": origin_json(origin, info.id),
                             "inherited": origin.layer != "built-in"
                             and (origin.project or info.id) != info.id}
        else:
            settings[key] = {shown[0]: shown[1]}
    overrides, counts = {}, {}
    for axis, shown in info.overrides.items():
        if shown[0] == "unavailable":
            overrides[axis], counts[axis] = {"unavailable": shown[1]}, None
        else:
            overrides[axis] = [{"id": full_id, "overrides": overridden}
                               for full_id, overridden in shown[1]]
            counts[axis] = shown[2]
    order = info.order
    return {
        "id": info.id, "path": str(info.path),
        "parents": [{"id": r["id"], "inherit": r["inherit"], "present": r["present"],
                     "path": r["path"]} for r in info.parents],
        "children": [{"id": r["id"], "personal": r["personal"], "present": r["present"],
                      "path": r["path"]} for r in info.children],
        "load-order": list(order.ids), "load-order-complete": order.complete,
        "load-order-missing": list(order.missing),
        "load-order-unreadable": list(order.unreadable),
        "load-order-warning": order.warning,
        "settings": settings,
        "stores": {axis: {"path": str(where)} if kind == "path" else {"unavailable": where}
                   for axis, (kind, where) in info.stores.items()},
        "overrides": overrides,
        "same-path-warnings": counts,
    }


def _info(args: argparse.Namespace) -> int:
    import sys
    from tcw import exit as codes
    from tcw.errors import NO_PROJECT, BackendError
    from tcw.store.fs import find_project_root
    root = find_project_root(Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    info = project_info(root)
    if args.json:
        from tcw.output import print_json
        print_json("project", render_json(info))
    else:
        sys.stdout.write(render_text(info))
    return codes.OK
