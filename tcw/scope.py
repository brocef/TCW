"""The projects one list or show command covers (TCW-113 Design 1, 2).

`cover` answers which projects a `--scope` and a `--project` cover for the
project a command acts on, refusing a `--project` the scope does not cover
before anything is read. `Covered.read` reads one of the other projects
inside the one catch of Design 1.6, so a project that cannot be read is
named, with its reason, rather than stopping the command or being left out
silently; the active project is never read through it (Design 1.7). The
CLI and `tcw serve` both use it, so they cover the same projects and say
the same about them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tcw.errors import ConfigError, Unreachable, UsageError
from tcw.ids import is_project_id
from tcw.store.base import (SCOPES, ScopeMember, UNAVAILABILITY_ERRORS,
                            is_unavailability)

#: What `Covered.read` answers for a project that could not be read.
UNAVAILABLE = object()

#: The project-ID rule, as `--project` states it when refusing a value.
_PROJECT_RULE = "lowercase letters and digits joined by single hyphens"


@dataclass
class Covered:
    """What one command covers: the scope, the active project (`active`, its
    folder `root`), the command's one `Locator` and its registry, the covered
    projects in scope order, the `--project` value (`only`), and each
    project a read failed for, with its reason, in the order met."""

    scope: str
    active: str
    root: Path
    locator: Any
    members: list[ScopeMember]
    only: str | None = None
    reasons: dict[str, str] = field(default_factory=dict)

    @property
    def registry(self):
        return self.locator.registry

    @property
    def ids(self) -> list[str]:
        return [m.id for m in self.members]

    def wanted(self) -> list[ScopeMember]:
        """The covered projects whose own objects the command lists: the
        one `--project` names, or all of them."""
        if self.only is None:
            return list(self.members)
        return [m for m in self.members if m.id == self.only]

    def others(self) -> list[ScopeMember]:
        """`wanted()` without the active project, which the caller reads
        itself, first and outside any catch (Design 1.7)."""
        return [m for m in self.wanted() if m.id != self.active]

    def root_of(self, project_id: str) -> Path:
        """The folder of a covered project: the active one's, or the one the
        registry holds for a member of the family. Raises `Unreachable` with
        the reason a project not on this machine is unavailable for: its
        manifest entry's sentence, which names how to fetch it when the
        entry gives a repository (TCW-107 Design 6.2), or a fixed sentence
        when nothing records where it would be. Asks the registry nothing
        new, so a project with no family opens nothing (Design 1.9)."""
        if project_id == self.active:
            return self.root
        found = self.registry.get(project_id)
        if found is not None:
            return Path(found.locator)
        from tcw.store.fs import unreachable_project_note
        note = unreachable_project_note(self.registry, project_id)
        if note is None:
            note = (f"project '{project_id}' is not on this machine, and no manifest "
                    f"entry says where it would be")
        raise Unreachable(note, project=project_id)

    def read(self, project_id: str, fn: Callable[[Path], Any]) -> Any:
        """`fn(<the project's folder>)`, or `UNAVAILABLE` when the read
        raised one of Design 1.6's errors, whose message is kept as the
        project's reason. A project a read already failed for is not read
        again. Any other error, a usage error among them, is raised again.
        Never used for the active project (Design 1.7)."""
        if project_id in self.reasons:
            return UNAVAILABLE
        try:
            return fn(self.root_of(project_id))
        except UNAVAILABILITY_ERRORS as error:
            if not is_unavailability(error):
                raise
            self.reasons[project_id] = _reason(error)
            return UNAVAILABLE

    def warn(self, left_out: str, say: Callable[[str], None]) -> None:
        """One line per unavailable project, in scope order (Design 1.8):
        `warning: '<id>' is unavailable, so <left_out>: <reason>`."""
        for member in self.members:
            reason = self.reasons.get(member.id)
            if reason is not None:
                say(f"warning: '{member.id}' is unavailable, so {left_out}: {reason}")

    def unavailable(self) -> list[str]:
        """The covered projects a read failed for, in scope order."""
        return [m.id for m in self.members if m.id in self.reasons]

    def projects_json(self) -> list[dict] | None:
        """`projects` for a `--json` document (Design 1.8): every covered
        project in scope order, with its relation, and `unavailable` with
        its reason for each a read failed for; None under `own`, whose
        document is unchanged."""
        if self.scope == "own":
            return None
        out = []
        for member in self.members:
            entry: dict[str, Any] = {"id": member.id, "relation": member.relation}
            if member.id in self.reasons:
                entry["unavailable"] = self.reasons[member.id]
            out.append(entry)
        return out


def _reason(error: BaseException) -> str:
    if isinstance(error, ConfigError):
        return "; ".join(str(p) for p in error.problems)
    return str(error) or error.__class__.__name__


def cover(root: Path, scope: str, project: str | None = None) -> Covered:
    """The projects `scope` covers for the project at `root`, and the one
    `project` keeps. One `Locator` is taken here and every later read of
    the command uses it (TCW-113 plan choice 4). `own` asks the registry
    nothing more than the active project's ID. A `project` that is not a
    project ID, or that the scope does not cover, is refused (exit 2) before
    anything is read (Design 2.2)."""
    from tcw.locate import Locator
    if scope not in SCOPES:
        raise UsageError(f"--scope must be one of {', '.join(SCOPES)}, not '{scope}'")
    if project is not None and not is_project_id(project):
        raise UsageError(f"--project {project}: '{project}' is not a project ID "
                         f"({_PROJECT_RULE})")
    locator = Locator.of(Path(root))
    active = locator.project_id
    if scope == "own":
        members = [ScopeMember(active, "current")]
    else:
        members = locator.registry.scope_members(scope)
    covered = Covered(scope, active, Path(locator.root), locator, members, project)
    if project is not None and project not in covered.ids:
        raise UsageError(_not_covered(covered, project))
    return covered


def _not_covered(covered: Covered, project: str) -> str:
    """Design 2.2's refusal of a `--project` the scope does not cover."""
    text = (f"--project {project}: '{project}' is not covered by --scope "
            f"{covered.scope} in '{covered.active}', which covers "
            f"{', '.join(covered.ids)}")
    wider = covered.registry.covering_scope(project)
    if wider is not None:
        return f"{text}; --scope {wider} covers it"
    return f"{text}; it is neither an ancestor nor a descendant of '{covered.active}'"


#: The help strings of the two options (TCW-113 plan choice 13).
SCOPE_HELP = ("which projects to cover: own (this project, the default), up (adds "
              "its ancestors), down (adds its descendants), all (both); never a "
              "sibling")
PROJECT_HELP = ("keep only this project's own objects; it must be one the scope "
                "covers")


def scope_options(parser, *, default: str | None = "own") -> None:
    """`--scope` and `--project` on one of the eight list and show commands
    (Design 1.1)."""
    parser.add_argument("--scope", choices=SCOPES, default=default, help=SCOPE_HELP)
    parser.add_argument("--project", metavar="ID", help=PROJECT_HELP)
