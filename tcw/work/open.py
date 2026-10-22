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
from pathlib import Path
from typing import Callable

from tcw.errors import BackendError, ConfigError, NotFound, Refused, Unreachable
from tcw.store.fs import FsProjectRegistry, WorkLocation, git_root
from tcw.work.backend import WorkBackend
from tcw.work.config import WorkConfig
from tcw.work.jira.backend import JiraBackend, link_exists
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.model import Changes, Slug, inbox_stage


def work_path(project_root: Path) -> Path:
    """The project's work path, resolved as every store's location is
    (`work.path`, else `docs/work`, re-anchored in a linked worktree, else a
    declared repository's provisioned checkout). Raises `ValueError` when no
    usable directory is found."""
    return WorkLocation.open(Path(project_root)).root


def _layered(project_root: Path, personal: bool):
    """The project's configuration through the layered loader; `ConfigError`
    naming every problem. Personal layers apply only to the project a command
    acts on (TCW-72 Design 1.7)."""
    from tcw.config import effective, load_config
    config = (effective(project_root) if personal
              else load_config(project_root, personal=False))
    if config.problems:
        raise ConfigError(config.problems)
    return config


def read_work_config(project_root: Path, *, personal: bool = True) -> WorkConfig:
    """The project's parsed `work:` configuration, without opening the
    store: what the tag registry commands need."""
    return _layered(Path(project_root), personal).work


def open_backend(project_root: Path, *,
                 report: Callable[[str], None] | None = None,
                 personal: bool = True) -> WorkBackend:
    """The work backend of the project at `project_root`, from its effective
    configuration. `personal=False` for any project other than the one the
    command acts on: its backend is built from `tcw-config.yaml` alone, with
    no `user.name`."""
    root = Path(project_root)
    layered = _layered(root, personal)
    config = layered.work
    try:
        registry = FsProjectRegistry.open(root)
        if personal:
            # The project the command acts on answers for its whole graph, as
            # `taxonomy` and `validate` do; another project's broken child does
            # not stop reading that project from here.
            registry.require_valid()
        project = registry.current.id
        path = work_path(root)
    except ValueError as error:
        raise BackendError(str(error)) from None
    if config.backend == "jira":
        return JiraBackend(project, path, config, layered.jira, report=report,
                           root=root)
    return FsWorkBackend(project, path, config, layered.user_name, report=report)


def _registry(here: Path) -> FsProjectRegistry:
    try:
        return FsProjectRegistry.open(Path(here))
    except ValueError as error:
        raise BackendError(str(error)) from None


def open_project(project_id: str, here: Path) -> WorkBackend:
    """Another project's backend, for reading. `NotFound` when nothing here
    declares the id; `Unreachable` when it is declared but not on this
    machine."""
    registry = _registry(here)
    project = registry.get(project_id)
    if project is None:
        absent = registry.unreachable_project(project_id)
        if absent is not None and absent.message:
            # TCW-107 Design 6.2: where its manifest places it, and the
            # command that fetches it when the entry names a repository.
            raise Unreachable(absent.message, project=project_id,
                              repository=absent.repository)
        if absent or registry.entry(project_id):
            raise Unreachable(f"project '{project_id}' is declared but is not on "
                              f"this machine", project=project_id)
        raise NotFound(f"no project '{project_id}' is declared here")
    return open_backend(Path(project.locator), personal=False)


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
    """The first two conditions of delegation: declared, and not upstream."""
    if registry.get(project_id) is None and registry.entry(project_id) is None \
            and registry.unreachable_project(project_id) is None:
        raise Refused(f"no project '{project_id}' is declared here")
    reason = registry.read_only_reason(project_id)
    if reason is not None:
        raise Refused(f"{reason}; an upstream project is read-only from here")


def _check_target(registry: FsProjectRegistry, project_id: str) -> Path:
    """The five conditions of delegation, in order; the first that fails
    refuses. Returns the target's work path."""
    _check_declared(registry, project_id)
    project = registry.get(project_id)
    if project is None:
        entry = registry.entry(project_id)
        if entry is not None and entry.jira is not None:
            raise Refused(f"project '{project_id}' is not on this machine, and "
                          f"--blocks never creates a ticket")
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
    entry = registry.entry(project_id)
    if project is None and entry is not None and entry.jira is not None:
        from tcw.work.jira.tickets import delegate_to_jira
        return delegate_to_jira(project_id, title, request, priority,
                                block=entry.jira, report=say)
    if project is not None and read_work_config(Path(project.locator),
                                                personal=False).backend == "jira":
        from tcw.work.jira.tickets import delegate_to_jira
        return delegate_to_jira(project_id, title, request, priority,
                                root=Path(project.locator), report=say)
    path = _check_target(registry, project_id)
    backend = open_backend(Path(registry.get(project_id).locator),
                           report=_uncommitted_in(path, say), personal=False)
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
                        report=_uncommitted_in(path, say), personal=False)


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
    project that is here but cannot be opened or read answers `broken`."""
    from tcw.work.references import BROKEN, FOUND, MISSING, UNRESOLVED
    opened: dict[str, object] = {}

    def resolve(ref: Slug) -> str:
        if ref.project not in opened:
            try:
                opened[ref.project] = open_project(ref.project, project_root)
            except NotFound:
                opened[ref.project] = MISSING
            except Unreachable:
                opened[ref.project] = UNRESOLVED
            except BackendError:
                opened[ref.project] = BROKEN
        other = opened[ref.project]
        if isinstance(other, str):
            return other
        if isinstance(other, JiraBackend):
            return FOUND if link_exists(other.work_path, ref.folder) else MISSING
        try:
            other.read(ref.folder)
        except NotFound:
            return MISSING
        except BackendError:
            return BROKEN
        return FOUND

    return resolve
