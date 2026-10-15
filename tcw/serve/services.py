"""The operations the web viewer calls, gathered in one value.

Every one of them is an operation the CLI also uses: the backend and its
operations, delegation into another project, and the Jira-only helpers beside
`tickets list`. (A `blocks` link into another project goes through the
function behind `tcw work edit --blocks`, which opens that project with
`open_for_update` itself.) The server holds no second
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


def _ticket_link(backend, folder: str):
    from tcw.work.jira.tickets import ticket_link
    return ticket_link(backend, folder)


def _user_name(backend, account_id: str):
    from tcw.work.jira.tickets import user_name
    return user_name(backend, account_id)


def _assignable_users(backend, query: str, limit: int):
    from tcw.work.jira.tickets import assignable_users
    return assignable_users(backend, query, limit)


def _is_assignable(backend, account_id: str) -> bool:
    from tcw.work.jira.tickets import is_assignable
    return is_assignable(backend, account_id)


def _inbox(backend):
    from tcw.work.jira.tickets import inbox
    return inbox(backend)


def _adopt(backend, key: str, root: Path) -> tuple[str, int, str | None]:
    """`tickets adopt`, which runs the request stage's post hooks as the CLI's
    does. Also returns what a failed hook reported, for the page to show."""
    from tcw.work.jira.tickets import adopt
    said: list[str] = []
    slug, code = adopt(backend, key, config=backend.config, layout=backend.layout,
                       project_root=root, report=said.append)
    for line in said:
        _stderr(line)
    return slug, code, (said[-1] if code and said else None)


def _create_fields(backend):
    from tcw.work.jira.tickets import create_fields
    return create_fields(backend)


@dataclass(frozen=True)
class Services:
    open_backend: Callable[[Path], Any] = _open_backend
    open_project: Callable[[str, Path], Any] = _open_project
    delegate: Callable[..., str] = _delegate
    ticket_link: Callable[[Any, str], tuple[str, str]] = _ticket_link
    user_name: Callable[[Any, str], "str | None"] = _user_name
    assignable_users: Callable[[Any, str, int], list] = _assignable_users
    is_assignable: Callable[[Any, str], bool] = _is_assignable
    inbox: Callable[[Any], tuple] = _inbox
    adopt: Callable[[Any, str, Path], tuple] = _adopt
    create_fields: Callable[[Any], tuple] = _create_fields
