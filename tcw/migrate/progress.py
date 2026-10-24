"""The progress record, `.tcw/tcw-migration-progress.yaml` (TCW-116 Design 2.7).

Phase A writes it once the migration record and its ignore line are on disk;
phase E deletes it last. In between, it is what a run that stopped is
finished from: every local step of the plan in order, each with the bytes it
writes and the digests it expects, so the next run works out nothing again
from a disk the earlier phases have changed. It also keeps the active
project's ID and whether its work is kept in Jira, which the next run's Jira
half is decided from (Decided 19).

YAML, with `tcw-version` first, dumped so that any text round-trips exactly
(Decided 4). It holds personal values (the planned personal files), so inside
a git repository it is ignored from phase A on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from tcw import __version__
from tcw.migrate.model import Delete, Move, Plan, Step, Write
from tcw.project_files import TCW_FOLDER, VERSION_KEY

NAME = "tcw-migration-progress.yaml"
PROGRESS = f"{TCW_FOLDER}/{NAME}"
#: Its line in `.tcw/.gitignore`.
IGNORE_RULE = "/" + NAME


class ProgressUnreadable(ValueError):
    """The progress record is not one `tcw migrate` wrote: blocker B17."""


@dataclass
class Progress:
    """A progress record read back."""

    project: str | None
    work_backend: str
    steps: list[Step]


def _step(step: Step) -> dict:
    if isinstance(step, Write):
        return {"write": step.path, "phase": step.phase, "expect": step.expect,
                "conversions": list(step.conversions),
                "reads": [{"path": p, "digest": d} for p, d in step.reads],
                "text": step.text}
    if isinstance(step, Move):
        return {"move": step.old, "to": step.new, "phase": step.phase,
                "conversions": list(step.conversions),
                "files": [{"path": p, "digest": d} for p, d in step.files]}
    return {"delete": step.path, "phase": step.phase, "digest": step.digest,
            "waits-for": step.waits_for, "waits-digest": step.waits_digest,
            "conversions": list(step.conversions)}


def dump(plan: Plan) -> str:
    """The progress record's text for `plan`."""
    data = {VERSION_KEY: __version__, "project": plan.project,
            "work-backend": plan.work_backend,
            "steps": [_step(step) for step in plan.steps],
            "owners": dict(plan.owners), "resolved": dict(plan.resolved)}
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True,
                          width=float("inf"))


def _read_step(raw: dict) -> Step:
    conversions = tuple(raw.get("conversions") or ())
    if "write" in raw:
        return Write(str(raw["write"]), str(raw["phase"]), str(raw["expect"]),
                     raw["text"], conversions,
                     tuple((str(f["path"]), str(f["digest"]))
                           for f in raw.get("reads") or ()))
    if "move" in raw:
        return Move(str(raw["move"]), str(raw["to"]), str(raw["phase"]),
                    tuple((str(f["path"]), str(f["digest"])) for f in raw["files"]),
                    conversions)
    if "delete" in raw:
        return Delete(str(raw["delete"]), str(raw["phase"]), raw.get("digest"),
                      raw.get("waits-for"), raw.get("waits-digest"), conversions)
    raise KeyError("write, move or delete")


def load(root: Path) -> Progress | None:
    """The progress record of the project at `root`, or None when there is
    none. One this command did not write is `ProgressUnreadable`."""
    path = Path(root) / PROGRESS
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            data = yaml.safe_load(handle.read())
        if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
            raise KeyError("steps")
        for key in ("project", "work-backend"):
            if key not in data:
                raise KeyError(key)
        if data["work-backend"] not in ("jira", "filesystem"):
            raise KeyError("work-backend")
        steps = [_read_step(raw) for raw in data["steps"]]
    except (yaml.YAMLError, KeyError, TypeError, AttributeError, UnicodeDecodeError) as error:
        raise ProgressUnreadable(f"{PROGRESS} is not a progress record tcw migrate "
                                 f"wrote ({error})") from None
    return Progress(data["project"], data["work-backend"], steps)
