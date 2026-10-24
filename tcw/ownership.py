"""Only the active project changes anything (TCW-114 Design 1).

A command or web route that changes or deletes an object first passes it to
`check_owned`, the one **ownership check**: it refuses (`Refused`, exit 3,
nothing written) an object whose owner is not the active project, and words
the refusal in one shape, naming where to run the command instead. No writer
compares project IDs itself.

The check is model code: "is this object's owner the active project?"
compares two project IDs every store has. It asks the deployment layer
(`tcw.locate`) for the owner's folder only to word the refusal, after it
has decided to refuse, and every error that search raises is caught, so
locating never changes the outcome (Design 1.3).

`writes` marks the methods of the store and backend interfaces that write,
creators included, for the sweep guard that keeps every caller of one either
on a path through this check or listed as a creator
(`tests/test_ownership_sweep.py`). It does nothing at run time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from tcw.errors import (ProjectGraphError, Refused, TcwError, UnknownProject,
                        Unreachable)
from tcw.ids import FullId

F = TypeVar("F", bound=Callable)


def writes(method: F) -> F:
    """Mark an interface method as one that writes."""
    method.__tcw_writes__ = True
    return method


def active_project_id(active_root: Path) -> str:
    """The ID of the project at `active_root`, from the command's one
    registry."""
    from tcw.locate import Locator
    return Locator.of(Path(active_root)).project_id


def check_owned(full_id: FullId, active_root: Path, *, reason: str | None = None,
                hint: str | None = None) -> None:
    """Return when the active project at `active_root` owns `full_id`;
    otherwise raise `Refused` with Design 1.3's message:
    `<full id> belongs to project '<owner>'`, then `reason` (which starts
    with `, and`), then where to go, then `hint` (which starts with `;`).
    Opens no backend and no store of the owner's, and writes nothing."""
    owner = full_id.project
    if owner == active_project_id(active_root):
        return
    message = f"{full_id} belongs to project '{owner}'{reason or ''}"
    message += _where(owner, Path(active_root))
    raise Refused(message + (hint or ""))


def _where(owner: str, active_root: Path) -> str:
    """Where the command can be run instead: the owner's folder when it is
    on this machine, or why it cannot be named. The `except` clauses are in
    this order because `UnknownProject` is a `ProjectGraphError`."""
    from tcw.locate import Locator
    try:
        locator = Locator.of(active_root)
        folder = locator.owner_root(owner, named_by=locator.root)
    except (UnknownProject, Unreachable) as error:
        return not_here(owner, getattr(error, "repository", None))
    except ProjectGraphError as error:
        return f"; project '{owner}' cannot be located: {error}"
    except (TcwError, ValueError, OSError):
        return not_here(owner, None)
    return f"; run the command there: tcw -C {Path(folder).resolve()} …"


def not_here(owner: str, repository: str | None) -> str:
    """The tail of a refusal naming a project that is not on this machine."""
    return f"; project '{owner}' is not on this machine" + \
        (f" ({repository})" if repository else "")
