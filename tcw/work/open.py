"""Opening a project's work backend, and delegating work into another project.

`open_backend` is how every `tcw work` command reaches the items of the
project it runs in. `open_project` reads another project's items.
`delegate` and `open_for_update` are the only two ways a command writes into
another project, and both check the same conditions first.

Git is only read here: the uncommitted-changes check runs
`git --no-optional-locks status`, which never takes the index lock.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tcw.errors import (BackendError, ConfigError, NotFound, ProjectGraphError, Refused,
                        Unreachable)
from tcw.ids import FullId, sort_input
from tcw.store.fs import FsProjectRegistry, WorkLocation, git_root
from tcw.work.backend import WorkBackend
from tcw.work.config import WorkConfig
from tcw.work.jira.backend import KEY, JiraBackend, link_exists
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.model import Changes, Slug, inbox_stage


def work_path(project_root: Path) -> Path:
    """The project's work path, resolved as every store's location is
    (`work.path`, else `docs/work`, re-anchored in a linked worktree, else a
    declared repository's provisioned checkout). Raises `ValueError` when no
    usable directory is found."""
    return WorkLocation.open(Path(project_root)).root


def _layered(project_root: Path, personal: bool, registry=None):
    """The project's configuration through the layered loader; `ConfigError`
    naming every problem. Personal layers apply only to the project a command
    acts on (TCW-72 Design 1.7). `registry` is the command's, through which a
    project read for itself finds its parents (TCW-109 Design 5.2)."""
    from tcw.config import effective, load_config
    config = (effective(project_root, registry=registry) if personal
              else load_config(project_root, personal=False, registry=registry))
    if config.problems:
        raise ConfigError(config.problems)
    return config


def read_layered(project_root: Path, *, personal: bool = True, registry=None):
    """The project's whole layered configuration (`tcw.config.Config`),
    without opening the store; `ConfigError` naming every problem."""
    return _layered(Path(project_root), personal, registry)


def read_work_config(project_root: Path, *, personal: bool = True,
                     registry=None) -> WorkConfig:
    """The project's parsed `work:` configuration, without opening the
    store: what the tag registry commands need."""
    return _layered(Path(project_root), personal, registry).work


@dataclass(frozen=True)
class ProjectFacts:
    """What opening a project's work store checks and reads before it builds
    a backend (TCW-109 Design 3.4): its layered configuration, its ID, its
    work path, and the registry used for the active project."""

    layered: Any
    project: str
    path: Path
    registry: Any = None


def project_facts(project_root: Path, *, personal: bool = True,
                  registry=None) -> ProjectFacts:
    """Every check `open_backend` makes before it builds a backend, and what
    they read, without building one, so a command that needs only the
    project's own configuration, its ID or its work path never reads a key
    the project inherits. Fails as `open_backend` does: `ConfigError` for a
    configuration problem, `BackendError` for an invalid project graph or no
    work path.

    For the active project (`personal`) the registry passed, or one opened at
    `project_root`, answers for its whole graph and its ID. For a project read
    for itself, the passed registry, the command's, is used only to find its
    parents; its ID is read from its own registry, never from the passed
    one, whose current project is the active one (Design 5.2)."""
    root = Path(project_root)
    try:
        if personal and registry is None:
            registry = FsProjectRegistry.open(root)
    except ValueError as error:
        raise BackendError(str(error)) from None
    layered = _layered(root, personal, registry)
    try:
        if personal:
            # The project the command acts on answers for its whole graph, as
            # `taxonomy` and `validate` do; another project's broken child does
            # not stop reading that project from here.
            registry.require_valid()
            project = registry.current.id
        else:
            project = FsProjectRegistry.open(root).current.id
        path = work_path(root)
    except ValueError as error:
        raise BackendError(str(error)) from None
    return ProjectFacts(layered, project, path, registry if personal else None)


def external_stages_of(config: WorkConfig) -> frozenset[str]:
    """The stages whose record the project's backend keeps, a fixed fact of
    its kind, read without building it."""
    return (JiraBackend.external_stages if config.backend == "jira"
            else FsWorkBackend.external_stages)


def open_backend(project_root: Path, *,
                 report: Callable[[str], None] | None = None,
                 personal: bool = True, registry=None) -> WorkBackend:
    """The work backend of the project at `project_root`, from its effective
    configuration. `personal=False` for any project other than the one the
    command acts on: its backend is built from its shared files and the
    variables naming it, with no personal file and no `user.name`.
    `registry` is the command's, as `project_facts` takes it."""
    root = Path(project_root)
    facts = project_facts(root, personal=personal, registry=registry)
    layered = facts.layered
    config = layered.work
    if config.backend == "jira":
        # Before the backend exists, so a key a missing parent leaves unknown
        # stops the command before any request (TCW-109 Design 3.3): opening
        # reads `work.jira`, and reading tickets reads `work.tags`.
        layered.require("work.jira")
        layered.require("work.tags")
        return JiraBackend(facts.project, facts.path, config, layered.jira,
                           report=report, root=root)
    return FsWorkBackend(facts.project, facts.path, config, layered.user_name,
                         report=report)


def item_folders(project_root: Path, *, personal: bool = True, registry=None
                 ) -> "Path | WorkBackend":
    """What answers whether an item of the project at `project_root` exists:
    for a Jira-mode project its work path, since a reference into it is
    answered from the item folders, which need no Jira setting (TCW-71 R20,
    TCW-109 Design 3.4); for a filesystem project its backend."""
    facts = project_facts(project_root, personal=personal, registry=registry)
    if facts.layered.work.backend == "jira":
        return facts.path
    return FsWorkBackend(facts.project, facts.path, facts.layered.work,
                         facts.layered.user_name)


def _registry(here: Path) -> FsProjectRegistry:
    try:
        return FsProjectRegistry.open(Path(here))
    except ValueError as error:
        raise BackendError(str(error)) from None


def open_project(project_id: str, here: Path) -> WorkBackend:
    """Another project's backend, for reading: any project TCW can locate,
    not only one `projects:` names (TCW-110 Design 6.1). `Unreachable` when
    it is named but not on this machine; `UnknownProject` for an ID nothing
    knows and `ProjectGraphError` for a problem in the project graph."""
    root, registry = _reading_root(project_id, here)
    return open_backend(root, personal=False, registry=registry)


def _reading_root(project_id: str, here: Path):
    """Another project's root, as the active project at `here` finds it, and
    the command's registry, through which that project's parents are found
    (TCW-109 Design 5.2)."""
    from tcw.locate import Locator
    try:
        locator = Locator.of(Path(here))
    except ValueError as error:
        raise BackendError(str(error)) from None
    return locator.owner_root(project_id, locator.root), locator.registry


def resolve_work_input(text, active: Callable[[], WorkBackend], root: Path
                       ) -> tuple[Slug, WorkBackend]:
    """The item that command input `text` names, sorted by TCW-110 Design
    3.1, and the backend that holds it. `active` gives the active project's
    backend and is called only when the item is the active project's: a key
    alone (form b), an id-path (form d), or a full identifier naming this
    project. Another project's full identifier opens that project's backend
    alone (Design 6.1). A key is looked up in its project's backend, never
    read as a folder name (Design 3.2)."""
    found = sort_input(str(text) if isinstance(text, FullId) else text, "work", KEY)
    if found.form == "b":
        backend = active()
        return _by_key(backend, found.key), backend
    if found.form == "d":
        backend = active()
        if "/" in found.id_path and not backend.is_item_folder(found.id_path):
            # A nested item is named by its whole id-path (TCW-111); one that
            # names no item may be a 3.x `<project>/<folder>`, and the hint
            # (TCW-110 Design 3.4) is tried only then.
            from tcw.locate import Locator, three_x_hint
            try:
                hint = three_x_hint(Locator.of(Path(root)), "work", found.id_path)
            except (ValueError, OSError):
                hint = ""
            raise NotFound(f"no work item {text} in project '{backend.project}'{hint}")
        return Slug(backend.project, found.id_path), backend
    project = found.full_id.project
    backend = active() if project == _active_id(root, active) \
        else open_project(project, root)
    if found.form == "c":
        return _by_key(backend, found.key), backend
    return Slug.of(found.full_id), backend


def _active_id(root: Path, active: Callable[[], WorkBackend]) -> str:
    """The active project's ID, read from its configuration rather than by
    opening its backend; from the backend when no registry opens here."""
    try:
        return FsProjectRegistry.open(Path(root)).current.id
    except (ValueError, OSError):
        return active().project


def _by_key(backend: WorkBackend, key: str) -> Slug:
    folder = backend.lookup(key)
    if folder is None:
        raise NotFound(f"no work item in project '{backend.project}' carries "
                       f"the key {key}")
    return Slug(backend.project, folder)


def name_item(text, active: Callable[[], WorkBackend], root: Path) -> Slug:
    """The full identifier of the item `text` names, opening no backend for a
    full identifier: its owner is opened later by whatever writes to it or
    checks it. A key or a folder name is resolved as `resolve_work_input`
    does."""
    found = sort_input(str(text) if isinstance(text, FullId) else text, "work", KEY)
    if found.form == "a":
        return Slug.of(found.full_id)
    return resolve_work_input(text, active, root)[0]


def existing_item(text, active: Callable[[], WorkBackend], root: Path
                  ) -> tuple[Slug, WorkBackend]:
    """`resolve_work_input`, and the item must be there: a reference a
    command is about to store is read from its owner's backend first, by
    its folder alone, so a misspelt or wrong-case one stops the command
    (exit 4) before anything is written (TCW-110 AC 25)."""
    slug, backend = resolve_work_input(text, active, root)
    if not backend.is_item_folder(slug.folder):
        raise NotFound(f"no work item {slug}")
    return slug, backend


# ---------------------------------------------------------------------------
# Writing into another project


def uncommitted_changes(path: Path, project_id: str | None = None) -> list[str]:
    """Paths under `path` that git has not committed, ignored files excepted.

    Refuses when `path` is not inside a git repository, because then it cannot
    be checked. Runs `git --no-optional-locks status`, which neither refreshes
    the index nor takes `index.lock` in someone else's repository.
    """
    who = (f"the work store of project '{project_id}'" if project_id
           else "the project's work store")
    repository = git_root(Path(path))
    if repository is None:
        raise Refused(f"{who} is not in a git repository, so TCW "
                      f"cannot check it for uncommitted changes")
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repository), "status",
         "--porcelain", "--untracked-files=all", "--", str(path)],
        capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise BackendError(f"cannot check {path} for uncommitted changes: "
                           f"{result.stderr.strip()}")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def _check_declared(registry: FsProjectRegistry, project_id: str) -> None:
    """The first two conditions of delegation: in the family, and reached
    across links both sides declare (TCW-108 Design 7.1)."""
    if registry.get(project_id) is None \
            and registry.unreachable_project(project_id) is None:
        raise Refused(f"no project '{project_id}' is declared here")
    reason = registry.read_only_reason(project_id)
    if reason is not None:
        raise Refused(reason)


def _check_target(registry: FsProjectRegistry, project_id: str) -> Path:
    """The five conditions of delegation, in order; the first that fails
    refuses. Returns the target's work path."""
    _check_declared(registry, project_id)
    project = registry.get(project_id)
    if project is None:
        absent = registry.unreachable_project(project_id)
        if absent is not None and absent.message:
            # TCW-107 Design 6.2, as `open_project` reports it.
            raise Refused(absent.message)
        raise Refused(f"project '{project_id}' is declared but is not on this "
                      f"machine")
    try:
        path = work_path(Path(project.locator))
    except ValueError:
        raise Refused(f"'{project_id}' has no work store on this machine") from None
    changed = uncommitted_changes(path, project_id)
    if changed:
        raise Refused(f"the work store of '{project_id}' has uncommitted changes: "
                      f"{', '.join(changed)} — resolve them in that project first")
    return path


def delegate(project_id: str, title: str, request: str | None,
             priority: str | None, *, here: Path,
             report: Callable[[str], None] | None = None) -> str:
    """Create an item in another project's inbox, and return its full slug;
    for a Jira-mode target, the ticket's key when no item could be made
    (TCW-71 Design 8)."""
    registry = _registry(here)
    _check_declared(registry, project_id)
    say = report or (lambda line: print(line, file=sys.stderr))
    project = registry.get(project_id)
    # The target is read for itself, its parents found through this
    # command's registry (TCW-109 Design 5.2).
    if project is not None and read_work_config(Path(project.locator), personal=False,
                                                registry=registry).backend == "jira":
        from tcw.work.jira.tickets import delegate_to_jira
        return delegate_to_jira(project_id, title, request, priority,
                                root=Path(project.locator), report=say,
                                registry=registry)
    path = _check_target(registry, project_id)
    backend = open_backend(Path(registry.get(project_id).locator),
                           report=_uncommitted_in(path, say), personal=False,
                           registry=registry)
    props = Changes() if priority is None else Changes(priority=priority)
    item = backend.create(title, props, stage=inbox_stage(), request=request)
    return str(item.slug)


def open_for_update(project_id: str, here: Path, *,
                    report: Callable[[str], None] | None = None) -> WorkBackend:
    """Another project's backend, so `edit --blocks` can change an existing
    item there. It never creates anything. Each file it writes is named with
    where it is left uncommitted, as delegation names its files (Design 1.2)."""
    registry = _registry(here)
    path = _check_target(registry, project_id)
    say = report or (lambda line: print(line, file=sys.stderr))
    return open_backend(Path(registry.get(project_id).locator),
                        report=_uncommitted_in(path, say), personal=False,
                        registry=registry)


def _uncommitted_in(path: Path, say: Callable[[str], None]) -> Callable[[str], None]:
    """A reporter that adds, to each line, the repository holding the work
    store at `path`, where the files are left uncommitted; it need not be the
    project's own."""
    repository = git_root(path) or path
    return lambda line: say(f"{line} (uncommitted in {repository})")


def reference_resolver(project_root: Path) -> Callable[[Slug], str]:
    """How `validate` answers a reference into another project: `found`,
    `missing` or `unresolved`, opening each project once. A Jira-mode project
    is answered by its folders, so no reference needs Jira (TCW-71 R20). A
    project that is here but cannot be opened or read answers `broken`; one
    that cannot be looked up, `GraphError` with the reason (TCW-110 Design
    6.3)."""
    from tcw.errors import InheritedUnavailable
    from tcw.work.references import BROKEN, FOUND, MISSING, UNRESOLVED, GraphError
    opened: dict[str, object] = {}

    def resolve(ref: Slug) -> "str | GraphError":
        if ref.project not in opened:
            try:
                root, registry = _reading_root(ref.project, project_root)
                opened[ref.project] = item_folders(root, personal=False,
                                                   registry=registry)
            except (Unreachable, InheritedUnavailable):
                # Not here, or what it inherits is not: it could not be
                # checked, and the run goes on (TCW-109 Design 3.6).
                opened[ref.project] = UNRESOLVED
            except ProjectGraphError as error:
                opened[ref.project] = GraphError(str(error))
            except BackendError:
                opened[ref.project] = BROKEN
        other = opened[ref.project]
        if isinstance(other, (str, GraphError)):
            return other
        if isinstance(other, Path):
            return FOUND if link_exists(other, ref.folder) else MISSING
        try:
            other.read(ref.folder)
        except NotFound:
            return MISSING
        except BackendError:
            return BROKEN
        return FOUND

    return resolve
