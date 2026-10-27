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


#: What a run says when Jira fails while planning (Design 2.3, 2.6, 2.7).
NOTHING_WRITTEN = ("nothing was written; 'tcw migrate --no-jira' converts the files "
                   "without Jira")
NOTHING_MORE = ("nothing more was written; 'tcw migrate --no-jira' finishes the files "
                "without Jira")
NOT_LISTED = "the tickets to edit could not be listed"
NOT_CHECKED = "nothing to migrate in the files; the tickets could not be checked"
NOT_CHECKED_NO_JIRA = "nothing to migrate in the files; tickets not checked (--no-jira)"


def run(root: Path, *, dry_run: bool, no_jira: bool) -> int:
    """Migrate the project at `root`; the exit code."""
    from tcw.migrate import progress, report
    try:
        record = progress.load(root)
    except progress.ProgressUnreadable as error:
        report.blockers([_unreadable(error)])
        return codes.REFUSED
    if record is not None:
        return follow_progress(root, record, dry_run=dry_run, no_jira=no_jira)
    from tcw.migrate.plan import make_plan
    plan = make_plan(root, no_jira=no_jira)
    if plan.blockers:
        _would(plan.steps, plan.tickets, root)
        report.reports(plan.reports)
        report.blockers(plan.blockers)
        return codes.REFUSED
    if plan.jira_failure is not None:
        return _planning_failed(plan, dry_run, root)
    if plan.empty:
        report.reports(plan.reports)
        if no_jira and plan.work_backend == "jira":
            report.say(NOT_CHECKED_NO_JIRA)
        else:
            report.say("nothing to migrate")
        return codes.OK
    if dry_run:
        _would(plan.steps, plan.tickets, root)
        report.reports(plan.reports)
        _summary([report.counts(plan.steps, len(plan.tickets), dry=True), *plan.summary,
                  *([report.KNOWN_AFTER] if plan.steps else [])])
        return codes.OK
    code = apply_plan(plan, root) if plan.steps else codes.OK
    after = []
    if code == codes.OK and plan.steps:
        after = _check_after(root, [r.predicts for r in plan.reports if r.predicts],
                             plan.work_backend, no_jira, plan.reports)
    edited: list = []
    if code == codes.OK:
        code = phase_f(plan.half, plan.tickets, edited)
    if code == codes.OK:
        report.reports(plan.reports)
        _summary([report.counts(plan.steps, len(edited), dry=False), *plan.summary,
                  *after])
    return code


def _check_after(root: Path, predicts, work_backend: str, no_jira: bool,
                 reports: list) -> list[str]:
    """The check after the local phases, its A12 reports added to `reports`;
    the summary's lines when the check stopped at a related 3.x project and
    when the work store was left out."""
    from tcw.migrate import execute, report
    work = not (no_jira and work_backend == "jira")
    found, stopped = execute.check_after(root, predicts, work=work)
    reports += found
    return [*([report.CHECK_STOPPED] if stopped else []),
            *([] if work else [report.NOT_CHECKED_WORK])]


def _would(steps, tickets, root: Path | None = None) -> None:
    from tcw.migrate import report
    report.say_steps(steps, dry=True, root=root)
    for edit in tickets:
        report.say(report.ticket_line(edit, dry=True))


def _summary(lines: list[str]) -> None:
    from tcw.migrate import report
    for line in lines:
        report.say(line)


def _planning_failed(plan, dry_run: bool, root: Path) -> int:
    """Jira failed while planning: nothing is written (Design 2.3, 2.6)."""
    from tcw.migrate import report
    error = plan.jira_failure
    _would(plan.steps, [], root)
    report.reports(plan.reports)
    report.say(f"error: {error}")
    if not plan.steps:
        report.say(NOT_CHECKED)
    elif dry_run:
        report.say(NOT_LISTED)
    else:
        report.say(NOTHING_WRITTEN)
    return error.code


def phase_f(half, tickets, edited: list | None = None) -> int:
    """Phase F: the ticket edits, through the function the Jira half
    returned; each edit made is said as it is made. A failure names the
    tickets left, and a run again edits only those (Design 5.3). Each edit
    made is appended to `edited`."""
    from tcw.errors import TcwError
    from tcw.migrate import report
    if half is None or not tickets:
        return codes.OK
    edited = [] if edited is None else edited

    def made(edit) -> None:
        edited.append(edit)
        report.say(report.ticket_line(edit))
    try:
        half.apply(made)
    except TcwError as error:
        left = set(getattr(error, "pending", None) or [t.key for t in tickets])
        report.say(f"stopped: {error}")
        report.say("not done:")
        for edit in tickets:
            if edit.key in left:
                report.say(f"  {report.ticket_line(edit)}")
        report.say(report.RUN_AGAIN)
        return error.code
    return codes.OK


def _unreadable(error) -> "Blocker":
    from tcw.migrate import progress
    from tcw.migrate.model import Blocker
    return Blocker("B17", progress.PROGRESS, str(error).split(" ", 1)[1],
                   f"restore the project from version control, delete "
                   f"{progress.PROGRESS}, and run 'tcw migrate' again")


def _say_once(line: str | None) -> None:
    """Say a step's line; None for a file's later write, said at its first."""
    from tcw.migrate import report
    if line is not None:
        report.say(line)


def apply_plan(plan, root: Path) -> int:
    """Carry out `plan`'s local steps, printing each change as it is made;
    the exit code. A stop says what was not done and how to finish it."""
    from tcw.migrate import execute, report
    try:
        line = report.once(plan.steps, root=root)
        execute.apply(plan, root, lambda step: _say_once(line(step)))
    except execute.MigrateRefused as refused:
        report.blockers([refused.blocker])
        return codes.REFUSED
    except execute.MigrateStopped as stop:
        report.stopped(stop.reason, stop.not_done, root)
        return codes.ERROR
    return codes.OK


def follow_progress(root: Path, record, *, dry_run: bool, no_jira: bool = False) -> int:
    """Finish a run that stopped, from its progress record (Design 2.7). The
    Jira half is planned first, by the function a fresh run uses, with the
    project and backend the record holds; a dry run lists the steps still to
    do and the ticket edits planned."""
    from tcw.errors import TcwError
    from tcw.migrate import execute, report
    from tcw.migrate.plan import no_jira_line, plan_jira_half
    jira_backed = record.work_backend == "jira"
    try:
        half = plan_jira_half(root, record.project, jira_backed=jira_backed,
                              no_jira=no_jira)
    except TcwError as error:
        if dry_run:
            _would(execute.pending(record.steps, root), [], root)
        report.say(f"error: {error}")
        report.say(NOT_LISTED if dry_run else NOTHING_MORE)
        return error.code
    tickets = list(half.tickets) if half is not None else []
    summary = [no_jira_line(root, record.project)] if no_jira and jira_backed else []
    if half is not None and half.blockers:
        _would(execute.pending(record.steps, root), tickets, root)
        report.blockers(half.blockers)
        return codes.REFUSED
    if dry_run and (refused := execute.refusal(record.steps, root)) is not None:
        _would(execute.pending(record.steps, root), tickets, root)
        report.blockers([refused])
        return codes.REFUSED
    if dry_run:
        pending = execute.pending(record.steps, root)
        _would(pending, tickets, root)
        _summary([report.counts(pending, len(tickets), dry=True), *summary,
                  report.KNOWN_AFTER])
        return codes.OK
    done: list = []
    line = report.once(record.steps, root=root)

    def made(step) -> None:
        done.append(step)
        _say_once(line(step))
    try:
        execute.follow(record.steps, root, made)
    except execute.MigrateRefused as refused:
        report.blockers([refused.blocker])
        return codes.REFUSED
    except execute.MigrateStopped as stop:
        report.stopped(stop.reason, stop.not_done, root)
        return codes.ERROR
    reports = list(half.reports) if half is not None else []
    after = _check_after(root, record.predicts, record.work_backend, no_jira, reports)
    edited: list = []
    code = phase_f(half, tickets, edited)
    if code == codes.OK:
        report.reports(reports)
        _summary([report.counts(done, len(edited), dry=False), *summary, *after])
    return code
