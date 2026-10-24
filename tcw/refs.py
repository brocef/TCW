"""Resolving a `tcw://` address (TCW-110 Design 2, 6).

Grammar, held by `tcw.ids`:
  - an object address, ``tcw://<project>.<namespace>/<id-path>``, names one
    taxonomy entry, capability or work item by its full identifier;
  - a folder address, ``tcw://<project>[.<namespace>].path/<folder-path>``,
    names a folder in a project's root or in one of its stores.

A TCW 3.x reference (``tcw://[<project>/]<axis>/<ref>``) is recognised and
refused, naming ``tcw migrate``; it is never resolved.

`resolve_address` is thin CLI and web glue over `tcw.locate`: it finds the
owner through the command's one `Locator` and never propagates a store
exception to a caller scanning many links. A work item is found at any
stage, because TCW never deletes an item folder (TCW-70 Design 12.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tcw.errors import ProjectGraphError, Unreachable
from tcw.ids import (FolderAddress, IdError, is_3x_address, parse_address,
                     three_x_address_message)
from tcw.locate import ERROR, FOUND, Locator, Outcome, outcome_of


@dataclass(frozen=True)
class ResolveResult:
    ok: bool
    namespace: str | None
    key: str | None
    reason: str
    # The owner when it is neither the served project nor one it inherits
    # from: a sound reference that a viewer of this project cannot open.
    project: str = ""
    # A work ref that resolved to a *record* of a resolved item rather than to a
    # live one. Still `ok` — the reference is sound and names real, finished work
    # — but there is nothing to navigate to, so a viewer shows it inert rather
    # than as a link, and `tcw validate` says nothing at all.
    archived: bool = False
    resolution: str = ""   # the archived item's resolution; "" when unrecorded
    # Design 6.3's answer: `found`, `missing`, `unresolved` or `error`.
    outcome: str = FOUND
    folder: bool = False   # a folder address, checked for form and owner only


def _failed(outcome: Outcome, namespace: str | None = None) -> ResolveResult:
    return ResolveResult(False, namespace, None, outcome.message, outcome=outcome.kind)


def resolve_address(project_root: Path | None, uri: str) -> ResolveResult:
    """Resolve `uri`, written in the project at `project_root` (Design 2.5).

    ``ok`` answers one question only: **does this address name something that
    is there?** That is what `tcw validate` asks. Whether a *viewer* can open
    it is a different question, so an object owned by a project the served
    one neither is nor inherits from reports its owner in ``project``, and
    the viewer gates on that (see `tcw serve`'s ``/api/resolve``)."""
    if is_3x_address(uri):
        return _failed(Outcome(ERROR, message=three_x_address_message(uri)))
    try:
        found = parse_address(uri)
    except IdError as error:
        return _failed(Outcome(ERROR, message=str(error)))
    if project_root is None:
        return _failed(Outcome(ERROR, message="no TCW project"))
    try:
        locator = Locator.of(Path(project_root))
        if isinstance(found, FolderAddress):
            # Design 6.4: its form and that its project can be located, not
            # whether the folder is there.
            try:
                locator.owner_root(found.project, Path(project_root))
            except (Unreachable, ProjectGraphError) as error:
                return _failed(outcome_of(error), found.namespace)
            return ResolveResult(True, found.namespace, None, "", folder=True)
        # Existence only, asked of the owner's own store (TCW-112 Design
        # 3.1): an address is never "could not check" because a project
        # above its owner is missing.
        answer = locator.exists(found, named_by=Path(project_root))
        active = locator.project_id
        if answer.kind != FOUND:
            return _failed(answer, found.namespace)
        if found.namespace == "work":
            if found.project == active:
                return ResolveResult(True, "work", found.id_path, "")
            return ResolveResult(True, "work", str(found), "", project=found.project)
        # An owner the active project inherits this axis from is shown here;
        # any other is another project's (TCW-110 Design 4.5).
        foreign = found.project != active and found.project not in {
            entry.id for entry in locator.registry.source_entries(found.namespace)}
    except Exception as error:   # a store's own failure (TcwError, IO, YAML)
        return _failed(Outcome(ERROR, message=str(error)))
    key = found.id_path if found.project == active else str(found)
    return ResolveResult(True, found.namespace, key, "",
                         project=found.project if foreign else "")
