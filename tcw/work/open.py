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
from tcw.store.base import StoreLocationUnusable
from tcw.store.fs import (
    SENTINEL, FsProjectRegistry, anchor_configured_path, git_root, load_config,
    resolve_store,
)
from tcw.work.backend import WorkBackend
from tcw.work.config import parse_work_config
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.model import Changes, inbox_stage


class _WorkPath:
    """The work component as `resolve_store` asks for it: where the work path
    is, and whether it is usable. Usable means the directory is there; an
    empty store is a real state, and 3.0 has no status folders to look for."""

    COMPONENT = "work"

    @classmethod
    def _local_root(cls, node_root: Path, configured: str | None) -> Path:
        if configured is None:
            return node_root / "docs" / cls.COMPONENT
        value = Path(configured).expanduser()
        if value.is_absolute():
            return value
        return anchor_configured_path(node_root, value) / value

    @classmethod
    def _open_at(cls, raw_root: Path, node_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True, declaration=None,
                 _walk=None) -> Path:
        if not raw_root.is_dir():
            raise StoreLocationUnusable(
                f"{config_path}: work.path is not a directory: {raw_root}")
        return raw_root.resolve()


def work_path(project_root: Path) -> Path:
    """The project's work path, resolved as every store's location is
    (`work.path`, else `docs/work`, re-anchored in a linked worktree, else a
    declared repository's provisioned checkout). Raises `ValueError` when no
    usable directory is found."""
    return resolve_store(_WorkPath, Path(project_root))


def open_backend(project_root: Path, *,
                 report: Callable[[str], None] | None = None) -> WorkBackend:
    """The work backend of the project at `project_root`, from its tracked
    `tcw-config.yaml`."""
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
    if config.backend != "filesystem":
        raise BackendError(f"{root / SENTINEL}: work.backend is "
                           f"{config.backend!r}; the Jira backend arrives with "
                           f"TCW-71")
    try:
        project = FsProjectRegistry.open(root).current.id
        path = work_path(root)
    except ValueError as error:
        raise BackendError(str(error)) from None
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
    who = f"'{project_id}'" if project_id else "the project"
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


def _check_target(registry: FsProjectRegistry, project_id: str, *,
                  creating: bool) -> Path:
    """The five conditions of delegation, in order; the first that fails
    refuses. Returns the target's work path."""
    if registry.get(project_id) is None and registry.entry(project_id) is None \
            and registry.unreachable_project(project_id) is None:
        raise Refused(f"no project '{project_id}' is declared here")
    reason = registry.read_only_reason(project_id)
    if reason is not None:
        raise Refused(f"{reason}; an upstream project is read-only from here")
    project = registry.get(project_id)
    if project is None:
        entry = registry.entry(project_id)
        if entry is not None and entry.jira is not None:
            if creating:
                raise BackendError("Jira delegation arrives with the Jira backend")
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
        raise Refused(f"'{project_id}''s work store has uncommitted changes: "
                      f"{', '.join(changed)} — commit or remove them in that "
                      f"project first")
    return path


def delegate(project_id: str, title: str, request: str | None,
             priority: str | None, *, here: Path,
             report: Callable[[str], None] | None = None) -> str:
    """Create an item in another project's inbox, and return its full slug."""
    registry = _registry(here)
    _check_target(registry, project_id, creating=True)
    project = registry.get(project_id)
    root = Path(project.locator)
    repository = git_root(root) or root
    say = report or (lambda line: print(line, file=sys.stderr))
    backend = open_backend(root, report=lambda line: say(
        f"{line} (uncommitted in {repository})"))
    props = Changes() if priority is None else Changes(priority=priority)
    item = backend.create(title, props, stage=inbox_stage(), request=request)
    return str(item.slug)


def open_for_update(project_id: str, here: Path) -> WorkBackend:
    """Another project's backend, so `edit --blocks` can change an existing
    item there. It never creates anything."""
    registry = _registry(here)
    _check_target(registry, project_id, creating=False)
    return open_backend(Path(registry.get(project_id).locator))
