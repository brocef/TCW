"""Overrides move to their original's path (TCW-116 C14, C15, B9, D2, D3,
D4; Design 7's `moved:`; plan Step 21).

3.x matched an override to its original by the original's `cap-…` id
(`_apply_override`, `tcw/store/fs.py:2324-2369` at v3.0.2), among the local
capabilities of the projects its `capabilities.extends` names. 4.0 has no
pointer: an override is the object at its original's id-path. So each
override's pointer is resolved the way 3.x matched it, and the folder is
planned to move to the id-path found. A source still in 3.x form is read
for the id in its state files; one already migrated is read in its record,
`.tcw/tcw-migration.yaml`, whose id-path must still be in the source.

Every move is of one entry of the override's folder, so that no move is
inside another: a loose entry goes straight into the target's `resources/`
(C13), each entry of the override's own `resources/` into the target's, and
every other entry to the target under its own name. The 3.x state file is
not moved: phase C writes the 4.0 one at the target and deletes it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from tcw.migrate.legacy import (ROOT_CONFIG, STATE_3X, extends_3x, ledger_3x,
                                override_target_3x, parse_mapping_3x)
from tcw.migrate.model import Blocker, Report
from tcw.object_folders import STATE_FILES
from tcw.store.config_edit import read_text

B9_FIX = ("move the folder to the original's path and delete the overrides key by hand, "
          "then run 'tcw migrate' again")


@dataclass(frozen=True)
class Override:
    """One override of a capabilities store: its id-path now, its pointer,
    and the original it resolves to (the source's ID, the id-path there, and
    the source store's folder)."""

    path: str
    pointer: str
    source: str
    target: str
    source_folder: Path | None

    @property
    def moves(self) -> bool:
        return self.path != self.target


@dataclass
class OverridePlan:
    found: dict[str, Override] = field(default_factory=dict)    # by its id-path now
    blockers: list[Blocker] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)


@dataclass
class _Source:
    """One `capabilities.extends` project, as the pointers are resolved
    against it: each `cap-…` id to the id-path it has, the id-paths the
    record names that the source no longer has, and its store's folder."""

    ids: dict[str, str]
    gone: set[str]
    folder: Path | None
    record: bool


def pointers(store, convert: list[str]) -> dict[str, str]:
    """Each capability of `convert` whose 3.x state file has an `overrides`
    pointer, by its id-path."""
    out = {}
    for id_path in convert:
        path = store.folder / id_path / STATE_3X["capabilities"]
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError):
            continue
        data, _ = parse_mapping_3x(text, path) if text is not None else (None, None)
        if isinstance(data, dict) and data.get("overrides"):
            out[id_path] = str(data["overrides"])
    return out


def _sources(mapping: dict, family) -> dict[str, _Source]:
    from tcw.migrate.record import read_record
    from tcw.migrate.stores import related_stores
    try:
        named = extends_3x(mapping.get("capabilities"), "capabilities")
    except ValueError:
        return {}
    out = {}
    for pid in named:
        member = family.member(pid, "C14", ROOT_CONFIG) if family is not None else None
        if member is None:
            continue
        folder = next((f for ns, f in related_stores(member) if ns == "capabilities"), None)
        if member.three_x:
            ledger = ledger_3x(folder) if folder is not None else None
            ids = {cap_id: path for path, cap_id in ledger.capabilities.items()
                   if cap_id} if ledger else {}
            out[pid] = _Source(ids, set(), folder, False)
            continue
        recorded = read_record(member.folder)
        ids = recorded.get("capability-ids")
        ids = {str(k): str(v) for k, v in ids.items()} if isinstance(ids, dict) else {}
        gone = {path for path in ids.values()
                if folder is None
                or not (folder / path / STATE_FILES["capabilities"]).is_file()}
        out[pid] = _Source(ids, gone, folder, bool(recorded))
    return out


def plan_overrides(store, convert: list[str], kept: set[str], mapping: dict, family,
                   own_ids: dict[str, str]) -> OverridePlan:
    """Each override of the capabilities `store` resolved to its original,
    and B9 for each case Design 4's table names. `own_ids` is each of the
    project's own capabilities' `cap-…` id to its id-path."""
    out = OverridePlan()
    found = pointers(store, convert)
    if not found:
        return out
    sources = _sources(mapping, family)
    by_target: dict[str, str] = {}
    for path, pointer in found.items():
        where = f"{store.rel}/{path}/{STATE_3X['capabilities']}"

        def refuse(why: str) -> None:
            out.blockers.append(Blocker("B9", where, f"overrides: {pointer}: {why}",
                                        B9_FIX))
        if pointer in own_ids:
            refuse(f"names this project's own capability {store.rel}/{own_ids[pointer]}")
            continue
        matches = override_target_3x(pointer, {pid: s.ids for pid, s in sources.items()})
        if not matches:
            unrecorded = [pid for pid, s in sources.items()
                          if not s.record and s.folder is not None and not s.ids
                          and family.read.get(pid) and not family.read[pid].three_x]
            why = "names no capability of the projects capabilities.extends names"
            if unrecorded:
                why += (f"; '{unrecorded[0]}' is already migrated and keeps no "
                        f".tcw/tcw-migration.yaml to resolve it through")
            refuse(why)
            continue
        if len(matches) > 1:
            refuse("names more than one capability: " + ", ".join(
                f"'{pid}' {target}" for pid, target in matches))
            continue
        pid, target = matches[0]
        if target in sources[pid].gone:
            refuse(f"'{pid}''s .tcw/tcw-migration.yaml gives {target}, which '{pid}' "
                   f"no longer has")
            continue
        if target in by_target:
            refuse(f"overrides the same capability as {store.rel}/{by_target[target]}")
            out.found.pop(by_target[target], None)
            continue
        by_target[target] = path
        if target != path:
            if target in kept:
                refuse(f"its original's path {store.rel}/{target} holds another of this "
                       f"project's objects")
                continue
            inside = sorted(p for p in kept if p.startswith(path + "/"))
            if inside:
                refuse(f"its folder holds the capability {store.rel}/{inside[0]}, which "
                       f"would move with it")
                continue
        out.found[path] = Override(path, pointer, pid, target, sources[pid].folder)
    return out


def entry_moves(root: Path, store, override: Override, loose: list[str]):
    """The moves of one override's folder (phase B): `(old, new, codes)` for
    each entry, relative to the project's root, and B9 for an entry whose
    place at the target is taken."""
    from tcw.object_folders import RESOURCES
    old = store.folder / override.path
    moves, blockers = [], []
    base_old = f"{store.rel}/{override.path}"
    base_new = f"{store.rel}/{override.target}"
    try:
        entries = sorted(os.scandir(old), key=lambda e: e.name)
    except OSError:
        return moves, blockers
    for entry in entries:
        name = entry.name
        if name.startswith(".") or entry.is_symlink() or name == STATE_3X["capabilities"]:
            continue
        if name == RESOURCES and entry.is_dir():
            for inner in sorted(os.listdir(entry.path)):
                if not inner.startswith("."):
                    moves.append((f"{base_old}/{RESOURCES}/{inner}",
                                  f"{base_new}/{RESOURCES}/{inner}", ("C14",)))
            continue
        if name in loose:
            moves.append((f"{base_old}/{name}", f"{base_new}/{RESOURCES}/{name}",
                          ("C13", "C14")))
        else:
            moves.append((f"{base_old}/{name}", f"{base_new}/{name}", ("C14",)))
    for _, new, _ in moves:
        target = Path(root) / new
        if target.exists() or target.is_symlink():
            blockers.append(Blocker("B9", f"{base_old}/{STATE_3X['capabilities']}",
                                    f"overrides: {override.pointer}: {new} is already "
                                    f"there", B9_FIX))
    return moves, blockers


def _documents(meta: dict) -> bool:
    return bool(meta.get("prependedDocs") or meta.get("appendedDocs"))


def original_meta(override: Override) -> dict:
    """The original's state file, in either form, or `{}`."""
    if override.source_folder is None:
        return {}
    for name in (STATE_3X["capabilities"], STATE_FILES["capabilities"]):
        path = override.source_folder / override.target / name
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError):
            continue
        if text is not None:
            data, _ = parse_mapping_3x(text, path)
            return data if isinstance(data, dict) else {}
    return {}


def reports_of(store, override: Override, data: dict, middle: bool) -> list[Report]:
    """D3 and D4 for one override, named at its 4.0 state file."""
    where = f"{store.rel}/{override.target}/{STATE_FILES['capabilities']}"
    out = []
    if not _documents(data) and _documents(original_meta(override)):
        out.append(Report("D3", where, f"lists no prependedDocs or appendedDocs while "
                                       f"'{override.source}''s {override.target} does, "
                                       f"so its body now includes the original's "
                                       f"documents"))
    if middle:
        out.append(Report("D4", where, "overrides a capability this project passes on; "
                                       "TCW 3 did not apply it in the projects below, "
                                       "and TCW 4 does"))
    return out


def ancestor_paths(namespace: str, pid: str, family) -> set[str]:
    """The id-paths of `pid`'s own objects in `namespace`, as they will be
    once it is migrated: a 3.x project's capabilities with their overrides
    left out, a 4.0 one's walk."""
    from tcw.migrate.legacy import objects_3x
    from tcw.migrate.stores import related_stores
    from tcw.object_folders import walk
    member = family.quiet(pid) if family is not None else None
    if member is None:
        return set()
    folder = next((f for ns, f in related_stores(member) if ns == namespace), None)
    if folder is None or not folder.is_dir():
        return set()
    if not member.three_x:
        return set(walk(folder, namespace).objects)
    if namespace == "capabilities":
        return set(ledger_3x(folder).capabilities)
    return {p for p in objects_3x(folder, namespace)
            if not any(part.startswith(".") for part in p.split("/"))}


def d2_reports(store, kept: set[str], ancestors: list[str], family,
               overridden: set[str]) -> list[Report]:
    """D2 (C15): each of the project's own objects at an id-path an ancestor
    passing the store's axis also has, which now overrides it; an override
    C14 moved is C14's, not D2's."""
    out = []
    state = STATE_FILES[store.namespace]
    for pid in ancestors:
        theirs = ancestor_paths(store.namespace, pid, family)
        for id_path in sorted(kept & theirs - overridden):
            out.append(Report("D2", f"{store.rel}/{id_path}/{state}",
                              f"'{pid}' also has {id_path}; in TCW 4 this one overrides "
                              f"it and is merged with it field by field"))
    return out
