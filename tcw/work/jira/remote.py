"""`tcw validate --remote` for a Jira-mode project (TCW-71 Design 9.2).

Every request here is a read. Each check returns findings, and what passed or
was skipped is narrated for stderr, never stdout. A check that cannot run
because Jira cannot be reached stops the rest; what was found before that is
kept, with one `unresolved` finding for the project.

The checks run in this order: access (1); fields on the create screen (2);
the items' tickets are read next, since they decide which issue types are
checked (6); then the edit screens (2), statuses (3), moves (4, 5), items and
tickets (7), and TCW-69's model checks (8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from tcw.errors import BackendError, NotFound, TcwError, Unreachable
from tcw.findings import Finding
from tcw.work.jira import jql
from tcw.work.jira.backend import (
    KEY_FOLDER, IssueType, JiraBackend, Refusal, _chunks, _jira, choose_transition,
    field_id, folder_key, link_exists,
)
from tcw.work.jira.client import (
    TrackerNotFound, TrackerPermissionError, TrackerRequestInvalid,
)
from tcw.work.jira.mapping import BLOCKS, read_fields, scale_name
from tcw.work.layout import Layout
from tcw.work.model import (
    SIZES, TERMINAL, Slug, completion_stage, discard_stage, flow_order, inbox_stage,
    stage as table_stage,
)
from tcw.work.references import UNRESOLVED, reference_problems, stage_problems

PROJECT_WIDE = "work.jira"
#: Fields every create and edit sends or may send, besides the configured ones.
SYSTEM_FIELDS = (("summary", "Summary"), ("labels", "Labels"), ("assignee", "Assignee"),
                 ("parent", "Parent"))


@dataclass
class _Run:
    backend: JiraBackend
    findings: list[Finding] = field(default_factory=list)
    narration: list[str] = field(default_factory=list)
    samples: dict[tuple[str, str | None], str | None] = field(default_factory=dict)

    def error(self, where: str, message: str) -> None:
        self.findings.append(Finding("error", where, message))

    def warning(self, where: str, message: str) -> None:
        self.findings.append(Finding("warning", where, message))

    def unchecked(self, where: str, message: str) -> None:
        self.findings.append(Finding("warning", where, f"unchecked: {message}"))

    def say(self, line: str) -> None:
        self.narration.append(line)

    def sample(self, kind: IssueType, status: str | None) -> str | None:
        """The key of one ticket of `kind`, at `status` when given."""
        wanted = (kind.name, status)
        if wanted not in self.samples:
            jira = self.backend.jira
            query = (jql.type_query(jira.project, kind.name) if status is None
                     else jql.sample_query(jira.project, kind.name, status))
            with _jira():
                found = self.backend.client.search(query, ["summary"], limit=1)
            self.samples[wanted] = str(found[0]["key"]) if found else None
        return self.samples[wanted]


def remote_findings(backend: JiraBackend, layout: Layout, reader: Any,
                    resolve: Callable[[Slug], str] | None = None
                    ) -> tuple[list[Finding], list[str]]:
    """Findings for stdout, and narration for stderr. `resolve` answers a
    reference into another project (`found`, `missing` or `unresolved`)."""
    run = _Run(backend)
    try:
        _checks(run, layout, reader, resolve or (lambda slug: UNRESOLVED))
    except Unreachable as error:
        run.findings.append(Finding("unresolved", backend.project,
                                    f"Jira could not be reached, so the remaining "
                                    f"remote checks did not run: {error}"))
    except TcwError as error:
        run.error(PROJECT_WIDE, f"Jira refused a read, so the remaining remote checks "
                                f"did not run: {error}")
    return run.findings, run.narration


def _checks(run: _Run, layout: Layout, reader: Any,
            resolve: Callable[[Slug], str]) -> None:
    backend, jira = run.backend, run.backend.jira
    client = backend.client
    # 1. Access.
    try:
        with _jira():
            client.myself()
    except BackendError as error:
        run.error(PROJECT_WIDE, f"Jira rejected the credentials: {error}")
        run.say(f"{backend.project}: the remaining remote checks were skipped, since "
                f"Jira rejected the credentials")
        return
    try:
        with _jira():
            project = client.project(jira.project)
    except (NotFound, BackendError) as error:
        run.error(PROJECT_WIDE, f"Jira project {jira.project} cannot be read: {error}")
        run.say(f"{backend.project}: the remaining remote checks were skipped, since "
                f"the Jira project cannot be read")
        return
    run.say(f"{backend.project}: the credentials and Jira project {jira.project} are "
            f"readable")
    types = [IssueType(str(t.get("id")), str(t.get("name")),
                       int(t.get("hierarchyLevel") or 0), bool(t.get("subtask")))
             for t in project.get("issueTypes") or [] if isinstance(t, dict)]
    configured = next((t for t in types if t.name == jira.issue_type), None)
    if configured is None:
        run.error(PROJECT_WIDE, f"work.jira.issue-type {jira.issue_type!r} is not an "
                                f"issue type of {jira.project}")
        run.say(f"{backend.project}: the field, status and move checks were skipped, "
                f"since the configured issue type does not exist")
        return
    subtask = next((t for t in types if t.subtask), None)

    # 2. Fields, on the create screen.
    ids, has_priority, fields_ok = _create_screens(run, configured, subtask)

    # 6. Checked issue types, from the items' tickets (read once, for 7 and 8).
    folders = _folders(backend.work_path)
    tickets: dict[str, Mapping] = {}
    gone: set[str] = set()
    if "item" in ids and "project" in ids:
        tickets, gone = _read_tickets(run, list(folders), read_fields(ids))
    checked = [configured]
    for issue in tickets.values():
        name = _get(issue, "fields", "issuetype", "name")
        kind = next((t for t in types if t.name == name), None)
        if kind is not None and kind not in checked:
            checked.append(kind)

    # 2. Fields, on the edit screen.
    edit_types = checked + ([subtask] if subtask and subtask not in checked else [])
    _edit_screens(run, edit_types, ids, has_priority)

    # 3. Statuses.
    present = _statuses(run, checked)

    # 4 and 5. Moves, apart from those into or out of a status 3 found missing.
    _moves(run, checked, str(project.get("id")), present)

    # 7. Items and tickets.
    if "item" in ids and "project" in ids:
        _items_and_tickets(run, folders, tickets, gone, ids)
    else:
        run.say(f"{backend.project}: items and tickets were not checked, since the "
                f"TCW fields could not be found")
        return

    # 8. TCW-69's model checks.
    if not fields_ok:
        run.say(f"{backend.project}: the model checks were skipped, since a configured "
                f"field could not be read")
        return
    _model_checks(run, layout, reader, resolve, folders, tickets)


# -- 2. fields -----------------------------------------------------------------------


def _create_screens(run: _Run, configured: IssueType, subtask: IssueType | None
                    ) -> tuple[dict[str, str], bool, bool]:
    """Field ids by role, whether Priority exists, and whether every
    configured field was found as it should be."""
    jira = run.backend.jira
    client = run.backend.client
    with _jira():
        screens = {configured.name: client.create_metadata(jira.project, configured.id)}
        if subtask is not None:
            screens[subtask.name] = client.create_metadata(jira.project, subtask.id)
    fields = screens[configured.name]
    wanted = {"project": jira.fields.project, "item": jira.fields.item,
              "effort": jira.fields.effort, "complexity": jira.fields.complexity}
    ids: dict[str, str] = {}
    ok = True
    for role, name in wanted.items():
        if name is None:
            continue
        found = [f for f in fields if isinstance(f, dict) and f.get("name") == name]
        if len(found) != 1:
            ok = False
            run.error(PROJECT_WIDE, (f"work.jira.fields.{role} {name!r} is not on the "
                                     f"{configured.name} create screen") if not found else
                      (f"work.jira.fields.{role} {name!r} names {len(found)} fields on "
                       f"the {configured.name} create screen"))
            continue
        ids[role] = field_id(found[0])
        schema = found[0].get("schema") if isinstance(found[0].get("schema"), dict) else {}
        if role in ("project", "item") and schema.get("type") != "string":
            ok = False
            run.error(PROJECT_WIDE, f"{name!r} (work.jira.fields.{role}) is not a text "
                                    f"field")
        if role in ("effort", "complexity"):
            scales = {scale_name(v) for v in found[0].get("allowedValues") or []}
            missing = [s for s in SIZES if s not in scales]
            if schema.get("type") != "option" or missing:
                ok = False
                run.error(PROJECT_WIDE, f"{name!r} (work.jira.fields.{role}) must be a "
                                        f"single-choice list offering "
                                        f"{', '.join(SIZES)}; it lacks "
                                        f"{', '.join(missing) or 'the single-choice kind'}")
    priority = next((f for f in fields if isinstance(f, dict)
                     and field_id(f) == "priority"), None)
    if priority is None:
        run.say(f"{run.backend.project}: {jira.project} has no Priority field, so "
                f"priorities were not checked")
    else:
        offered = {v.get("name") for v in priority.get("allowedValues") or []
                   if isinstance(v, dict)}
        for model, name in jira.priorities.items():
            if name not in offered:
                run.error(PROJECT_WIDE, f"priority {name!r} (work.jira.priorities."
                                        f"{model}) is not a priority of {jira.project}")
    needed = _needed_fields(ids, priority is not None)
    for type_name, screen in screens.items():
        present = {field_id(f) for f in screen if isinstance(f, dict)}
        for wanted, label in needed:
            if wanted not in present:
                run.error(PROJECT_WIDE, f"{label} is not on the {type_name} create screen, "
                                        f"so a new ticket cannot set it")
    with _jira():
        link_types = run.backend.client.link_types()
    if not any(isinstance(t, dict) and t.get("name") == BLOCKS for t in link_types):
        run.error(PROJECT_WIDE, f"the site has no {BLOCKS!r} link type, which "
                                f"blocked-by needs")
    return ids, priority is not None, ok


def _needed_fields(ids: Mapping[str, str], has_priority: bool) -> list[tuple[str, str]]:
    jira_names = {"project": "TCW Project", "item": "TCW Item", "effort": "the effort "
                  "field", "complexity": "the complexity field"}
    needed = [(wanted, jira_names[role]) for role, wanted in ids.items()]
    needed += list(SYSTEM_FIELDS)
    if has_priority:
        needed.append(("priority", "Priority"))
    return needed


def _edit_screens(run: _Run, kinds: Iterable[IssueType], ids: Mapping[str, str],
                  has_priority: bool) -> None:
    needed = _needed_fields(ids, has_priority)
    for kind in kinds:
        key = run.sample(kind, None)
        if key is None:
            run.unchecked(PROJECT_WIDE, f"the {kind.name} edit screen: no {kind.name} "
                                        f"ticket in {run.backend.jira.project} to sample")
            continue
        with _jira():
            screen = run.backend.client.edit_metadata(key)
        for wanted, label in needed:
            if wanted not in screen:
                run.error(PROJECT_WIDE, f"{label} is not on the {kind.name} edit screen "
                                        f"(read on {key}), so TCW cannot change it")


# -- 3. statuses ---------------------------------------------------------------------


def _statuses(run: _Run, kinds: Iterable[IssueType]) -> dict[str, set[str]]:
    """Report each mapped status a checked type lacks; return each type's
    statuses."""
    jira = run.backend.jira
    with _jira():
        listed = run.backend.client.project_statuses(jira.project)
    by_type = {str(entry.get("name")): {s.get("name") for s in entry.get("statuses") or []
                                        if isinstance(s, dict)}
               for entry in listed if isinstance(entry, dict)}
    for kind in kinds:
        have = by_type.get(kind.name, set())
        for stage, status in run.backend.statuses.items():
            if status not in have:
                run.error(PROJECT_WIDE, f"status {status!r} (stage {stage}) is not a "
                                        f"status of {kind.name} in {jira.project}")
    return by_type


# -- 4 and 5. moves ------------------------------------------------------------------


def needed_moves(enabled: frozenset[str]) -> list[tuple[str, str]]:
    """Every move TCW needs a transition for (Design 9.2 check 4)."""
    order = flow_order(enabled)
    moves = list(zip(order, order[1:]))
    moves.append((order[-1], completion_stage()))
    for name in order:
        row = table_stage(name)
        if row.verdict and row.on_reject in enabled:
            moves.append((name, row.on_reject))
    moves += [(name, discard_stage()) for name in order if name != inbox_stage()]
    unique: list[tuple[str, str]] = []
    for move in moves:
        if move not in unique:
            unique.append(move)
    return unique


@dataclass(frozen=True)
class _Route:
    to: str
    sources: frozenset[str] | None       # None: from every status


def _definition(run: _Run, project_id: str, kind: IssueType) -> list[_Route] | None:
    """The workflow's transitions, or None when the definition cannot be read
    for lack of permission."""
    with _jira():
        try:
            answer = run.backend.client.workflows(project_id, kind.id)
        except TrackerPermissionError:
            return None
    if not answer.get("workflows"):
        return None                      # some sites answer a non-admin with none
    names = {s.get("statusReference"): s.get("name")
             for s in answer.get("statuses") or [] if isinstance(s, dict)}
    routes = []
    for workflow in answer.get("workflows") or []:
        for transition in (workflow.get("transitions") or []) if isinstance(
                workflow, dict) else []:
            if not isinstance(transition, dict):
                continue
            shape = transition.get("type")
            if shape == "INITIAL":
                continue                 # the create transition, from no status
            to = names.get(transition.get("toStatusReference"))
            links = [names.get(link.get("fromStatusReference"))
                     for link in transition.get("links") or [] if isinstance(link, dict)]
            sources = None if shape == "GLOBAL" else frozenset(links)
            routes.append(_Route(str(to), sources))
    return routes


def _moves(run: _Run, kinds: Iterable[IssueType], project_id: str,
           present: Mapping[str, set[str]]) -> None:
    statuses = run.backend.statuses
    moves = [(a, b) for a, b in needed_moves(run.backend.enabled)
             if a in statuses and b in statuses]
    unread_screens = False
    for kind in kinds:
        routes = _definition(run, project_id, kind)
        if routes is None:
            run.say(f"{run.backend.project}: the {kind.name} workflow definition could not "
                    f"be read (no permission, or an empty answer), so moves were checked "
                    f"on sample tickets")
        have = present.get(kind.name, set())
        for a, b in moves:
            source, target = statuses[a], statuses[b]
            if source not in have or target not in have:
                continue                 # already an error; Jira refuses its JQL
            where = f"the move from {source!r} to {target!r} ({a} to {b}) for {kind.name}"
            if routes is not None:
                candidates = [r for r in routes if r.to == target
                              and (r.sources is None or source in r.sources)]
                if not candidates:
                    run.error(PROJECT_WIDE, f"no transition makes {where}")
                    continue
                if len(candidates) == 1:
                    unread_screens = True
                    continue
            _sampled_move(run, kind, source, target, where)
    if unread_screens:
        run.say(f"{run.backend.project}: moves read from the workflow definition had "
                f"their screen fields left unchecked; only a sample ticket shows them")


def _sampled_move(run: _Run, kind: IssueType, source: str, target: str,
                  where: str) -> None:
    key = run.sample(kind, source)
    if key is None:
        run.unchecked(PROJECT_WIDE, f"{where}: no {kind.name} ticket is at {source!r} "
                                    f"to sample")
        return
    with _jira():
        offered = run.backend.client.transitions(key)
    chosen = choose_transition(offered, target)
    if isinstance(chosen, Refusal):
        run.error(PROJECT_WIDE, f"{where}, read on {key}: {chosen.message}")
        return
    required = [f for f in chosen.required if f != "comment"]
    if required:
        run.error(PROJECT_WIDE, f"{where}, read on {key}: {chosen.name!r} requires "
                                f"{', '.join(required)}; set it in a workflow post "
                                f"function instead, since TCW fills in only the comment")


# -- 7. items and tickets ----------------------------------------------------------------


def _folders(work_path: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    if work_path.is_dir():
        for entry in sorted(work_path.iterdir(), key=lambda p: p.name):
            if entry.is_dir() and KEY_FOLDER.fullmatch(entry.name):
                found.setdefault(folder_key(entry.name), []).append(entry.name)
    return found


def _read_tickets(run: _Run, keys: list[str], fields: Iterable[str]
                  ) -> tuple[dict[str, Mapping], set[str]]:
    """Each key's ticket, by the key asked for, and the keys with none. A key
    a search did not return, or every key of a refused search, is read
    directly before it is called gone (Design 3.1 step 3)."""
    client = run.backend.client
    fields = list(fields)
    tickets: dict[str, Mapping] = {}
    for chunk in _chunks(keys, jql.MAX_KEYS):
        with _jira():
            try:
                found = client.search(jql.keys_query(chunk), fields)
            except TrackerRequestInvalid:
                found = []
        for issue in found:
            tickets[str(issue.get("key"))] = issue
    gone = set()
    for key in keys:
        if key in tickets:
            continue
        with _jira():
            try:
                tickets[key] = client.issue(key, tuple(fields))
            except TrackerNotFound:
                gone.add(key)
    return tickets, gone


def _get(value: Any, *path: str) -> Any:
    for key in path:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def _items_and_tickets(run: _Run, folders: Mapping[str, list[str]],
                       tickets: Mapping[str, Mapping], gone: set[str],
                       ids: Mapping[str, str]) -> None:
    backend = run.backend
    inbox_status = backend.statuses.get(inbox_stage())
    for key, names in folders.items():
        for name in names:
            slug = Slug(backend.project, name)
            where = str(slug)
            if key in gone:
                run.error(where, f"its ticket {key} does not exist in Jira, or this "
                                 f"account cannot see it")
                continue
            issue = tickets[key]
            answered = str(issue.get("key"))
            if answered != key:
                run.error(where, f"Jira answers for {key} with {answered}: the ticket was "
                                 f"moved, so the folder's key is stale")
            fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
            if fields.get(ids["project"]) != backend.project:
                run.error(where, f"its ticket's TCW Project is "
                                 f"{fields.get(ids['project'])!r}, not {backend.project!r}")
            if fields.get(ids["item"]) != str(slug):
                run.error(where, f"its ticket's TCW Item is {fields.get(ids['item'])!r}, "
                                 f"not {str(slug)!r}")
            if _get(fields, "status", "name") == inbox_status:
                run.warning(where, f"its ticket is at the inbox status "
                                   f"{inbox_status!r}; move it on with `tcw work advance "
                                   f"{slug}`")
    query = jql.item_query(backend.jira.project, ids["item"])
    with _jira():
        named = backend.client.search(query, [ids["project"], ids["item"]])
    for issue in named:
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        if fields.get(ids["project"]) != backend.project:
            continue
        slug = backend._slug_of(fields.get(ids["item"]))
        if slug is None or slug.project != backend.project:
            continue
        if not link_exists(backend.work_path, slug.folder):
            run.warning(str(issue.get("key")), f"names {slug}, whose folder is not here; "
                                               f"the item may be on another branch")
    run.say(f"{backend.project}: {sum(len(n) for n in folders.values())} item folders "
            f"checked against their tickets")


# -- 8. the model checks ---------------------------------------------------------------


def _model_checks(run: _Run, layout: Layout, reader: Any, resolve: Callable[[Slug], str],
                  folders: Mapping[str, list[str]], tickets: Mapping[str, Mapping]) -> None:
    from tcw.work.gates import records_problems
    backend = run.backend
    pairs = [(Slug(backend.project, name), tickets[key])
             for key, names in folders.items() for name in names if key in tickets]
    try:
        items = backend._items(pairs)
    except TcwError as error:
        if isinstance(error, Unreachable):
            raise
        run.say(f"{backend.project}: the model checks were skipped: {error}")
        return
    for problem in reference_problems(items, backend.project, resolve):
        run.findings.append(Finding(problem.level, str(problem.slug), problem.message))
    for problem in stage_problems(items, layout):
        run.findings.append(Finding(problem.level, str(problem.slug),
                                    f"stage {problem.message}"))
    for item in items:
        if item.stage is None or table_stage(item.stage).kind == TERMINAL:
            continue
        if not layout.capabilities_file(item.slug).exists():
            continue
        for message in records_problems(layout, item.slug, reader, finished=False):
            run.error(str(item.slug), message)
    run.say(f"{backend.project}: the model checks ran over {len(items)} items")
