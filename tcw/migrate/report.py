"""The lines `tcw migrate` prints (TCW-116 Design 1.5, 2.9, 2.10; Decided 14).

Every line goes to standard error. A change line names its file or ticket,
its action and its conversions, and a dry run puts `would ` first:

    write <path>: C9, C10, C16
    move <old> -> <new>: C13
    delete <path>: C9
    edit <KEY>: C17 TCW Item: <old> -> <new>

Reports are `<code> <where>: <text>` under `needs attention:` (A1-A14) and
`reads differently in TCW 4:` (D1-D8); blockers are `<code> <where>: <why>;
<what to do>` under `refused:`.
"""

from __future__ import annotations

import sys
from typing import Iterable

from tcw.migrate.model import Blocker, Delete, Move, Report, Step, TicketEdit, Write

#: The lines a stopped run ends with (Design 2.7, 8.6).
RUN_AGAIN = "run 'tcw migrate' again to finish"
DO_NOT_SAVE = ("do not save these files in version control until 'tcw migrate' "
               "finishes")


#: The summary's lines about the check after the run (Design 1.1, 2.1).
NOT_CHECKED_WORK = ("work store not checked after the run (--no-jira): run 'tcw validate' "
                    "to check it")
KNOWN_AFTER = ("tcw validate's findings on the converted project are known only after "
               "a real run")
CHECK_STOPPED = ("check after the run stopped: a related project is still TCW 3.x; run "
                 "'tcw validate' once it is migrated")


def say(line: str = "") -> None:
    print(line, file=sys.stderr)


def _conversions(codes: Iterable[str]) -> str:
    codes = list(codes)
    return f": {', '.join(codes)}" if codes else ""


def step_line(step: Step, *, dry: bool = False) -> str:
    would = "would " if dry else ""
    if isinstance(step, Write):
        return f"{would}write {step.path}{_conversions(step.conversions)}"
    if isinstance(step, Move):
        return f"{would}move {step.old} -> {step.new}{_conversions(step.conversions)}"
    return f"{would}delete {step.path}{_conversions(step.conversions)}"


def ticket_line(edit: TicketEdit, *, dry: bool = False) -> str:
    would = "would " if dry else ""
    return f"{would}edit {edit.key}: C17 TCW Item: {edit.old} -> {edit.new}"


def report_line(report: Report) -> str:
    return f"{report.code} {report.where}: {report.text}"


def blocker_line(blocker: Blocker) -> str:
    fix = f"; {blocker.fix}" if blocker.fix else ""
    return f"{blocker.code} {blocker.where}: {blocker.why}{fix}"


def _number(report: Report) -> int:
    return int(report.code[1:])


def reports(found: list[Report]) -> None:
    """Each group in the order of its numbers; within a number, as found."""
    attention = sorted((r for r in found if r.code.startswith("A")), key=_number)
    different = sorted((r for r in found if r.code.startswith("D")), key=_number)
    if attention:
        say("needs attention:")
        for report in attention:
            say(f"  {report_line(report)}")
    if different:
        say("reads differently in TCW 4:")
        for report in different:
            say(f"  {report_line(report)}")


def blockers(found: list[Blocker]) -> None:
    if found:
        say("refused:")
        for blocker in found:
            say(f"  {blocker_line(blocker)}")


def stopped(reason: str, not_done: list[Step]) -> None:
    """A stopped run's end (Design 2.7): why, what was not done, and the two
    instructions."""
    say(f"stopped: {reason}")
    if not_done:
        say("not done:")
        for step in not_done:
            say(f"  {step_line(step)}")
    say(RUN_AGAIN)
    say(DO_NOT_SAVE)


def counts(steps: list[Step], tickets: int, *, dry: bool) -> str:
    """The summary's count of the changes (Design 2.10): files written (each
    once), moves, deletions and tickets edited, `file` and `ticket` singular
    for a count of 1."""
    written = len({s.path for s in steps if isinstance(s, Write)})
    moved = sum(isinstance(s, Move) for s in steps)
    deleted = sum(isinstance(s, Delete) for s in steps)
    files = "file" if written == 1 else "files"
    edits = "ticket" if tickets == 1 else "tickets"
    return (f"{'would change' if dry else 'changed'}: {written} {files} written, "
            f"{moved} moved, {deleted} deleted; {tickets} {edits} edited")
