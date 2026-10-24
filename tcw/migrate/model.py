"""What a migration plan is made of (TCW-116 Design 2; plan Step 3).

A plan is worked out whole, in memory, before anything is written: its
local steps in the order they are written (phases A to E, Design 2.4), the
ticket edits of phase F, and everything it reports. Each step records what
a later run needs to finish it without working anything out again from a
disk the earlier phases changed (Design 2.7): a write its bytes and the
digest of what it replaces, a move the files it carries, a deletion the
digest of what it deletes and of the 4.0 file it waits for.

Paths are relative to the active project's root, written with `/`, or
absolute for a file outside it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

#: What a write expects to find where it writes, when there is nothing.
ABSENT = "absent"

#: The phases of Design 2.4, in order.
PHASES = ("A", "B", "C", "D", "E", "F")


def digest(data: bytes | str) -> str:
    """SHA-256 of `data`, a text taken as its UTF-8 bytes (Decided 4)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    """The digest of the file at `path`, or `ABSENT`."""
    try:
        return digest(Path(path).read_bytes())
    except FileNotFoundError:
        return ABSENT
    except IsADirectoryError:
        return "folder"


@dataclass(frozen=True)
class Write:
    """Write `text` to `path`. `expect` is the digest of the bytes the plan
    read there, or `ABSENT` for a new file. `reads` are the other files the
    text was planned from, each with the digest the plan read (a 4.0 state
    file's 3.x one, say), so a re-run does not write bytes planned from a
    file changed since."""

    path: str
    phase: str
    expect: str
    text: str
    conversions: tuple[str, ...] = ()
    reads: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Move:
    """Move the file or folder at `old` to `new`, by one rename. `files` is
    each file it carries, as `(path within it, digest)`; for a file, its one
    entry's path is empty."""

    old: str
    new: str
    phase: str
    files: tuple[tuple[str, str], ...]
    conversions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Delete:
    """Delete the file at `path`, whose digest the plan read as `digest`, once
    the file it waits for (`waits_for`) holds `waits_digest`. `digest` is None
    only for the progress record's own deletion."""

    path: str
    phase: str
    digest: str | None
    waits_for: str | None = None
    waits_digest: str | None = None
    conversions: tuple[str, ...] = ()


Step = Write | Move | Delete


@dataclass(frozen=True)
class TicketEdit:
    """Phase F: set ticket `key`'s `TCW Item` from `old` to `new` (C17)."""

    key: str
    old: str
    new: str


@dataclass(frozen=True)
class Report:
    """A report: `code` A1-A14 or D1-D8, where it is, and what it says.
    `predicts` is the 4.0 finding the report stands for, as `(file, kind)`,
    so the check after the run can tell it from an A12 (Decided 13)."""

    code: str
    where: str
    text: str
    predicts: tuple[str, str] | None = None


@dataclass(frozen=True)
class Blocker:
    """A blocker, B1-B17: where, why it cannot be converted, and what to do."""

    code: str
    where: str
    why: str
    fix: str = ""


@dataclass
class Plan:
    """Everything one run will do and say, worked out before any write.

    `project` and `work_backend` are what a run following the progress record
    needs to decide about the Jira half without reading a configuration the
    earlier phases changed (Decided 19). `owners` and `resolved` say why each
    planned byte is what it is (Design 2.7): the owner each converted
    reference was given, and the id-path each override pointer resolved to.
    """

    project: str | None
    work_backend: str
    steps: list[Step] = field(default_factory=list)
    tickets: list[TicketEdit] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    owners: dict[str, str] = field(default_factory=dict)
    resolved: dict[str, str] = field(default_factory=dict)
    summary: list[str] = field(default_factory=list)
    #: The Jira half (`jira.JiraHalf`), or None; and the error that stopped
    #: it while planning, or None (Design 2.3).
    half: object = None
    jira_failure: Exception | None = None

    @property
    def empty(self) -> bool:
        """Nothing to write and no ticket to edit."""
        return not self.steps and not self.tickets


def resolve(root: Path, path: str) -> Path:
    """A plan's path on disk."""
    return Path(path) if Path(path).is_absolute() else Path(root) / path
