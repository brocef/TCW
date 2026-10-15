"""The operations the web viewer calls, gathered in one value.

Every one of them is an operation the CLI also uses: the backend and its
eleven operations, delegation and `open_for_update` for another project, and
the Jira-only helpers beside `tickets list`. The server holds no second
version of any. Tests replace them through this value, to serve TCW-69's
in-memory backend with the spec's stubs for the Jira-only helpers.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _stderr(line: str) -> None:
    print(line, file=sys.stderr)


def _open_backend(root: Path):
    from tcw.work.open import open_backend
    return open_backend(root, report=_stderr)


def _open_project(project_id: str, root: Path):
    from tcw.work.open import open_project
    return open_project(project_id, root)


def _delegate(project_id: str, title: str, request: str | None,
              priority: str | None, root: Path) -> str:
    from tcw.work.open import delegate
    return delegate(project_id, title, request, priority, here=root, report=_stderr)


def _open_for_update(project_id: str, root: Path):
    from tcw.work.open import open_for_update
    return open_for_update(project_id, root, report=_stderr)


def _ticket_link(backend, folder: str):
    from tcw.work.jira.tickets import ticket_link
    return ticket_link(backend, folder)


def _user_name(backend, account_id: str):
    from tcw.work.jira.tickets import user_name
    return user_name(backend, account_id)


def _assignable_users(backend, query: str, limit: int):
    from tcw.work.jira.tickets import assignable_users
    return assignable_users(backend, query, limit)


def _inbox(backend):
    from tcw.work.jira.tickets import inbox
    return inbox(backend)


def _adopt(backend, key: str, root: Path):
    from tcw.work.jira.tickets import adopt
    return adopt(backend, key, config=backend.config, layout=backend.layout,
                 project_root=root)


def _create_fields(backend):
    from tcw.work.jira.tickets import create_fields
    return create_fields(backend)


@dataclass(frozen=True)
class Services:
    open_backend: Callable[[Path], Any] = _open_backend
    open_project: Callable[[str, Path], Any] = _open_project
    delegate: Callable[..., str] = _delegate
    open_for_update: Callable[[str, Path], Any] = _open_for_update
    ticket_link: Callable[[Any, str], tuple[str, str]] = _ticket_link
    user_name: Callable[[Any, str], "str | None"] = _user_name
    assignable_users: Callable[[Any, str, int], list] = _assignable_users
    inbox: Callable[[Any], tuple] = _inbox
    adopt: Callable[[Any, str, Path], tuple] = _adopt
    create_fields: Callable[[Any], tuple] = _create_fields
