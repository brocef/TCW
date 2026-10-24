"""The Jira half of a migration (TCW-116 Design 5; plan Decided 10, 11, 19;
Step 9).

The one module of `tcw.migrate` that imports from `tcw.work.jira`, and it is
imported only by `plan.plan_jira_half`, which returns before the import under
`--no-jira` and for a project whose work is kept in files. So no other code
of the run can hold a Jira client.

The backend is built from the `work.jira` of the project's own layers, in
whichever form they are on disk (`legacy.own_jira_layers`), with the default
work configuration: the two backend methods migration uses read nothing
else. Planning hands it `_ReadOnlyClient`, which passes on only the reading
calls planning makes; phase F builds a second backend over the plain client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from tcw.errors import BackendError
from tcw.ids import ID_LIMIT, looks_full
from tcw.migrate.legacy import own_jira_layers
from tcw.migrate.model import Blocker, Report, TicketEdit
from tcw.work.config import parse_work_config
from tcw.work.jira.backend import JiraBackend, _jira, three_x_item
from tcw.work.jira.client import JiraClient
from tcw.work.jira.config import JiraConfig, parse_jira_config

#: The client calls planning makes: `metadata()`, `item_values()` and B16.
ALLOWED = frozenset({"search", "issue", "edit_metadata", "project", "create_metadata",
                     "myself"})

NO_JIRA_HINT = "'tcw migrate --no-jira' converts the files without Jira"


class _ReadOnlyClient:
    """A client that passes on only `ALLOWED`; any other name, a writing call
    or one a later item adds, fails the run (Decided 19)."""

    def __init__(self, client: JiraClient):
        object.__setattr__(self, "_client", client)

    def __getattr__(self, name: str):
        if name in ALLOWED:
            return getattr(self._client, name)
        raise AssertionError(f"tcw migrate: {name} is not allowed while planning")

    def __setattr__(self, name: str, value) -> None:
        raise AssertionError(f"tcw migrate: {name} is not allowed while planning")


def settings(root: Path) -> JiraConfig:
    """The project's own `work.jira`, parsed (Decided 11). A layer that cannot
    be read, a missing key or one the parser refuses is a Jira failure while
    planning: exit 1, naming the file, the key and `--no-jira`."""
    root = Path(root)
    layers = own_jira_layers(root)
    if layers.problems:
        raise BackendError(f"{layers.problems[0]}; {NO_JIRA_HINT}")
    jira, problems = parse_jira_config(layers.jira)
    if problems:
        problem = problems[0]
        where = layers.file_of(tuple(problem.key_path[2:]))
        shown = where.relative_to(root).as_posix() if where is not None \
            and where.is_relative_to(root) else str(where or "tcw-config.yaml")
        raise BackendError(f"{shown}: {problem}; {NO_JIRA_HINT}")
    return jira


def backend_for(root: Path, project_id: str, jira: JiraConfig, client) -> JiraBackend:
    """The backend migration's two calls are made through, over `client`."""
    return JiraBackend(project_id, Path(root), parse_work_config({})[0], jira,
                       client=client, report=lambda line: None)


def plan_tickets(project_id: str, backend: JiraBackend
                 ) -> tuple[list[TicketEdit], list[Report], list[Blocker]]:
    """The ticket edits of phase F (Design 5.1, 5.2), the A10 reports, and
    B16 when the first ticket to edit cannot have its `TCW Item` set."""
    tickets, reports = [], []
    own = f"{project_id}.work/"
    for key, project, value in backend.item_values():
        if project != project_id or (isinstance(value, str) and value.startswith(own)):
            continue
        named, _, folder = value.partition("/") if isinstance(value, str) else ("", "", "")
        if named == project_id and folder and not looks_full(value):
            new = own + folder
            if len(new) > ID_LIMIT:
                reports.append(Report(
                    "A10", key, f"TCW Item {value[:40]}… would be {len(new)} characters "
                                f"as {own}…, over the {ID_LIMIT} a full identifier can "
                                f"hold; it is not edited"))
                continue
            if three_x_item(value):
                tickets.append(TicketEdit(key, value, new))
                continue
        reports.append(Report("A10", key, f"TCW Item {value!r} is neither a TCW 3.x "
                                          f"nor a TCW 4 value of this project; it is "
                                          f"not edited"))
    blockers = []
    if tickets:
        first = tickets[0].key
        item_field = backend.metadata().field_ids["item"]
        with _jira():
            screen = backend.client.edit_metadata(first)
        if item_field not in screen:
            blockers.append(Blocker(
                "B16", first, f"its edit screen does not offer the TCW Item field "
                              f"({item_field}), so no ticket's TCW Item could be set",
                "add the field to the edit screen of its issue type in Jira, then run "
                "'tcw migrate' again"))
    return tickets, reports, blockers


def apply_tickets(tickets: list[TicketEdit], backend: JiraBackend,
                  edited: Callable[[TicketEdit], None]) -> None:
    """Phase F: every planned edit, through `set_item_values`."""
    by_key = {t.key: t for t in tickets}
    backend.set_item_values([(t.key, t.old, t.new) for t in tickets],
                            edited=lambda key: edited(by_key[key]))


@dataclass
class JiraHalf:
    """The Jira half as planned: the edits, A10, B16, the Jira project's key,
    and `apply`, which makes the edits over the plain client."""

    jira_project: str
    tickets: list[TicketEdit] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    apply: Callable[[Callable[[TicketEdit], None]], None] = lambda edited: None


def half(root: Path, project_id: str) -> JiraHalf:
    """Plan the Jira half over the read-only client. A Jira failure raises
    the backend's own error (Design 1.6)."""
    jira = settings(root)
    planning = backend_for(root, project_id, jira, _ReadOnlyClient(JiraClient(jira)))
    tickets, reports, blockers = plan_tickets(project_id, planning)

    def apply(edited: Callable[[TicketEdit], None]) -> None:
        apply_tickets(tickets, backend_for(root, project_id, jira, JiraClient(jira)), edited)
    return JiraHalf(jira.project, tickets, reports, blockers, apply)
