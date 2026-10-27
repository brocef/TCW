"""The lines `tcw migrate` prints (TCW-116 Design 1.5, 2.9, 2.10; Decided 14).

Every line goes to standard error. A change line names its file or ticket,
its action and its conversions, and a dry run puts `would ` first:

    write <path>: C9, C10, C16
    move <old> -> <new>: C13
    delete <path>: C9
    edit <KEY>: C17 TCW Item: <old> -> <new>

A file a run writes more than once (`.tcw/.gitignore`: its ignore line before
the progress record, the whole file later) is one line, at its first write,
with the conversions of all its writes.

Reports are `<code> <where>: <text>` under `needs attention:` (A1-A14) and
`reads differently in TCW 4:` (D1-D8); blockers are `<code> <where>: <why>;
<what to do>` under `refused:`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Iterable

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


def checkouts(folder: Path) -> list[Path]:
    """The folders at and above `folder` holding a `.git` marker, nearest
    first: the checkouts it sits in."""
    return [f for f in (folder, *folder.parents) if (f / ".git").exists()]


def shown(root: Path | None, rel: str) -> str:
    """A planned path, relative to the project at `root`, as a line shows it:
    as it is when it is inside the project or inside a checkout the project
    sits in (a planning workspace holding it, say); otherwise absolute, since
    a relative path to anywhere else climbs most of the way to `/`."""
    if root is None or not rel.startswith(".."):
        return rel
    base = Path(os.path.realpath(root))
    target = Path(os.path.normpath(base / rel))
    outer = checkouts(base)
    if outer and target.is_relative_to(outer[-1]):
        return rel
    return str(target)


def step_line(step: Step, *, dry: bool = False, root: Path | None = None) -> str:
    """`root`, the project's folder, decides how a path outside it is shown."""
    would = "would " if dry else ""
    if isinstance(step, Write):
        return f"{would}write {shown(root, step.path)}{_conversions(step.conversions)}"
    if isinstance(step, Move):
        return (f"{would}move {shown(root, step.old)} -> {shown(root, step.new)}"
                f"{_conversions(step.conversions)}")
    return f"{would}delete {shown(root, step.path)}{_conversions(step.conversions)}"


def _number_of(code: str) -> tuple[int, str]:
    return (int(code[1:]), code) if code[1:].isdigit() else (sys.maxsize, code)


def once(steps: Iterable[Step], *, dry: bool = False,
         root: Path | None = None) -> Callable[[Step], str | None]:
    """A function giving each step of `steps` its line, with each written file
    named once: at its first write, with every write's conversions in number
    order, and None for its later writes."""
    union: dict[str, set[str]] = {}
    for step in steps:
        if isinstance(step, Write):
            union.setdefault(step.path, set()).update(step.conversions)
    said: set[str] = set()

    def line(step: Step) -> str | None:
        if not isinstance(step, Write) or step.path not in union:
            return step_line(step, dry=dry, root=root)
        if step.path in said:
            return None
        said.add(step.path)
        codes = sorted(union[step.path], key=_number_of)
        would = "would " if dry else ""
        return f"{would}write {shown(root, step.path)}{_conversions(codes)}"
    return line


def say_steps(steps: Iterable[Step], *, dry: bool = False, indent: str = "",
              root: Path | None = None) -> None:
    """Each line of `steps`, each written file once."""
    steps = list(steps)
    line = once(steps, dry=dry, root=root)
    for step in steps:
        if (text := line(step)) is not None:
            say(f"{indent}{text}")


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


def stopped(reason: str, not_done: list[Step], root: Path | None = None) -> None:
    """A stopped run's end (Design 2.7): why, what was not done, and the two
    instructions."""
    say(f"stopped: {reason}")
    if not_done:
        say("not done:")
        say_steps(not_done, indent="  ", root=root)
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
