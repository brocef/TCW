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
from typing import Any, Callable, Mapping

import yaml

from tcw import exit as codes
from tcw.errors import BackendError, NotFound, Refused, StateFileProblem, TcwError, UsageError
from tcw.ids import IdError
from tcw.output import shown
from tcw.work.advance import run_post
from tcw.work.config import WorkConfig
from tcw.work.jira import jql
from tcw.work.jira.backend import (
    KEY, STATE_FILE, JiraBackend, Refusal, _jira, _named, choose_transition, folder_key,
)
from tcw.work.jira.client import TrackerError, TrackerNotFound, TrackerRequestInvalid
from tcw.work.jira.mapping import document_text
from tcw.work.layout import Layout
from tcw.work.model import Slug, fitted_words, inbox_stage, start_stage


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
    accept without a further request (R19), oldest first. Without the TCW
    fields a ticket at the request status is not offered: nothing shows it
    is no other repository's item."""
    backend = jira_backend(backend)
    meta = backend.metadata()
    ids = meta.field_ids
    tcw_fields = backend.tcw_fields
    inbox_status = backend.statuses[inbox_stage()]
    request_status = backend.statuses[start_stage()]
    offered = (inbox_status, request_status) if tcw_fields else (inbox_status,)
    query = jql.inbox_query(backend.jira.project, ids["item"] if tcw_fields else None,
                            inbox_status, backend.jira.inbox_query)
    tcw_ids = [ids["project"], ids["item"]] if tcw_fields else []
    with _jira():
        issues = backend.client.search(query, ["summary", "status", "created", "reporter",
                                               "description", "project", *tcw_ids])
    found = []
    for issue in issues:
        fields = _fields(issue)
        key = str(issue.get("key"))
        project = fields.get("project")
        if not isinstance(project, dict) or project.get("key") != backend.jira.project:
            continue
        if _name(fields.get("status")) not in offered:
            continue
        if tcw_fields and (fields.get(ids["item"]) or fields.get(ids["project"]) not in (
                None, "", backend.project)):
            continue
        # Any folder named for the key, with its state file or without one,
        # as adopt refuses beside either: the list offers only what adopt
        # accepts (TCW-111 Design 6.4).
        if backend.key_folders(key):
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
          project_root: Path, report: Callable[[str], None] = _say) -> tuple[str, int]:
    """Make the ticket `key` an item at request. Returns the slug and the exit
    code: 0, or 6 when the item arrived but a `post` hook failed, which
    `report` is told (stderr for the CLI; the web viewer shows it)."""
    backend = jira_backend(backend)
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise UsageError(f"{key!r} is not a Jira key")
    meta = backend.metadata()
    ids = meta.field_ids
    # Without the TCW fields the folder alone records the adoption, and
    # neither field is read or written.
    tcw_fields = backend.tcw_fields
    inbox_status = backend.statuses[inbox_stage()]
    request_status = backend.statuses[start_stage()]
    # 1. Read the ticket.
    try:
        with _jira():
            issue = backend.client.issue(key, ("summary", "status", "project",
                                               *((ids["project"], ids["item"])
                                                 if tcw_fields else ())))
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
    tcw_project = fields.get(ids["project"]) if tcw_fields else None
    if tcw_project not in (None, "", backend.project):
        raise Refused(f"{key} belongs to TCW project {tcw_project!r}, not "
                      f"{backend.project!r}")
    # Every folder named for the key, with its state file or without one, at
    # any depth (TCW-111 Design 6.4): `lookup` answers only for items, and a
    # folder an interrupted run left without its state file is adopt's to
    # finish, or to refuse beside.
    named_for_key = backend.key_folders(key)
    if len(named_for_key) > 1:
        raise BackendError(f"two folders in {backend.work_path} carry the key {key}: "
                           f"{', '.join(named_for_key)}; rename or remove one")
    here = named_for_key[0] if named_for_key else None
    if here is not None:
        _refuse_unreadable_state(backend.work_path / here / STATE_FILE)
    tcw_item = fields.get(ids["item"]) if tcw_fields else None
    # Statuses of stages past request: adopting from one would skip stages.
    moved_on = set(backend.statuses.values()) - {inbox_status, request_status}
    resuming = False
    if tcw_item:
        named = _own_slug(backend, tcw_item, key)
        if named is None:
            raise Refused(f"{key} is already an item: its TCW Item is {tcw_item!r}")
        if here is not None and here != named.folder:
            raise Refused(f"a folder for {key} already exists here ({here}), but the "
                          f"ticket names {named.folder}")
        # A folder without its state file is an adoption that stopped part way, but
        # only at a status nothing has moved it on from (Design 7.2).
        unfinished = (here is not None and status not in moved_on
                      and not (backend.work_path / here / STATE_FILE).is_file())
        if here is not None and status != inbox_status and not unfinished:
            raise Refused(f"{key} is already the item {named}")
        slug, resuming = named, True
    elif not tcw_fields and here is not None:
        # Without the TCW fields the folder is made before the ticket moves
        # and its state file after, so one without its state file, at a
        # status nothing has moved it on from, is an adoption that stopped
        # part way.
        if status in moved_on or (backend.work_path / here / STATE_FILE).is_file():
            raise Refused(f"a folder for {key} already exists here: {here}")
        slug, resuming = Slug(backend.project, here), True
    else:
        if here is not None:
            raise Refused(f"a folder for {key} already exists here: {here}")
        if not tcw_fields and status == request_status:
            raise Refused(f"{key} is at {request_status!r} with no folder here, so it "
                          f"may be an item of another repository sharing Jira project "
                          f"{backend.jira.project}; if it is not, move it back to "
                          f"{inbox_status!r} in Jira, then adopt it")
        # The key is known, so the room is too: refused before any edit
        # (TCW-111 Design 4.3, choice 2).
        words = fitted_words(str(fields.get('summary') or key), project=backend.project,
                             parent=None, prefix=len(key) + 1)
        slug = Slug(backend.project, f"{key}-{words}")
    # A ticket this project made, whose create or delegation stopped before it
    # set TCW Item, may sit at a first status that no stage maps (Design 7.2).
    ours = tcw_project == backend.project and not tcw_item and \
        status not in backend.statuses.values()
    chosen = None
    if status != request_status:
        if not resuming and not ours and status != inbox_status:
            either = (f"{inbox_status!r} or {request_status!r}" if tcw_fields
                      else repr(inbox_status))
            raise Refused(f"{key} is at {status!r}; only a ticket at {either} can be "
                          f"adopted, since adopting one further along would skip "
                          f"stages with no trace")
        with _jira():
            chosen = choose_transition(backend.client.transitions(key), request_status)
        if isinstance(chosen, Refusal):
            raise Refused(f"cannot adopt {key}: {chosen.message}")
    if resuming:
        report(f"resuming the adoption of {key} as {slug}")
    # 3. Set TCW Project and TCW Item in one edit.
    if tcw_fields and (not resuming or tcw_project != backend.project):
        with _jira():
            backend.client.edit_issue(key, {ids["project"]: backend.project,
                                            ids["item"]: str(slug)})
    # 4. Write the folder and its state file, or finish a folder left without
    # one. Without the TCW fields only the folder is made here, and its state
    # file once the ticket has moved, so a stop in between leaves what the
    # resume above recognises.
    unwritten = not (backend.work_path / slug.folder / STATE_FILE).is_file()
    if unwritten:
        try:
            if tcw_fields:
                backend._item_file(slug.folder, key, resume=True)
            else:
                _bare_folder(backend, slug.folder)
        except OSError as error:
            done = f"{key} now names {slug}" if tcw_fields else \
                f"nothing changed in Jira for {key}"
            raise _named(BackendError(
                f"{done}, but its folder could not be written: "
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
        except TrackerError as error:
            # The folder is written, so the failure still names the item
            # (Design 1.8).
            try:
                with _jira():
                    raise error
            except TcwError as mapped:
                raise _named(type(mapped)(
                    f"{slug} is made, but moving it to {start_stage()} did not "
                    f"complete: {mapped}; run `tcw work tickets adopt {key}` again"),
                    str(slug)) from None
    if unwritten and not tcw_fields:
        try:
            backend._item_file(slug.folder, key, resume=True)
        except OSError as error:
            raise _named(BackendError(
                f"{key} is at {start_stage()}, but the state file of {slug} could not "
                f"be written: {error}; run `tcw work tickets adopt {key}` again"),
                key) from None
    try:
        item = backend.read(slug.folder)
    except TcwError as error:
        raise _named(type(error)(f"{slug} is made, but could not be read back: "
                                 f"{error}; check it with `tcw work show {slug}`"),
                     str(slug)) from None
    if item.stage != start_stage():
        raise _named(BackendError(f"{slug} is made, but Jira reports it at "
                                  f"{item.stage or 'no stage'}, not {start_stage()}"),
                     str(slug))
    # 6. Run the request stage's post hooks, as a move there would.
    failure = run_post(config, layout, project_root, replace(item, stage=from_stage),
                       start_stage())
    if failure:
        report(f"adopted {key} as {slug}, but {failure}")
        return str(slug), codes.MOVED_WITH_PROBLEM
    return str(slug), codes.OK


def _bare_folder(backend: JiraBackend, folder: str) -> None:
    """An adopted item's folder, without its state file yet."""
    path = backend.work_path / folder
    backend._forget_walk()
    if not path.is_dir():
        path.mkdir(parents=True)
        backend.report(f"created {shown(path)}/")


def _refuse_unreadable_state(path: Path) -> None:
    """Adopt writes nothing over a state file whose version this TCW cannot
    read (TCW-111 Design 1.5): exit 1 with the version check's message."""
    from tcw.object_folders import read_state
    try:
        _, problem = read_state(path)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return                       # `tcw validate` reports a file that cannot be read
    if problem is not None:
        raise StateFileProblem(path, problem)


def _own_slug(backend: JiraBackend, value: Any, key: str) -> Slug | None:
    """The slug TCW Item names, when it is an item of this project for `key`."""
    try:
        slug = Slug.stored(value)
    except IdError:
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


def is_assignable(backend: JiraBackend, account_id: str) -> bool:
    """Whether `account_id` is exactly the account id of someone assignable
    in the project: a name, or someone who cannot be assigned, is not."""
    backend = jira_backend(backend)
    with _jira():
        found = backend.client.assignable_users(backend.jira.project, "", 1,
                                                account_id=account_id)
    return any(isinstance(u, dict) and u.get("accountId") == account_id for u in found)


def create_fields(backend: JiraBackend) -> tuple[str, ...]:
    """Which of priority, effort and complexity a new ticket can carry: the
    create screen's Priority field, and the size fields the configuration
    maps. A form offers only these, since `new` refuses the others."""
    backend = jira_backend(backend)
    meta = backend.metadata()
    found = ("priority",) if meta.has_priority else ()
    return found + tuple(name for name in ("effort", "complexity")
                         if name in meta.field_ids)
