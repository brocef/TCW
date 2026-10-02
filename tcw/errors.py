"""The exceptions TCW raises, each carrying the exit code it maps to.

They sit at the top of the package rather than under `tcw/work/` so that the
work model and its backends can both raise them without importing each other,
and so that the taxonomy and capabilities commands can use them too.
"""

from __future__ import annotations

from tcw import exit as codes


class TcwError(Exception):
    """Base class: a failure the CLI turns into its `code`."""

    code = codes.ERROR


class BackendError(TcwError):
    """The backend failed in a way none of the other classes describes."""

    code = codes.ERROR


class UsageError(TcwError):
    """The request cannot be made at all; nothing was read or written."""

    code = codes.USAGE


class Refused(TcwError):
    """A legal request that a rule turned down, having changed nothing.

    `name` is set when the backend had already made a record before the
    refusal — in Jira, the key of a ticket `new` created before it stopped — so
    the caller can tell the user it exists.
    """

    code = codes.REFUSED

    def __init__(self, message: str, *, name: str | None = None):
        super().__init__(message)
        self.name = name


class NotFound(TcwError):
    code = codes.NOT_FOUND


class Unreachable(TcwError):
    code = codes.UNREACHABLE


class MovedWithoutNote(TcwError):
    """The item's stage changed, but the note meant to record why did not."""

    code = codes.MOVED_WITH_PROBLEM
