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

from tcw.errors import BackendError, NotFound, Refused, Unreachable
from tcw.store.fs import (
    SENTINEL, FsProjectRegistry, WorkLocation, git_root, load_config,
)
from tcw.work.backend import WorkBackend
from tcw.work.config import WorkConfig, parse_work_config
from tcw.work.jira.backend import JiraBackend
from tcw.work.jira.config import JiraConfig, parse_jira_config
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.model import Changes, inbox_stage


def work_path(project_root: Path) -> Path:
    """The project's work path, resolved as every store's location is
    (`work.path`, else `docs/work`, re-anchored in a linked worktree, else a
    declared repository's provisioned checkout). Raises `ValueError` when no
    usable directory is found."""
    return WorkLocation.open(Path(project_root)).root


def read_work_config(project_root: Path) -> WorkConfig:
    """The `work:` section of the project's `tcw-config.yaml`, parsed, without
    opening the store: what the tag registry commands need."""
    root = Path(project_root)
    try:
        raw = load_config(root / SENTINEL)
    except ValueError as error:
        raise BackendError(str(error)) from None
    config, problems = parse_work_config(raw.get("work") if isinstance(raw, dict)
                                         else None)
    if problems:
        raise BackendError(f"{root / SENTINEL}: " +
                           "; ".join(str(p) for p in problems))
    return config


def read_jira_config(project_root: Path, config: WorkConfig) -> JiraConfig:
    """`work.jira` of a project whose `work.backend` is `jira`, parsed;
    `BackendError` naming every problem."""
    jira, problems = parse_jira_config(config.jira)
    if problems:
        raise BackendError(f"{Path(project_root) / SENTINEL}: " +
                           "; ".join(str(p) for p in problems))
    return jira


def open_backend(project_root: Path, *,
                 report: Callable[[str], None] | None = None) -> WorkBackend:
    """The work backend of the project at `project_root`, from its tracked
    `tcw-config.yaml`."""
    root = Path(project_root)
    config = read_work_config(root)
    jira = read_jira_config(root, config) if config.backend == "jira" else None
    try:
        project = FsProjectRegistry.open(root).current.id
        path = work_path(root)
    except ValueError as error:
        raise BackendError(str(error)) from None
    if jira is not None:
        return JiraBackend(project, path, config, jira, report=report, root=root)
    return FsWorkBackend(project, path, config, report=report)


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
        if registry.unreachable_project(project_id) or registry.entry(project_id):
            raise Unreachable(f"project '{project_id}' is declared but is not on "
                              f"this machine")
        raise NotFound(f"no project '{project_id}' is declared here")
    return open_backend(Path(project.locator))


# ---------------------------------------------------------------------------
# Writing into another project


def uncommitted_changes(path: Path, project_id: str | None = None) -> list[str]:
    """Paths under `path` that git has not committed, ignored files excepted.

    Refuses when `path` is not inside a git repository, because then it cannot
    be checked. Runs `git --no-optional-locks status`, which neither refreshes
    the index nor takes `index.lock` in someone else's repository.
    """
    who = f"`{project_id}`" if project_id else "the project"
    repository = git_root(Path(path))
    if repository is None:
        raise Refused(f"{who}'s work store is not in a git repository, so TCW "
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
        raise Refused(f"project '{project_id}' is declared but is not on this "
                      f"machine")
    try:
        path = work_path(Path(project.locator))
    except ValueError:
        raise Refused(f"'{project_id}' has no work store on this machine") from None
    changed = uncommitted_changes(path, project_id)
    if changed:
        raise Refused(f"`{project_id}`'s work store has uncommitted changes: "
                      f"{', '.join(changed)} — commit or remove them in that "
                      f"project first")
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
    if project is not None and read_work_config(Path(project.locator)).backend == "jira":
        from tcw.work.jira.tickets import delegate_to_jira
        return delegate_to_jira(project_id, title, request, priority,
                                root=Path(project.locator), report=say)
    path = _check_target(registry, project_id)
    project = registry.get(project_id)
    root = Path(project.locator)
    # The repository holding the work store, which is where the new files are
    # left uncommitted; it need not be the project's own.
    repository = git_root(path) or path
    backend = open_backend(root, report=lambda line: say(
        f"{line} (uncommitted in {repository})"))
    props = Changes() if priority is None else Changes(priority=priority)
    item = backend.create(title, props, stage=inbox_stage(), request=request)
    return str(item.slug)


def open_for_update(project_id: str, here: Path) -> WorkBackend:
    """Another project's backend, so `edit --blocks` can change an existing
    item there. It never creates anything."""
    registry = _registry(here)
    _check_target(registry, project_id)
    return open_backend(Path(registry.get(project_id).locator))
