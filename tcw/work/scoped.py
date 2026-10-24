"""Work items across the projects a command covers (TCW-113 Design 3).

Work is never inherited: each covered project's own items come from its own
backend's `list`, with its own query, and no item appears under any project
but its owner. The active project is read first, outside any catch, with the
query as given; every other project is read for itself (Design 1.5) inside
`Covered.read`, so one that cannot be read is named as unavailable rather
than stopping the command (Design 1.6). The CLI and `tcw serve` both list a
scope through `list_scope`, so they give the same items.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from tcw.errors import ConfigError
from tcw.scope import UNAVAILABLE, Covered
from tcw.work.backend import Query, WorkBackend
from tcw.work.model import Item, Slug
from tcw.work.record import readable


@dataclass
class ScopedItems:
    """Each covered project's items, in scope order, with the backend that
    holds them; and `every`, the readable items of every covered project
    that is not unavailable, which `children` and `blocks` are computed
    from (Design 3.3), filled only when asked for."""

    by_project: list[tuple[str, list[Item], WorkBackend]] = field(default_factory=list)
    every: list[Item] = field(default_factory=list)
    bad: list[str] = field(default_factory=list)

    def items(self) -> list[tuple[Item, WorkBackend]]:
        return [(item, backend) for _, items, backend in self.by_project
                for item in items]


def no_identity() -> ConfigError:
    """`_me`'s message, for a project that can name nobody for `--mine`."""
    from tcw.config import LOCAL_FILE, user_config_label
    return ConfigError(
        f"no identity is configured: set `user.name` in {user_config_label()} "
        f"or in {LOCAL_FILE}, or, in a Jira project, set the environment "
        f"variables named by `work.jira.credentials`")


def narrowed_stages(stages: frozenset[str] | None, config) -> frozenset[str] | None:
    """`stages` without those another project cannot hold an item at
    (Design 3.2): a stage its lifecycle does not enable and, when it keeps
    its work in Jira, a stage its configuration maps to no Jira status. A
    fact of its configuration, read with no request."""
    if stages is None:
        return None
    jira = config.backend == "jira"
    return frozenset(s for s in stages if s in config.enabled
                     and (not jira or config.stage(s).status is not None))


def list_scope(covered: Covered, query: Query, *, active: WorkBackend,
               active_assignee: str | None = None, mine: bool = False,
               me: Callable[[], str | None] | None = None,
               need_every: bool = False) -> ScopedItems:
    """The items `query` selects in each project the scope keeps, in scope
    order. `active` is the active project's backend, listed first and
    outside any catch, with `query` as given and `active_assignee` as the
    assignee (Design 1.7). With `mine`, every other project is asked for
    the one person running the command in its own form (Design 3.2): its
    Jira account for a Jira project, else `me()`, the active project's
    `user.name`. `need_every` also reads every item of each project read,
    for `children` and `blocks`."""
    from tcw.work.jira.backend import JiraBackend
    from tcw.work.open import open_backend, read_work_config
    found = ScopedItems()
    wanted = {m.id for m in covered.wanted()}
    if covered.active in wanted:
        own_query = replace(query, assignee=active_assignee) if mine else query
        items = active.list(own_query)
        found.by_project.append((covered.active, items, active))
    if need_every:
        every, bad = readable(active)
        found.every += every
        found.bad += bad
    for member in covered.members:
        if member.id == covered.active:
            continue
        listing = member.id in wanted

        def read(root: Path, listing=listing):
            config = read_work_config(root, personal=False, registry=covered.registry)
            stages = narrowed_stages(query.stages, config)
            if listing and stages is not None and not stages and not need_every:
                return [], None, ([], [])
            backend = open_backend(root, personal=False, registry=covered.registry)
            items: list[Item] = []
            if listing and (stages is None or stages):
                own = replace(query, stages=stages)
                if mine:
                    person = backend.current_user() if isinstance(backend, JiraBackend) \
                        else (me() if me is not None else None)
                    if person is None:
                        raise no_identity()
                    own = replace(own, assignee=person)
                items = backend.list(own)
            return items, backend, readable(backend) if need_every else ([], [])

        if not listing and not need_every:
            continue
        answer = covered.read(member.id, read)
        if answer is UNAVAILABLE:
            continue
        items, backend, (every, bad) = answer
        if listing and backend is not None:
            found.by_project.append((member.id, items, backend))
        found.every += every
        found.bad += bad
    order = {pid: i for i, pid in enumerate(covered.ids)}
    found.by_project.sort(key=lambda row: order[row[0]])
    return found


def every_item(covered: Covered, active: WorkBackend, owner: WorkBackend | None = None
               ) -> tuple[list[Item], list[str]]:
    """The readable items of every covered project that is not unavailable,
    the active project's first and outside any catch, for `children` and
    `blocks` (Design 3.3); and the items that could not be read. `owner` is
    the backend of the item they are computed for, when that item is named
    by its full identifier: when the scope does not cover its project, that
    project's items are added once, outside any catch, so a wider scope
    never loses the children and blocked items `own` would count."""
    from tcw.work.open import open_backend
    every, bad = readable(active)
    if owner is not None and owner.project != covered.active \
            and owner.project not in covered.ids:
        more, more_bad = readable(owner)
        every += more
        bad += more_bad
    for member in covered.members:
        if member.id == covered.active:
            continue
        answer = covered.read(member.id, lambda root: readable(
            open_backend(root, personal=False, registry=covered.registry)))
        if answer is not UNAVAILABLE:
            every += answer[0]
            bad += answer[1]
    return every, bad


def find_in_scope(covered: Covered, text: str, *, active: WorkBackend,
                  key: str | None, id_path: str | None) -> list[tuple[Slug, WorkBackend]]:
    """Each item a folder name (`id_path`) or a ticket key (`key`) names in
    the projects the scope keeps (Design 3.4): the active project's first,
    outside any catch, then each other project in scope order. A project
    that has no such item answers no match, never an unavailability; one
    that cannot be read is unavailable."""
    from tcw.work.open import open_backend

    def match(backend: WorkBackend) -> Slug | None:
        if key is not None:
            folder = backend.lookup(key)
            return None if folder is None else Slug(backend.project, folder)
        return Slug(backend.project, id_path) if backend.is_item_folder(id_path) else None

    found: list[tuple[Slug, WorkBackend]] = []
    for member in covered.wanted():
        if member.id == covered.active:
            hit = match(active)
            if hit is not None:
                found.append((hit, active))
            continue

        def look(root: Path):
            backend = open_backend(root, personal=False, registry=covered.registry)
            return match(backend), backend
        answer = covered.read(member.id, look)
        if answer is not UNAVAILABLE and answer[0] is not None:
            found.append(answer)
    order = {pid: i for i, pid in enumerate(covered.ids)}
    found.sort(key=lambda row: (row[0].project != covered.active, order[row[0].project]))
    return found
