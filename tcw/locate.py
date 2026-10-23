"""Finding the object a full identifier names (TCW-110 Design 6).

The one module outside `tcw/store/` that turns a project ID into a folder,
by asking the active project's registry (TCW-107's `project_folder`). A
command has one `Locator` for the project it acts on, so the graph and every
lookup's answer are read once, whichever project's file holds the reference
being looked up.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tcw.errors import BackendError, NotFound, ProjectGraphError, Unreachable
from tcw.ids import FullId
from tcw.store.project import FsProjectRegistry

#: Design 6.3's four answers.
FOUND, MISSING, UNRESOLVED, ERROR = "found", "missing", "unresolved", "error"


@dataclass(frozen=True)
class Outcome:
    """What a lookup found: `kind` is one of the four answers, `value` the
    object when it was found, and `message` why it was not."""

    kind: str
    value: Any = None
    message: str = ""


def outcome_of(error: Exception) -> Outcome:
    """The answer a lookup's failure gives, for a caller that reports it
    rather than stops: `unresolved` for a project that is not on this
    machine, `error` for a problem in the project graph or an ID nothing
    knows."""
    if isinstance(error, Unreachable):
        return Outcome(UNRESOLVED, message=str(error))
    if isinstance(error, ProjectGraphError):
        return Outcome(ERROR, message=str(error))
    raise error


# One `Locator` per registry: the registry is the same object for one root
# for the whole command, and a new one once a command has written a
# configuration file or a manifest, so a `Locator` lives exactly as long as
# the registry it holds.
_BY_REGISTRY: "weakref.WeakKeyDictionary[FsProjectRegistry, Locator]" = \
    weakref.WeakKeyDictionary()


class Locator:
    """The command's lookups of other projects, for the project it acts on."""

    def __init__(self, registry: FsProjectRegistry):
        self.registry = registry
        self.root = registry.project_root
        self._stores: dict[tuple[str, str], Any] = {}

    @classmethod
    def of(cls, active_root: Path) -> "Locator":
        """The command's one `Locator` for the project at `active_root`."""
        registry = FsProjectRegistry.open(active_root)
        found = _BY_REGISTRY.get(registry)
        if found is None:
            found = _BY_REGISTRY[registry] = cls(registry)
        return found

    @property
    def project_id(self) -> str:
        """The active project's ID."""
        return self.registry.current.id

    def owner_root(self, project_id: str, named_by: Path) -> Path:
        """The root of project `project_id`, as the project at `named_by`
        (the one whose file names it) finds it. Raises `Unreachable`,
        `UnknownProject` or `ProjectGraphError` as `project_folder` does."""
        if project_id == self.project_id:
            return self.root
        return self.registry.project_folder(project_id, named_by)

    def read(self, full_id: FullId, named_by: Path) -> Outcome:
        """The object `full_id` names, as the active project sees it (Design
        6.2): its own object; an inherited one, overrides applied, when the
        active store inherits from its owner; else the owner's own object,
        never one the owner itself inherits."""
        if full_id.namespace == "work":
            return self._read_work(full_id, named_by)
        active = self._store(self.project_id, full_id.namespace, self.root)
        if full_id.project == self.project_id:
            return _answer(active.get_local(full_id.id_path), full_id)
        if full_id.project in _inherited(active, full_id.namespace):
            return _answer(active.get_inherited(full_id.project, full_id.id_path), full_id)
        try:
            root = self.owner_root(full_id.project, named_by)
        except (Unreachable, ProjectGraphError) as error:
            return outcome_of(error)
        owner = self._store(full_id.project, full_id.namespace, root)
        return _answer(owner.get_local(full_id.id_path), full_id)

    def _store(self, project_id: str, namespace: str, root: Path):
        from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
        key = (project_id, namespace)
        if key not in self._stores:
            store_class = {"taxonomy": FsTaxonomyStore,
                           "capabilities": FsCapabilitiesStore}[namespace]
            self._stores[key] = store_class.open(
                root, locator=None if root == self.root else self)
        return self._stores[key]

    def _read_work(self, full_id: FullId, named_by: Path) -> Outcome:
        from tcw.work.jira.backend import JiraBackend, link_exists
        from tcw.work.open import open_backend
        try:
            root = self.owner_root(full_id.project, named_by)
        except (Unreachable, ProjectGraphError) as error:
            return outcome_of(error)
        try:
            backend = open_backend(root, personal=root == self.root)
            if isinstance(backend, JiraBackend):
                # The folder scan, never a read of the ticket, so a check
                # needs no Jira (TCW-71 R20).
                found = link_exists(backend.work_path, full_id.id_path)
                return _answer(full_id if found else None, full_id)
            return Outcome(FOUND, backend.read(full_id.id_path))
        except NotFound:
            return _answer(None, full_id)
        except BackendError as error:
            return Outcome(ERROR, message=str(error))


def _inherited(store, namespace: str) -> dict:
    """The owners `store` inherits from: every project its taxonomy reaches,
    or the projects its capabilities extend directly."""
    return store._inherited_stores() if namespace == "taxonomy" else store.extends


def _answer(found: Any, full_id: FullId) -> Outcome:
    if found is None:
        return Outcome(MISSING, message=f"no {_NOUN[full_id.namespace]} {full_id}")
    return Outcome(FOUND, found)


_NOUN = {"taxonomy": "taxonomy entry", "capabilities": "capability", "work": "work item"}
