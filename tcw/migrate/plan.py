"""Working out the whole migration before anything is written (TCW-116
Design 2.1, 2.2; plan Step 5).

`make_plan` reads the active project's files in either format, asks each
part of the conversion for its steps, reports and blockers, and puts the
steps in the order of Design 2.4. Nothing here writes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from tcw.migrate import config, record, stores
from tcw.migrate.legacy import (ROOT_CONFIG, STATE_3X, Layer3, Layers3, objects_3x,
                                parse_mapping_3x, read_3x_layers, read_layer_3x,
                                store_folder_3x)
from tcw.migrate.model import PHASES, Blocker, Plan
from tcw.project_files import LOCAL_SENTINEL, SENTINEL, VERSION_KEY, without_version


@dataclass
class Read:
    """What the plan reads of the active project."""

    root: Path
    layers: Layers3                  # the root files and the user-wide one
    shared4: Layer3                  # .tcw/tcw-config.yaml
    personal4: Layer3                # .tcw/tcw-config.local.yaml
    git: Path | None

    @property
    def shared(self) -> tuple[str, dict]:
        """The shared configuration being converted, and the file it is in:
        the root file when there is one, else `.tcw/`'s."""
        if self.layers.shared.present:
            return ROOT_CONFIG, self.layers.shared.data or {}
        data = self.shared4.data or {}
        return SENTINEL, without_version(data) if VERSION_KEY in data else data

    @property
    def three_x(self) -> bool:
        """The shared configuration is still in 3.x form."""
        return self.layers.shared.present or VERSION_KEY not in (self.shared4.data or {})

    @property
    def work_backend(self) -> str:
        work = self.shared[1].get("work")
        backend = work.get("backend") if isinstance(work, dict) else None
        return "jira" if backend == "jira" else "filesystem"


def read_project(root: Path) -> Read:
    from tcw.store.fs import git_root
    root = Path(root)
    return Read(root, read_3x_layers(root), read_layer_3x(root / SENTINEL, "shared"),
                read_layer_3x(root / LOCAL_SENTINEL, "personal"), git_root(root))


# ---------------------------------------------------------------------------
# The part-1 refusal of part-2 forms (Decided 17)


def _not_yet(rel: str, where: str, form: str) -> Blocker:
    return Blocker("B5", rel, f"{where}: tcw migrate does not convert {form} yet",
                   "keep this project on TCW 3 until a TCW 4 release converts it")


def part_two_forms(read: Read) -> list[Blocker]:
    """B5 for every 3.x form only part 2 of the build converts. Each step of
    part 2 removes the forms it converts."""
    rel, mapping = read.shared
    out = []
    if "projects" in mapping:
        out.append(_not_yet(rel, "projects", "projects:"))
    for component in ("taxonomy", "capabilities"):
        section = mapping.get(component)
        if isinstance(section, dict) and "extends" in section:
            out.append(_not_yet(rel, f"{component}.extends", f"{component}.extends"))
    for component in ("taxonomy", "capabilities", "work"):
        section = mapping.get(component)
        store = store_folder_3x(read.root, component, section)
        configured = section.get("path") if isinstance(section, dict) else None
        if store.form == "outside":
            out.append(_not_yet(rel, f"{component}.path",
                                f"a {component} store outside the project"))
        elif store.form == "repository":
            out.append(_not_yet(rel, f"{component}.repository",
                                f"a {component} store with only a repository"))
        elif isinstance(configured, str) and (os.path.isabs(configured)
                                              or configured.startswith("~")):
            out.append(_not_yet(rel, f"{component}.path",
                                f"an absolute {component} store path"))
    for store in stores.stores_of(read.root, mapping):
        if store.namespace != "capabilities":
            continue
        for id_path in objects_3x(store.folder, "capabilities"):
            meta = f"{store.rel}/{id_path}/{STATE_3X['capabilities']}"
            try:
                text = (read.root / meta).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            data, _ = parse_mapping_3x(text, Path(meta))
            if isinstance(data, dict) and "overrides" in data:
                out.append(_not_yet(meta, "overrides", "an override"))
    return out


# ---------------------------------------------------------------------------
# The plan


def make_plan(root: Path, *, no_jira: bool = False) -> Plan:
    """Everything one run will do and say, worked out before any write."""
    read = read_project(root)
    shared = config.plan_file(read.root, read.layers.shared, read.shared4, shared=True)
    personal = config.plan_file(read.root, read.layers.personal, read.personal4,
                                shared=False)
    plan = Plan(shared.project, read.work_backend)
    plan.blockers = part_two_forms(read) + shared.blockers + personal.blockers
    steps = shared.steps + personal.steps
    reports = shared.reports + personal.reports
    if shared.project:
        found = stores.plan_stores(read.root, read.shared[1], shared.project,
                                   three_x=read.three_x)
        plan.blockers += found.blockers
        reports += found.reports
        written = record.plan_record(read.root, found.ids)
        steps = ([written] if written else []) + steps + found.steps
    if steps and read.git is not None:
        steps += config.plan_ignore(read.root)
    plan.steps = sorted(steps, key=lambda step: PHASES.index(step.phase))
    if plan.steps or plan.blockers:
        plan.reports = (reports + config.user_reports(read.layers.user)
                        + config.ignore_reports(read.root))
    return plan
