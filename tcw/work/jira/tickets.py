"""Jira-only commands and helpers, outside the backend interface (TCW-71
Design 7): the Jira inbox (`tickets list`), adopting a ticket as an item
(`tickets adopt`), and three helpers for display.

Each takes a `JiraBackend`; anything else is a usage error, since none of these
exists in filesystem mode.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from tcw import exit as codes
from tcw.errors import BackendError, NotFound, Refused, UsageError
from tcw.work.advance import run_post
from tcw.work.config import WorkConfig
from tcw.work.jira import jql
from tcw.work.jira.backend import (
    KEY, JiraBackend, Refusal, _jira, _named, choose_transition, folder_key,
)
from tcw.work.jira.client import TrackerError, TrackerNotFound, TrackerRequestInvalid
from tcw.work.jira.mapping import document_text
from tcw.work.layout import Layout
from tcw.work.model import Slug, inbox_stage, start_stage, title_words


def _say(line: str) -> None:
    print(line, file=sys.stderr)


def jira_backend(backend: Any) -> JiraBackend:
    if not isinstance(backend, JiraBackend):
        raise UsageError("this is for a project whose work.backend is jira; this "
                         "project keeps its items in the filesystem")
    return backend


def _fields(issue: Mapping) -> Mapping:
    fields = issue.get("fields")
    return fields if isinstance(fields, dict) else {}


def _name(value: Any) -> str | None:
    return value.get("name") if isinstance(value, dict) else None


# -- tickets list (Design 7.1) -----------------------------------------------------------


def inbox(backend: JiraBackend) -> tuple[list[dict], str]:
    """The Jira inbox, and the JQL that found it: only tickets `adopt` would
    accept without a further request (R19), oldest first."""
    backend = jira_backend(backend)
    meta = backend.metadata()
    ids = meta.field_ids
    inbox_status = backend.statuses[inbox_stage()]
    request_status = backend.statuses[start_stage()]
    query = jql.inbox_query(backend.jira.project, ids["item"], inbox_status,
                            backend.jira.inbox_query)
    with _jira():
        issues = backend.client.search(query, ["summary", "status", "created", "reporter",
                                               "description", "project", ids["project"],
                                               ids["item"]])
    found = []
    for issue in issues:
        fields = _fields(issue)
        key = str(issue.get("key"))
        project = fields.get("project")
        if not isinstance(project, dict) or project.get("key") != backend.jira.project:
            continue
        if _name(fields.get("status")) not in (inbox_status, request_status):
            continue
        if fields.get(ids["item"]) or fields.get(ids["project"]) not in (None, "",
                                                                          backend.project):
            continue
        if backend.lookup(key) is not None:
            continue
        description = document_text(fields.get("description"))
        reporter = fields.get("reporter")
        found.append({
            "key": key,
            "summary": fields.get("summary"),
            "status": _name(fields.get("status")),
            "created": fields.get("created"),
            "reporter": reporter.get("displayName") if isinstance(reporter, dict) else None,
            "url": f"{backend.jira.site}/browse/{key}",
            "description": description if description.strip() else None,
        })
    return found, query


# -- tickets adopt (Design 7.2) --------------------------------------------------------------


def adopt(backend: JiraBackend, key: str, *, config: WorkConfig, layout: Layout,
          project_root: Path) -> tuple[str, int]:
    """Make the ticket `key` an item at request. Returns the slug and the exit
    code: 0, or 6 when the item arrived but a `post` hook failed."""
    backend = jira_backend(backend)
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise UsageError(f"{key!r} is not a Jira key")
    meta = backend.metadata()
    ids = meta.field_ids
    inbox_status = backend.statuses[inbox_stage()]
    request_status = backend.statuses[start_stage()]
    # 1. Read the ticket.
    try:
        with _jira():
            issue = backend.client.issue(key, ("summary", "status", "project",
                                               ids["project"], ids["item"]))
    except NotFound:
        raise NotFound(f"Jira has no ticket {key}, or this account cannot see it") \
            from None
    fields = _fields(issue)
    status = _name(fields.get("status"))
    # 2. Refuse, changing nothing.
    project = fields.get("project")
    if not isinstance(project, dict) or project.get("key") != backend.jira.project:
        raise Refused(f"{key} is in Jira project {_key_of(project)}, not "
                      f"{backend.jira.project}")
    tcw_project = fields.get(ids["project"])
    if tcw_project not in (None, "", backend.project):
        raise Refused(f"{key} belongs to TCW project {tcw_project!r}, not "
                      f"{backend.project!r}")
    here = backend.lookup(key)
    tcw_item = fields.get(ids["item"])
    resuming = False
    if tcw_item:
        named = _own_slug(backend, tcw_item, key)
        if named is None:
            raise Refused(f"{key} is already an item: its TCW Item is {tcw_item!r}")
        if here is not None and here != named.folder:
            raise Refused(f"a folder for {key} already exists here ({here}), but the "
                          f"ticket names {named.folder}")
        if here is not None and status != inbox_status:
            raise Refused(f"{key} is already the item {named}")
        slug, resuming = named, True
    else:
        if here is not None:
            raise Refused(f"a folder for {key} already exists here: {here}")
        slug = Slug(backend.project, f"{key}-{title_words(str(fields.get('summary') or key))}")
    chosen = None
    if status != request_status:
        if not resuming and status != inbox_status:
            raise Refused(f"{key} is at {status!r}; only a ticket at {inbox_status!r} "
                          f"or {request_status!r} can be adopted, since adopting one "
                          f"further along would skip stages with no trace")
        with _jira():
            chosen = choose_transition(backend.client.transitions(key), request_status)
        if isinstance(chosen, Refusal):
            raise Refused(f"cannot adopt {key}: {chosen.message}")
    if resuming:
        _say(f"resuming the adoption of {key} as {slug}")
    # 3. Set TCW Project and TCW Item in one edit.
    if not resuming or tcw_project != backend.project:
        with _jira():
            backend.client.edit_issue(key, {ids["project"]: backend.project,
                                            ids["item"]: str(slug)})
    # 4. Write the folder and item.yaml.
    if not (backend.work_path / slug.folder).is_dir():
        try:
            backend._item_file(slug.folder, key)
        except OSError as error:
            raise _named(BackendError(
                f"{key} now names {slug}, but its folder could not be written: "
                f"{error}; run `tcw work tickets adopt {key}` again"), key) from None
    # TCW_FROM_STAGE is the stage step 5 moved the ticket from, and empty when
    # it was already at request (Design 7.2).
    from_stage = (None if chosen is None else
                  {name: stage for stage, name in backend.statuses.items()}.get(status))
    # 5. Move to request, and read the status back.
    if chosen is not None:
        try:
            backend.client.apply_transition(key, chosen.id)
        except TrackerRequestInvalid as error:
            raise _named(Refused(f"{slug} is made, but Jira refused to move it to "
                                 f"{start_stage()}: {error}; fix the workflow, then run "
                                 f"`tcw work tickets adopt {key}` again"), str(slug)) \
                from None
        except TrackerError:
            with _jira():
                raise
    item = backend.read(slug.folder)
    if item.stage != start_stage():
        raise _named(BackendError(f"{slug} is made, but Jira reports it at "
                                  f"{item.stage or 'no stage'}, not {start_stage()}"),
                     str(slug))
    # 6. Run the request stage's post hooks, as a move there would.
    failure = run_post(config, layout, project_root, replace(item, stage=from_stage),
                       start_stage())
    if failure:
        _say(f"adopted {key} as {slug}, but {failure}")
        return str(slug), codes.MOVED_WITH_PROBLEM
    return str(slug), codes.OK


def _own_slug(backend: JiraBackend, value: Any, key: str) -> Slug | None:
    """The slug TCW Item names, when it is an item of this project for `key`."""
    try:
        slug = Slug.parse(value, backend.project)
    except (UsageError, TypeError):
        return None
    if slug.project != backend.project or folder_key(slug.folder) != key:
        return None
    return slug


def _key_of(project: Any) -> str:
    return str(project.get("key")) if isinstance(project, dict) else "unknown"


# -- helpers for display (Design 7.3) ------------------------------------------------------


def ticket_link(backend: JiraBackend, folder: str) -> tuple[str, str]:
    """`("Jira", "<site>/browse/<KEY>")`, from the folder name alone."""
    backend = jira_backend(backend)
    key = folder_key(folder)
    if key is None:
        raise NotFound(f"{folder} is not a Jira item folder")
    return "Jira", f"{backend.jira.site}/browse/{key}"


def user_name(backend: JiraBackend, account_id: str) -> str | None:
    """A person's display name: from what this command has already read,
    else one request. None when Jira gives none."""
    backend = jira_backend(backend)
    if account_id in backend.names:
        return backend.names[account_id]
    with _jira():
        try:
            user = backend.client.user(account_id)
        except TrackerNotFound:
            return None
    name = user.get("displayName") if isinstance(user, dict) else None
    if isinstance(name, str) and name:
        backend.names[account_id] = name
        return name
    return None


def assignable_users(backend: JiraBackend, query: str,
                     limit: int = 20) -> list[tuple[str, str]]:
    """The project's assignable users matching `query`."""
    backend = jira_backend(backend)
    with _jira():
        found = backend.client.assignable_users(backend.jira.project, query, limit)
    return [(str(u["accountId"]), str(u.get("displayName") or u["accountId"]))
            for u in found if isinstance(u, dict) and u.get("accountId")]
