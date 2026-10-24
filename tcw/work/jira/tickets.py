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
from tcw.work.advance import run_post
from tcw.work.config import WorkConfig
from tcw.work.jira import jql
from tcw.work.jira.backend import (
    KEY, STATE_FILE, JiraBackend, Refusal, _jira, _named, choose_transition, folder_key,
)
from tcw.work.jira.client import (
    JiraClient, TrackerError, TrackerNotFound, TrackerRequestInvalid,
)
from tcw.work.jira.mapping import document_text, text_document
from tcw.work.layout import Layout
from tcw.work.model import (
    DEFAULT_PRIORITY, Slug, check_encodable, inbox_stage, start_stage,
    title_words,
)


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
    tcw_item = fields.get(ids["item"])
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
    else:
        if here is not None:
            raise Refused(f"a folder for {key} already exists here: {here}")
        slug = Slug(backend.project, f"{key}-{title_words(str(fields.get('summary') or key))}")
    # A ticket this project made, whose create or delegation stopped before it
    # set TCW Item, may sit at a first status that no stage maps (Design 7.2).
    ours = tcw_project == backend.project and not tcw_item and \
        status not in backend.statuses.values()
    chosen = None
    if status != request_status:
        if not resuming and not ours and status != inbox_status:
            raise Refused(f"{key} is at {status!r}; only a ticket at {inbox_status!r} "
                          f"or {request_status!r} can be adopted, since adopting one "
                          f"further along would skip stages with no trace")
        with _jira():
            chosen = choose_transition(backend.client.transitions(key), request_status)
        if isinstance(chosen, Refusal):
            raise Refused(f"cannot adopt {key}: {chosen.message}")
    if resuming:
        report(f"resuming the adoption of {key} as {slug}")
    # 3. Set TCW Project and TCW Item in one edit.
    if not resuming or tcw_project != backend.project:
        with _jira():
            backend.client.edit_issue(key, {ids["project"]: backend.project,
                                            ids["item"]: str(slug)})
    # 4. Write the folder and its state file, or finish a folder left without one.
    if not (backend.work_path / slug.folder / STATE_FILE).is_file():
        try:
            backend._item_file(slug.folder, key, resume=True)
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


# -- delegation into a Jira-mode project (Design 8) ----------------------------------------


def delegate_to_jira(project_id: str, title: str, request: str | None,
                     priority: str | None, *, root: Path,
                     report: Callable[[str], None] = _say) -> str:
    """Create a ticket in the inbox of the Jira-mode project at `root`, on
    this machine, and make it an item there when its checkout allows.
    Returns the slug, or the key when the ticket stays in the inbox. Runs no
    gates and no hooks: creation is not a move."""
    if not isinstance(title, str) or not title.strip():
        raise UsageError("a title must not be empty")
    check_encodable(title, "the title")
    if request is not None:
        check_encodable(request, "the request")
    from tcw.work.open import open_backend
    # Another project: read from its tcw-config.yaml alone (TCW-72 AC 9).
    backend = jira_backend(open_backend(root, report=report, personal=False))
    site, jira_project = backend.jira.site, backend.jira.project
    client, priorities = backend.client, backend.jira.priorities
    meta = backend.metadata()
    issue_type, field = meta.issue_type.id, meta.field_ids["project"]
    has_priority = meta.has_priority
    inbox_status = backend.statuses[inbox_stage()]
    if priority is not None and not has_priority:
        raise Refused(f"Jira project {jira_project} has no Priority field, so an item "
                      f"there has no priority to set")
    # 2. Create the ticket.
    fields: dict = {"project": {"key": jira_project}, "issuetype": {"id": issue_type},
                    "summary": title, field: project_id}
    if request is not None:
        fields["description"] = text_document(request)
    if has_priority:
        fields["priority"] = {"name": priorities[priority or DEFAULT_PRIORITY]}
    with _jira():
        created = client.create_issue(fields)
    key = created.get("key") if isinstance(created, dict) else None
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise BackendError(f"Jira's answer to the create request names no ticket key; a "
                           f"ticket may have been created in {jira_project}: look for it")
    report(f"created Jira ticket {site}/browse/{key} for {project_id}")
    # 3. Place it at the target's inbox status.
    try:
        _move_to(client, key, inbox_status)
    except TcwError as error:
        raise _named(error, key) from None
    # 4. Try to create the item.
    why = _cannot_make_item(backend, project_id, key)
    if why is not None:
        report(f"{key} stays in {project_id}'s Jira inbox: {why}")
        return key
    slug = Slug(project_id, f"{key}-{title_words(title)}")
    try:
        with _jira():
            client.edit_issue(key, {backend.metadata().field_ids["item"]: str(slug)})
        backend._item_file(slug.folder, key)
        _move_to(client, key, backend.statuses[start_stage()])
    except (TcwError, OSError) as error:
        raise _named(BackendError(f"created {key} for {project_id}, but did not finish "
                                  f"making it the item {slug}: {error}; finish with "
                                  f"`tcw work tickets adopt {key}` there"), key) from None
    report(f"the new files in {backend.work_path / slug.folder} are left uncommitted; "
           f"record them in that project's version control before filing into "
           f"{project_id} again, or the next ticket stays in its Jira inbox")
    return str(slug)


def _move_to(client: JiraClient, key: str, status: str) -> None:
    """Move `key` to `status` by the choice rule, unless it is there."""
    with _jira():
        issue = client.issue(key, ("status",))
        if _name(_fields(issue).get("status")) == status:
            return
        chosen = choose_transition(client.transitions(key), status)
    if isinstance(chosen, Refusal):
        raise Refused(f"created {key}, but cannot move it to {status!r}: "
                      f"{chosen.message}")
    with _jira():
        client.apply_transition(key, chosen.id)


def _cannot_make_item(backend: JiraBackend, project_id: str,
                      key: str) -> str | None:
    """Why the item cannot be made in the target here, or None (Design 8
    step 4)."""
    from tcw.work.open import uncommitted_changes
    if not backend.work_path.is_dir():
        return f"{project_id} has no work store at {backend.work_path}"
    try:
        changed = uncommitted_changes(backend.work_path, project_id)
    except (Refused, BackendError) as error:
        return str(error)
    if changed:
        return (f"{project_id}'s work store has uncommitted changes: "
                f"{', '.join(changed)}")
    with _jira():
        chosen = choose_transition(backend.client.transitions(key),
                                   backend.statuses[start_stage()])
    if isinstance(chosen, Refusal):
        return chosen.message
    return None
