"""Carrying out a plan's local steps, phases A to E (TCW-116 Design 2.4-2.8).

Every change goes through four functions (Decided 7): `_write` (one file,
atomically, then read back), `_move` (one rename, never a copy), `_delete`
and `_mkdir`. A run following a progress record walks the recorded steps in
order: a step whose result is on disk is skipped, one whose input is still as
recorded is done, and any other stops the run before it with blocker B17
(Design 2.7). A step that fails stops the run with `MigrateStopped`, which
says what was done and what was not; an operating-system error becomes one
too, so the instruction to run again is never lost (Decided 21).

Nothing here imports anything of Jira: phase F is a function the Jira half
hands over (Decided 19).
"""

from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import Callable

from tcw.migrate import progress
from tcw.migrate.model import (ABSENT, Blocker, Delete, Move, Plan, Report, Step,
                               Write, digest, file_digest, resolve)
from tcw.store import fs
from tcw.store.config_edit import read_text

DONE, TODO, CHANGED = "done", "todo", "changed"

Say = Callable[[Step], None]


class MigrateStopped(Exception):
    """A local step failed partway: the run stops, and running it again
    finishes it (Design 2.7). `not_done` are the steps left, in order."""

    def __init__(self, reason: str, not_done: list[Step] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.not_done = list(not_done or [])


class MigrateRefused(Exception):
    """A run following a progress record found something not as recorded:
    blocker B17, before any more is written."""

    def __init__(self, blocker: Blocker, not_done: list[Step]):
        super().__init__(blocker.why)
        self.blocker = blocker
        self.not_done = not_done


def cross_device_message(old: str, new: str) -> str:
    """Design 2.5's refusal of a move between two filesystems."""
    return (f"{old} and {new} are on different filesystems; tcw migrate does not "
            f"copy across them: move it by hand, keeping its contents, then run "
            f"'tcw migrate' again")


# ---------------------------------------------------------------------------
# The four writes


def _mkdir(path: Path) -> None:
    """Make `path` and each missing folder above it, one at a time, so that
    each folder made is one write."""
    missing = []
    while not path.is_dir():
        missing.append(path)
        path = path.parent
    for folder in reversed(missing):
        folder.mkdir(exist_ok=True)


def _write(path: Path, text: str) -> None:
    """Write `text` to `path` in one atomic write, through the store's
    writer, then read it back; a file that does not read back as written
    stops the run, so nothing that waits for it is deleted."""
    _mkdir(path.parent)
    fs._atomic_write_all([(path, text)])
    if read_text(path) != text:
        raise MigrateStopped(f"{path} does not read back as it was written")


def _move(old: Path, new: Path, shown: tuple[str, str]) -> None:
    """One rename. Across two filesystems it stops, and copies nothing."""
    _mkdir(new.parent)
    try:
        os.rename(old, new)
    except OSError as error:
        if error.errno == errno.EXDEV:
            raise MigrateStopped(cross_device_message(*shown)) from None
        raise


def _delete(path: Path) -> None:
    path.unlink()


# ---------------------------------------------------------------------------
# Where each step stands


def _files_of(path: Path) -> set[tuple[str, str]] | None:
    """`(path within it, digest)` of each file at `path`, or None when nothing
    is there."""
    if path.is_symlink() or path.is_file():
        return {("", file_digest(path))}
    if not path.is_dir():
        return None
    found = set()
    for dirpath, _, filenames in os.walk(path):
        for name in filenames:
            inner = Path(dirpath) / name
            found.add((inner.relative_to(path).as_posix(), file_digest(inner)))
    return found


def state(step: Step, root: Path) -> str:
    """`DONE` when the step's result is on disk, `TODO` when what it reads is
    still as recorded, else `CHANGED` (Design 2.7)."""
    return _where(step, root)[0]


def _where(step: Step, root: Path) -> tuple[str, str | None]:
    """`state`, and for `CHANGED` the path found not as recorded."""
    if isinstance(step, Write):
        now = file_digest(resolve(root, step.path))
        if now == digest(step.text):
            return DONE, None
        if now != step.expect:
            return CHANGED, step.path
        for path, recorded in step.reads:
            if file_digest(resolve(root, path)) != recorded:
                return CHANGED, path
        return TODO, None
    if isinstance(step, Move):
        old, new = resolve(root, step.old), resolve(root, step.new)
        recorded = set(step.files)
        old_files, new_files = _files_of(old), _files_of(new)
        if old_files is None and new_files == recorded:
            return DONE, None
        if old_files == recorded and new_files is None:
            return TODO, None
        return CHANGED, step.old
    path = resolve(root, step.path)
    if not path.exists() and not path.is_symlink():
        return DONE, None
    if step.digest is not None and file_digest(path) != step.digest:
        return CHANGED, step.path
    if step.waits_for is not None and \
            file_digest(resolve(root, step.waits_for)) != step.waits_digest:
        return CHANGED, step.waits_for
    return TODO, None


def _changed_blocker(step: Step, where: str) -> Blocker:
    fix = (f"restore it as it was, or restore the project from version control, "
           f"delete {progress.PROGRESS}, and run 'tcw migrate' again")
    recorded = f"is not as {progress.PROGRESS} recorded it"
    if isinstance(step, Move):
        return Blocker("B17", where, f"{recorded} when it planned to move it to "
                       f"{step.new}", fix)
    if isinstance(step, Delete):
        if where == step.path:
            return Blocker("B17", where, f"{recorded}, so it is not deleted", fix)
        return Blocker("B17", where, f"{recorded}; {step.path} is deleted only once "
                       f"it is", fix)
    if where != step.path:
        return Blocker("B17", where, f"{recorded}; {step.path} was planned from it",
                       fix)
    return Blocker("B17", where, recorded, fix)


def _perform(step: Step, root: Path) -> None:
    if isinstance(step, Write):
        _write(resolve(root, step.path), step.text)
    elif isinstance(step, Move):
        _move(resolve(root, step.old), resolve(root, step.new), (step.old, step.new))
    else:
        _delete(resolve(root, step.path))


def _foreseen(steps: list[Step], root: Path) -> tuple[int, str] | None:
    """The first step that will be found changed when its turn comes, and
    the path found so, or None: each step judged against the disk as the
    steps before it will leave it, so a hand edit anywhere stops the run
    before it writes anything more (Design 2.2, 2.7)."""
    after: dict[str, str] = {}
    moving: list[Move] = []

    def now(rel: str) -> str:
        if rel in after:
            return after[rel]
        for move in moving:
            if rel == move.new or rel.startswith(move.new + "/"):
                inner = rel[len(move.new) + 1:]
                return dict(move.files).get(inner, ABSENT)
        return file_digest(resolve(root, rel))
    for i, step in enumerate(steps):
        if isinstance(step, Move):
            found, where = _where(step, root)
            if found == CHANGED:
                return i, where
            if found == TODO:
                moving.append(step)
            continue
        if isinstance(step, Write):
            here = now(step.path)
            if here != digest(step.text):
                if here != step.expect:
                    return i, step.path
                for path, recorded in step.reads:
                    if now(path) != recorded:
                        return i, path
            after[step.path] = digest(step.text)
            continue
        here = now(step.path)
        if here != ABSENT:
            if step.digest is not None and here != step.digest:
                return i, step.path
            if step.waits_for is not None and now(step.waits_for) != step.waits_digest:
                return i, step.waits_for
        after[step.path] = ABSENT
    return None


def run_local(steps: list[Step], root: Path, say: Say) -> None:
    """Walk `steps` in order: skip each done one, refuse at the first changed
    one (B17), and otherwise do it, saying each change as it is made. A step
    that will be found changed refuses the run before any step is done."""
    foreseen = _foreseen(steps, root)
    if foreseen is not None:
        i, where = foreseen
        raise MigrateRefused(_changed_blocker(steps[i], where), steps[i:])
    for i, step in enumerate(steps):
        found, where = _where(step, root)
        if found == DONE:
            continue
        if found == CHANGED:
            raise MigrateRefused(_changed_blocker(step, where), steps[i:])
        try:
            _perform(step, root)
        except MigrateStopped as stop:
            raise MigrateStopped(stop.reason, steps[i:]) from None
        except OSError as error:
            raise MigrateStopped(str(error), steps[i:]) from None
        say(step)


def apply(plan: Plan, root: Path, say: Say) -> None:
    """Carry out `plan`'s local steps: phase A's writes (the record, then the
    ignore line), then the progress record, then phases B to E, then the
    progress record deleted last (Design 2.4; Decided 5)."""
    first = [s for s in plan.steps if s.phase == "A"]
    rest = [s for s in plan.steps if s.phase != "A"]
    run_local(first, root, say)
    record = Write(progress.PROGRESS, "A", ABSENT, progress.dump(plan))
    try:
        _write(resolve(root, record.path), record.text)
    except MigrateStopped as stop:
        raise MigrateStopped(stop.reason, rest) from None
    except OSError as error:
        raise MigrateStopped(str(error), rest) from None
    _finish(rest, root, say)


def follow(steps: list[Step], root: Path, say: Say) -> None:
    """Finish a run that stopped, from its progress record's steps. Phase A
    was finished before the record was written, and a later phase may write
    the same file again (`.tcw/.gitignore`), so phase A is not walked."""
    _finish([s for s in steps if s.phase != "A"], root, say)


def _finish(steps: list[Step], root: Path, say: Say) -> None:
    run_local(steps, root, say)
    path = resolve(root, progress.PROGRESS)
    try:
        _remove_emptied(steps, root)
        if path.exists():
            _delete(path)
    except OSError as error:
        raise MigrateStopped(str(error), [Delete(progress.PROGRESS, "E", None)]) from None


def _remove_emptied(steps: list[Step], root: Path) -> None:
    """Remove each folder a move or a deletion left empty (an override's
    folder, C14, once its entries moved and its 3.x state file is
    deleted), and each folder above it left empty in
    turn, stopping at the first that holds anything and never removing the
    project's root or a folder above it. 4.0's `tcw validate` reports an
    empty folder in a store as holding no object. Run after every step, on
    each run that finishes, so a run stopped here removes them the next
    time."""
    top = Path(root).resolve()
    for step in steps:
        if not isinstance(step, (Move, Delete)):
            continue
        folder = resolve(root, step.old if isinstance(step, Move) else step.path).parent
        while not folder.exists() and folder != folder.parent:
            folder = folder.parent            # removed by an earlier run
        while folder.is_dir() and not any(folder.iterdir()):
            here = folder.resolve()
            if here == top or here in top.parents:
                break
            folder.rmdir()
            folder = folder.parent


def refusal(steps: list[Step], root: Path) -> Blocker | None:
    """B17 for a run following a progress record, found before anything is
    written; None when none would be found. For a dry run."""
    rest = [s for s in steps if s.phase != "A"]
    foreseen = _foreseen(rest, root)
    return None if foreseen is None else _changed_blocker(rest[foreseen[0]], foreseen[1])


def pending(steps: list[Step], root: Path) -> list[Step]:
    """The steps of a progress record not yet done, for a dry run."""
    return [step for step in steps if step.phase != "A" and state(step, root) != DONE]


# ---------------------------------------------------------------------------
# The check after the run (Design 2.1, 2.9; Decided 13)

#: How a 4.0 finding's kind is told from its message, for each kind a report
#: predicts.
KINDS = {"not_tags": "'not_tags'", "id": "is not its folder's name",
         "resources": "resources/", "mention": "names ",
         "legacy": "is a TCW 3.x project"}


def _same_file(a: str, b: str, root: Path) -> bool:
    return resolve(root, a).resolve() == resolve(root, b).resolve()


def check_after(root: Path, predicts: list[tuple[str, str]], *, work: bool) -> list[Report]:
    """4.0's offline `tcw validate` of the project as now written, each
    finding no report predicts listed as A12 in 4.0's words. A finding is
    predicted by a report naming its file and its kind; one in the same file
    but of another kind is not. `work=False` leaves out the work-store
    checks, which would open the Jira backend (Design 1.1). The configuration
    read so far is dropped first, since the run has just rewritten it."""
    from tcw import config as layered
    from tcw.cli import _located, collect_findings
    layered.end_command()
    layered.begin_command()
    out = []
    for finding in collect_findings(Path(root), work=work):
        finding = _located(finding, Path(root))
        where = finding.where.rsplit(":", 1)[0] if finding.where.rsplit(":", 1)[-1] \
            .isdigit() else finding.where
        if any(_same_file(where, file, root) and KINDS.get(kind, "\0") in finding.message
               for file, kind in predicts):
            continue
        # A8 names a related project's folder, which 4.0 reports in the file
        # whose entry or search reached it.
        if any(kind == "legacy" and KINDS["legacy"] in finding.message
               and file in finding.message for file, kind in predicts):
            continue
        out.append(Report("A12", finding.where, " ".join(finding.message.split())))
    return out
