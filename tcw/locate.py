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

from tcw.errors import (BackendError, NotFound, ProjectGraphError, Refused, TcwError,
                        Unreachable)
from tcw.ids import FullId, is_project_id, sort_input
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
            owner = self.owner_store(full_id.project, full_id.namespace, named_by)
        except (Unreachable, ProjectGraphError) as error:
            return outcome_of(error)
        return _answer(owner.get_local(full_id.id_path), full_id)

    def owner_store(self, project_id: str, namespace: str, named_by: Path):
        """The `namespace` store of project `project_id`, as the project at
        `named_by` finds it; raises as `owner_root` does."""
        return self._store(project_id, namespace, self.owner_root(project_id, named_by))

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
        from tcw.work.jira.backend import link_exists
        from tcw.work.open import item_folders
        try:
            root = self.owner_root(full_id.project, named_by)
        except (Unreachable, ProjectGraphError) as error:
            return outcome_of(error)
        try:
            target = item_folders(root, personal=root == self.root,
                                  registry=self.registry)
            if isinstance(target, Path):
                # A Jira-mode project: the folder scan, never a read of the
                # ticket, so a check needs no Jira (TCW-71 R20) and no Jira
                # setting a parent may hold (TCW-109 Design 3.4).
                found = link_exists(target, full_id.id_path)
                return _answer(full_id if found else None, full_id)
            return Outcome(FOUND, target.read(full_id.id_path))
        except NotFound:
            return _answer(None, full_id)
        except BackendError as error:
            return Outcome(ERROR, message=str(error))


def find_tree(store, text: str):
    """The taxonomy entry or capability that command input `text` names, as
    the project `store` belongs to sees it (TCW-110 Design 3.1): a full
    identifier of its own entry, of one it inherits (override applied), or of
    another project's own entry; or an id-path read local first, then
    inherited. Raises `NotFound` (exit 4) for nothing there, a usage error for
    text in no form, and the lookup's own error for a project TCW cannot
    find."""
    namespace = store.COMPONENT
    found = sort_input(text, namespace)
    if found.form == "d":
        hit = store.get_view(found.id_path)
        if hit is None:
            raise NotFound(_no_such(namespace, text) + _spelled(store, found.id_path)
                           + _three_x_hint(store, namespace, found.id_path))
        return hit
    full_id = found.full_id
    if full_id.project == store.project_id:
        owner = store
        hit = store.get_local(full_id.id_path)
    elif full_id.project in _inherited(store, namespace):
        owner = _inherited(store, namespace)[full_id.project]
        hit = store.get_inherited(full_id.project, full_id.id_path)
    else:
        locator = store.locator
        owner = locator.owner_store(full_id.project, namespace, locator.root)
        hit = owner.get_local(full_id.id_path)
    if hit is None:
        raise NotFound(_no_such(namespace, text) + _spelled(owner, full_id.id_path))
    return hit


def find_tree_writable(store, text: str):
    """`find_tree`, refusing an entry that belongs to a project `store` does
    not inherit from: a command changes only this project's own entries and
    its overrides of inherited ones (as `_own` does for work items)."""
    hit = find_tree(store, text)
    if hit.owner != store.project_id and hit.owner not in _inherited(store, store.COMPONENT):
        raise Refused(f"{hit.full_id} belongs to project '{hit.owner}'; change it there")
    return hit


def three_x_hint(locator: "Locator", namespace: str, id_path: str) -> str:
    """Design 3.4: when a multi-part id-path that was not found starts with
    the ID of a project TCW can locate, the text to add to the not-found
    message; otherwise "". Looking never changes the outcome: every answer
    but a folder, every error included, gives no hint."""
    first, slash, rest = id_path.partition("/")
    if not slash or not is_project_id(first):
        return ""
    try:
        locator.owner_root(first, locator.root)
    except (TcwError, OSError, ValueError):
        return ""
    return (f"; to name an object in project '{first}', write "
            f"{first}.{namespace}/{rest}")


def _three_x_hint(store, namespace: str, id_path: str) -> str:
    try:
        locator = store.locator
    except (TcwError, OSError, ValueError):
        return ""
    return three_x_hint(locator, namespace, id_path)


def _spelled(store, id_path: str) -> str:
    """When `id_path` was not found only because a folder's letter case
    differs (a disk that ignores case finds it), the spelling on disk, for
    the not-found message (Design 1.1)."""
    from tcw.store.fs import exact_path
    on_disk = exact_path(store.root, id_path)
    return f" (the folder is spelled {on_disk})" if isinstance(on_disk, str) else ""


def _no_such(namespace: str, text: str) -> str:
    return f"no such {_SINGULAR[namespace]}: '{text}'"


_SINGULAR = {"taxonomy": "term", "capabilities": "capability"}


def _inherited(store, namespace: str) -> dict:
    """The owners `store` inherits from: every project its taxonomy reaches,
    or the projects its capabilities extend directly."""
    return store._inherited_stores() if namespace == "taxonomy" else store.extends


def _answer(found: Any, full_id: FullId) -> Outcome:
    if found is None:
        return Outcome(MISSING, message=f"no {_NOUN[full_id.namespace]} {full_id}")
    return Outcome(FOUND, found)


_NOUN = {"taxonomy": "taxonomy entry", "capabilities": "capability", "work": "work item"}
