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
from pathlib import Path

NAME = "project"


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
                               "set that was not used; prints even when something "
                               "is wrong")
    p_config.set_defaults(own_config=True, func=config_cli._show)

    p_provision = command(
        verbs, "provision", help="fetch the stores this project declares but does "
        "not have here",
        prints="nothing; its plan and every remote, before it is contacted, on stderr",
        writes="a clone of each declared store repository that is missing",
        examples=["project provision", "project provision --component work --dry-run"])
    p_provision.add_argument(
        "--component", action="append", choices=list(PROVISION_COMPONENTS),
        help="only this axis's store; repeat for more (default: every declared one)")
    p_provision.add_argument("--dry-run", action="store_true",
                             help="print the plan; contact nothing")
    p_provision.set_defaults(own_config=True, func=_cmd_provision)

    p_path = command(
        verbs, "path", help="the folder a project is in on this machine",
        prints="one absolute folder: the project's root, the folder holding its .tcw/",
        writes="nothing", examples=["project path", "project path core"])
    p_path.add_argument("id", nargs="?", help="the project's ID (default: this project)")
    p_path.set_defaults(func=_path)
