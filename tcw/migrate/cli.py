"""The `tcw migrate` command (TCW-116 Design 1): its form, and which project
it runs in.

`migrate` is exempt from every check `_dispatch` makes before a command
(Design 1.2), because those checks read exactly the files that are its
input: `skips_checks` tells `_dispatch` to leave them out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

NAME = "migrate"


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw.cli_help import command
    p = command(
        sub, NAME, help="move a TCW 3.x project to TCW 4",
        description="move the TCW 3.x project in this folder to TCW 4: its "
        "configuration, its stores' files and, when its work is kept in Jira, "
        "the TCW Item of its tickets",
        prints="nothing; every change, report and blocker on stderr",
        writes="the active project's files and its tickets' TCW Item",
        examples=["migrate --dry-run", "migrate --no-jira", "migrate"])
    p.add_argument("--dry-run", action="store_true",
                   help="say what would change, and change nothing")
    p.add_argument("--no-jira", action="store_true",
                   help="convert the files only; never contact Jira")
    p.set_defaults(skips_checks=True, func=_cmd_migrate)


def _cmd_migrate(args: argparse.Namespace) -> int:
    from tcw.errors import NO_PROJECT, BackendError
    from tcw.project_files import find_marker
    found = find_marker()
    if found is None:
        raise BackendError(NO_PROJECT)
    return run(found[0], dry_run=args.dry_run, no_jira=args.no_jira)


def run(root: Path, *, dry_run: bool, no_jira: bool) -> int:
    """Migrate the project at `root`; the exit code."""
    print("nothing to migrate", file=sys.stderr)
    return 0
