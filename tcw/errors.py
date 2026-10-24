"""The exceptions TCW raises, each carrying the exit code it maps to.

They sit at the top of the package rather than under `tcw/work/` so that the
work model and its backends can both raise them without importing each other,
and so that the taxonomy and capabilities commands can use them too.
"""

from __future__ import annotations

from tcw import exit as codes


NO_PROJECT = "no TCW project here — run `tcw project new --id <id>` in the project folder"


class TcwError(Exception):
    """Base class: a failure the CLI turns into its `code`.

    `name` is set when the failure left a record behind that the user needs
    to know about: in Jira, the key or slug of what `new` created before it
    stopped. The CLI prints it on stdout.
    """

    code = codes.ERROR

    def __init__(self, message: str = "", *, name: str | None = None):
        super().__init__(message)
        self.name = name


class BackendError(TcwError):
    """The backend failed in a way none of the other classes describes."""

    code = codes.ERROR


class StateFileProblem(BackendError):
    """An object's state file whose `tcw-version` this TCW cannot read
    (TCW-111 Design 1.5): the object is never interpreted or rewritten.
    `path` is the file, `problem` the version check's message."""

    def __init__(self, path, problem: str, *, name: str | None = None):
        super().__init__(f"{path}: {problem}", name=name)
        self.path, self.problem = path, problem


class ConfigError(BackendError):
    """The configuration of the project a command acts on has problems, in
    `tcw-config.yaml`, a personal file, or the environment that switches
    personal files off. Every command that loads the configuration stops on
    it before doing anything else (TCW-72 Design 2.3).

    A `BackendError`, so code that already treats a broken backend as broken
    keeps doing so for a project whose configuration cannot be read.
    """

    code = codes.ERROR

    def __init__(self, problems, *, name: str | None = None):
        problems = [problems] if isinstance(problems, str) else list(problems)
        self.problems = problems
        super().__init__("\n".join(str(p) for p in problems), name=name)


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


class NotFound(TcwError):
    code = codes.NOT_FOUND


class Unreachable(TcwError):
    """A project something names is not on this machine.

    `project` is its ID and `repository` the one its deciding manifest entry
    gives, when the failure is about a project and that entry gives one
    (TCW-107 Design 6.2), so a caller can name it without parsing the
    message."""

    code = codes.UNREACHABLE

    def __init__(self, message: str = "", *, name: str | None = None,
                 project: str | None = None, repository: str | None = None):
        super().__init__(message, name=name)
        self.project = project
        self.repository = repository


class ProjectGraphError(TcwError):
    """Finding a project's folder met a problem in the project graph: two
    folders for one ID, a manifest entry pointing at a folder that is not that
    project, a manifest TCW cannot read (TCW-107 Design 2.12)."""

    code = codes.ERROR


class UnknownProject(ProjectGraphError):
    """No manifest, no `projects:` entry and no folder nearby knows the
    project ID: probably a misspelling. A subclass of `ProjectGraphError`, so
    a caller handling both catches this one first."""

    code = codes.ERROR


class InheritedUnavailable(TcwError):
    """Something the project inherits is not available here (TCW-108 Design
    6.2): a project it inherits an axis from is not on this machine, or that
    project's own parent links could not be read, so what reaches it from
    above is unknown.

    `project` is the ID of the project that is not available, `axis` the axis
    the command needed, and `reason` `"missing"`, `"unreadable"` or
    `"store"` (the project is here but its store for the axis cannot be
    opened, TCW-112 Design 1.3), so `tcw validate` can report it as "could
    not check" without parsing the message. `detail` is the store's own
    message for `"store"`, and None otherwise."""

    code = codes.INHERITED_UNAVAILABLE

    def __init__(self, message: str = "", *, project: str | None = None,
                 axis: str | None = None, reason: str | None = None,
                 detail: str | None = None):
        super().__init__(message)
        self.project = project
        self.axis = axis
        self.reason = reason
        self.detail = detail


class MovedWithoutNote(TcwError):
    """The item's stage changed, but the note meant to record why did not, or,
    when `uncertain`, may not have: the connection failed and whether the note
    arrived could not be read."""

    code = codes.MOVED_WITH_PROBLEM

    def __init__(self, message: str = "", *, uncertain: bool = False):
        super().__init__(message)
        self.uncertain = uncertain
