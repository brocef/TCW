"""The `tcw migrate` command (TCW-116 Design 1): its form, and which project
it runs in.

`migrate` is exempt from every check `_dispatch` makes before a command
(Design 1.2), because those checks read exactly the files that are its
input: `skips_checks` tells `_dispatch` to leave them out.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tcw import exit as codes

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
    from tcw.migrate import progress, report
    try:
        record = progress.load(root)
    except progress.ProgressUnreadable as error:
        report.blockers([_unreadable(error)])
        return codes.REFUSED
    if record is not None:
        return follow_progress(root, record, dry_run=dry_run)
    report.say("nothing to migrate")
    return codes.OK


def _unreadable(error) -> "Blocker":
    from tcw.migrate import progress
    from tcw.migrate.model import Blocker
    return Blocker("B17", progress.PROGRESS, str(error).split(" ", 1)[1],
                   f"restore the project from version control, delete "
                   f"{progress.PROGRESS}, and run 'tcw migrate' again")


def apply_plan(plan, root: Path) -> int:
    """Carry out `plan`'s local steps, printing each change as it is made;
    the exit code. A stop says what was not done and how to finish it."""
    from tcw.migrate import execute, report
    try:
        execute.apply(plan, root, lambda step: report.say(report.step_line(step)))
    except execute.MigrateRefused as refused:
        report.blockers([refused.blocker])
        return codes.REFUSED
    except execute.MigrateStopped as stop:
        report.stopped(stop.reason, stop.not_done)
        return codes.ERROR
    return codes.OK


def follow_progress(root: Path, record, *, dry_run: bool) -> int:
    """Finish a run that stopped, from its progress record (Design 2.7); a dry
    run lists the steps still to do."""
    from tcw.migrate import execute, report
    if dry_run:
        for step in execute.pending(record.steps, root):
            report.say(report.step_line(step, dry=True))
        return codes.OK
    try:
        execute.follow(record.steps, root, lambda step: report.say(report.step_line(step)))
    except execute.MigrateRefused as refused:
        report.blockers([refused.blocker])
        return codes.REFUSED
    except execute.MigrateStopped as stop:
        report.stopped(stop.reason, stop.not_done)
        return codes.ERROR
    return codes.OK
