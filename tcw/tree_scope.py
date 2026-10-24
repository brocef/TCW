"""Taxonomy entries and capabilities across the projects a command covers
(TCW-113 Design 4).

`list_rows` gives the rows a `list` or a `search` prints, `show_row` the one
object a `show` names. What a scope lists (Design 4.1): `own` and
`--project` one project's own objects, `up` the active project's view, and
`down` and `all` one row per group of objects (Design 4.2, 4.3), worked out
by `tcw.store.base.scope_rows` from what is read here. The active project
`P` is read first, outside any catch, its view included wherever the scope
needs it (Design 4.9); each other project is read for itself inside
`Covered.read`, so one that cannot be read is named as unavailable (Design
1.6). The CLI and `tcw serve` both read a scope through this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tcw.errors import BackendError, InheritedUnavailable, NotFound, UsageError
from tcw.ids import FullId, sort_input
from tcw.scope import UNAVAILABLE, Covered
from tcw.store.base import (UNAVAILABILITY_ERRORS, ProjectView, ScopeObject, ScopeRow,
                            row_order, scope_rows, text_matches)


@dataclass
class TreeRow:
    """One row: the object shown (a `Term` or a `Capability`, as its owner
    sees it, or as `P`'s view gives it), and, for a row of a group under
    `down` or `all`, `statuses` (capabilities only) and `overridden_by`.
    None means the record carries no such key."""
    obj: Any
    statuses: list[dict] | None = None
    overridden_by: list[FullId] | None = None
    #: The row's group as `scope_rows` gave it, and the full identifiers of
    #: its scope objects (`V(X)` and the descendants' own objects), for a
    #: `show` by full identifier.
    group: ScopeRow | None = None
    scope_ids: frozenset = frozenset()


@dataclass
class TreeRead:
    """What a listing read: its rows, the active project's store, and
    whether that store's view was read (so its warnings can be given
    without building it)."""
    rows: list[TreeRow]
    store: Any
    view_built: bool = True


def body_of(obj) -> str:
    """The text `search` matches besides the name: a term's description, a
    capability's body."""
    return obj.description if hasattr(obj, "description") else obj.body


def active_store(covered: Covered, axis: str):
    """`P`'s store for `axis`, opened once through the command's `Locator`,
    so a descendant's view that reads `P` as a source reads this same
    store."""
    return covered.locator.store(covered.active, axis, covered.root)


def _store(covered: Covered, axis: str, project_id: str, root: Path):
    return covered.locator.store(project_id, axis, root)


def _readable_own(store) -> list:
    """Another project's own objects as it sees it. An object whose file
    cannot be read makes the project unavailable, its reason naming the file
    (Design 1.6 g, h): its rows would otherwise be left out unsaid."""
    found = store.list_all(local_only=True)
    if store.unreadable:
        raise BackendError("; ".join(f"{path}: {problem}" for path, problem
                                     in sorted(store.unreadable.items())))
    return found


def _p_own(store, say: Callable[[str], None]) -> tuple[list, bool]:
    """`P`'s own objects as it sees them or, when its view cannot be built,
    each from its own declaration alone, marked partial, with the warning
    (TCW-112 Design 3.4). The flag says whether the view was built."""
    from tcw.output import own_only
    try:
        return store.list_all(local_only=True), True
    except InheritedUnavailable as error:
        own_only(error, store.project_id)
        return store.own_declarations(), False


def _keep(obj, *, status, namespace, query) -> bool:
    if namespace and obj.full_id.parts[0] != namespace:
        return False
    if status and getattr(obj, "status", None) != status:
        return False
    if query is not None and not text_matches(obj.name, body_of(obj), query):
        return False
    return True


def list_rows(covered: Covered, axis: str, *, status: str | None = None,
              namespace: str | None = None, query: str | None = None,
              say: Callable[[str], None] | None = None) -> TreeRead:
    """The rows of a `list` (or, with `query`, a `search`) of `axis` over
    the projects `covered` keeps, filtered (Design 4.5). The grouped rows of
    `down` and `all` are in Design 4.4's order; `own`, `up` and `--project`
    keep the order the store gives, which is each command's order today, so
    `--scope up` answers exactly what the command answered before TCW-113
    and `own` exactly what `--local` did."""
    from tcw.output import say as default_say
    say = say or default_say
    store = active_store(covered, axis)
    view_built = True
    if covered.only is not None or covered.scope == "own":
        only = covered.only or covered.active
        if only == covered.active:
            objs, view_built = _p_own(store, say)
        else:
            view_built = False
            got = covered.read(only, lambda root: _readable_own(
                _store(covered, axis, only, root)))
            objs = [] if got is UNAVAILABLE else got
        rows = [TreeRow(o) for o in objs
                if _keep(o, status=status, namespace=namespace, query=query)]
    elif covered.scope == "up":
        rows = [TreeRow(o) for o in store.list_all()
                if _keep(o, status=status, namespace=namespace, query=query)]
    else:
        rows = []
        for at in _grouped(covered, axis, store).values():
            for row in at:
                if namespace and row.obj.full_id.parts[0] != namespace:
                    continue
                if status and not any(e["status"] == status for e in row.statuses or ()):
                    continue
                if query is not None and not text_matches(row.obj.name, body_of(row.obj),
                                                          query):
                    continue
                rows.append(row)
    if covered.only is None and covered.scope in ("down", "all"):
        rows = row_order(rows, covered.ids, shown=lambda r: r.obj.full_id)
    return TreeRead(rows, store, view_built)


@dataclass
class _Read:
    """One covered project's answers, for the rows of `down` and `all`."""
    project: str
    own: dict[str, Any] = field(default_factory=dict)
    view: dict[str, Any] = field(default_factory=dict)
    sets_status: dict[str, bool] = field(default_factory=dict)


def _grouped(covered: Covered, axis: str, store) -> dict[str, list[TreeRow]]:
    """Under `down` and `all`, each id-path's rows. `P`'s view is built
    first, outside any catch (Design 4.9). On capabilities under `all` the
    ancestors' views are read too, for `statuses` (Design 1.8, 4.6)."""
    capabilities = axis == "capabilities"
    whole = covered.scope == "all"
    p_view = {o.full_id.id_path: o for o in store.list_all()}
    p = _Read(covered.active, view=p_view,
              own={x: o for x, o in p_view.items() if o.owner == covered.active})
    if capabilities:
        p.sets_status = _sets_status(store, p.own)
    reads: list[_Read] = []
    for member in covered.members:
        if member.id == covered.active:
            reads.append(p)
            continue
        if member.relation == "ancestor" and not (whole and capabilities):
            continue

        def read(root: Path, member=member):
            q = _store(covered, axis, member.id, root)
            found = _Read(member.id)
            if member.relation == "descendant":
                found.own = {o.full_id.id_path: o for o in _readable_own(q)}
            if capabilities:
                found.view = {o.full_id.id_path: o for o in q.list_all()}
                if member.relation == "ancestor":
                    found.own = {x: o for x, o in found.view.items()
                                 if o.owner == member.id}
                found.sets_status = _sets_status(q, found.own)
            return found
        got = covered.read(member.id, read)
        if got is not UNAVAILABLE:
            reads.append(got)
    relation = {m.id: m.relation for m in covered.members}
    descendants = [r for r in reads if relation[r.project] == "descendant"]
    paths = set(p.view if whole else p.own)
    for r in descendants:
        paths |= set(r.own)
    out: dict[str, list[TreeRow]] = {}
    for x in paths:
        v_obj = (p.view if whole else p.own).get(x)
        v = None if v_obj is None else ScopeObject(v_obj.full_id, v_obj.overrides)
        chain = store.chain(x) if whole and v_obj is not None else []
        own = [r.own[x] for r in descendants if x in r.own]
        views = None if not capabilities else [
            ProjectView(r.project, r.view[x].full_id if x in r.view else None,
                        r.view[x].status if x in r.view else None,
                        r.sets_status.get(x, False))
            for r in reads]
        by_id = {o.full_id: o for o in own}
        if v_obj is not None:
            by_id[v_obj.full_id] = v_obj
        rows = scope_rows(x, order=covered.ids, v=v, chain=chain, views=views,
                          own=[ScopeObject(o.full_id, o.overrides) for o in own])
        out[x] = [TreeRow(by_id[row.shown], row.statuses, row.overridden_by[row.shown],
                          row, frozenset(set(by_id) & row.group)) for row in rows]
    return out


def _sets_status(store, own: dict[str, Any]) -> dict[str, bool]:
    """Whether each own object's own declaration sets Status (TCW-112
    Design 7.2)."""
    out = {}
    for x in own:
        declared = store.declaration(x)
        out[x] = declared is not None and "Status" in declared.fields
    return out


def show_row(covered: Covered, axis: str, text: str) -> TreeRow:
    """The object `text` names under the scope (Design 4.8, 2.3)."""
    from tcw.locate import _no_such, find_tree
    found = sort_input(text, axis)
    store = active_store(covered, axis)
    named = None if found.form == "d" else found.full_id
    if covered.only is not None:
        if named is not None and named.project != covered.only:
            raise UsageError(f"'{text}' names an object of project '{named.project}', and "
                             f"--project keeps only project '{covered.only}''s; give one "
                             f"of them")
        if named is None:
            text = f"{covered.only}.{axis}/{found.id_path}"
        # Read as that full identifier is read (Design 2.3), outside any
        # catch: the object asked for is never made unavailable (Design 1.7).
        return TreeRow(find_tree(store, text))
    if named is not None:
        obj = find_tree(store, text)
        if covered.scope in ("down", "all"):
            for row in _grouped(covered, axis, store).get(named.id_path, []):
                if obj.full_id in row.scope_ids:
                    return TreeRow(obj, row.statuses,
                                   row.group.overridden_by[obj.full_id], row.group,
                                   row.scope_ids)
        return TreeRow(obj)
    x = found.id_path
    if covered.scope == "own":
        if store.has_own(x):
            return TreeRow(find_tree(store, text))
        raise NotFound(_no_such(axis, text) + _hints(store, axis, x)
                       + _inherits_hint(store, x))
    if covered.scope == "up":
        store.list_all()        # `P`'s view, which `up` needs (Design 4.9)
        return TreeRow(find_tree(store, text))
    rows = _grouped(covered, axis, store).get(x, [])
    if len(rows) == 1:
        return rows[0]
    if not rows:
        raise NotFound(f"{_no_such(axis, text)} in --scope {covered.scope}"
                       + _hints(store, axis, x))
    raise UsageError(f"'{x}' names {len(rows)} objects in --scope {covered.scope}: "
                     f"{', '.join(str(r.obj.full_id) for r in rows)}; name one by its "
                     f"full identifier")


def _hints(store, axis: str, id_path: str) -> str:
    """The hints `find_tree` gives a path it does not find: the folder's
    spelling on disk, and how to name another project's object."""
    from tcw.locate import _spelled, _three_x_hint
    return _spelled(store, id_path) + _three_x_hint(store, axis, id_path)


def _inherits_hint(store, id_path: str) -> str:
    """Design 4.8's hint, when `P` has no object of its own at `id_path` but
    its view has one. Building the view never changes the outcome: when it
    cannot be built, there is no hint."""
    try:
        seen = store.get_view(id_path)
    except UNAVAILABILITY_ERRORS:
        return ""
    if seen is None:
        return ""
    return (f"; '{store.project_id}' inherits {seen.full_id} there: add --scope up, "
            f"or name it by that full identifier")


# -- what the CLI prints ----------------------------------------------------------------

#: What an unavailable project's warning says is left out (Design 1.8), by
#: axis: for a listing, then for a `show`.
LEFT_OUT = {
    "taxonomy": ("its taxonomy entries are not listed",
                 "its taxonomy entries are not included"),
    "capabilities": ("its capabilities are not listed", "its status is not shown"),
}


def covered_for(args, axis: str, missing: Callable[[], Exception]) -> Covered | None:
    """The projects a tree command covers, or None for what the command did
    before TCW-113 (no `--scope` and no `--project`: plan choice 12's interim
    default). A `--project` with no `--scope` is under `own`. `missing()` is
    the error for a folder with no `axis` store, as the command gives it."""
    if args.scope is None and args.project is None:
        return None
    from tcw.scope import cover
    from tcw.store.fs import find_component_project, find_project_root
    from tcw.store.project import FsProjectRegistry
    root = find_project_root()
    if root is None:
        raise missing()
    FsProjectRegistry.open(root).require_valid()
    covered = cover(root, args.scope or "own", args.project)
    # Whether the project has the store, asked of the store the command's
    # `Locator` keeps, so it is opened once.
    if find_component_project(axis, opener=lambda nr: active_store(covered, axis)) is None:
        raise missing()
    return covered


def scope_keys(row: TreeRow) -> dict:
    """The keys a record gains from its row (Design 4.6, 4.7): `statuses`
    and `overridden-by`, each only when the row carries it."""
    out: dict[str, Any] = {}
    if row.statuses is not None:
        out["statuses"] = row.statuses
    if row.overridden_by is not None:
        out["overridden-by"] = [str(f) for f in row.overridden_by]
    return out


def print_rows(covered: Covered, axis: str, key: str, record: Callable[[Any], dict],
               as_json: bool, reorder: Callable[[list], list] | None = None,
               **filters) -> int:
    """A `list` or `search` over `covered`: the warnings, then one full
    identifier per line, or the `--json` document; the exit code is the
    active project's, as today (`left_out`). `reorder`, when given, orders
    the objects of an ungrouped listing as the command orders them today."""
    from tcw.output import left_out, print_json, say
    read = list_rows(covered, axis, **filters)
    if reorder is not None and (covered.only is not None
                                or covered.scope not in ("down", "all")):
        read.rows = [TreeRow(o) for o in reorder([r.obj for r in read.rows])]
    covered.warn(LEFT_OUT[axis][0], say)
    if read.view_built:
        for warning in read.store.view_warnings(
                {r.obj.full_id.id_path for r in read.rows}):
            say(f"warning: {warning}")
    if as_json:
        projects = covered.projects_json()
        print_json(None, {key: [{**record(r.obj), **scope_keys(r)} for r in read.rows],
                          **({} if projects is None else {"projects": projects})})
    else:
        for row in read.rows:
            print(row.obj.full_id)
    return left_out(read.store.unreadable_files())


def show_lines(covered: Covered, row: TreeRow) -> tuple[list[str], list[str]]:
    """The text a `show` adds for its row (Design 4.6, 4.7; plan choice 8):
    the `overridden by:` line, to follow `overrides:`, and the `status by
    project:` block, to follow the fields."""
    overridden = [f"overridden by: {', '.join(str(f) for f in row.overridden_by)}"] \
        if row.overridden_by else []
    if row.statuses is None:
        return overridden, []
    by_status: dict[str, list[str]] = {}
    for e in row.statuses:
        name = "(no status)" if e["status"] is None else e["status"]
        by_status.setdefault(name, []).append(
            e["project"] + (" (inherited)" if e["inherited"] else ""))
    block = ["status by project:",
             *(f"  {status}: {', '.join(ids)}" for status, ids in by_status.items())]
    if covered.unavailable():
        block.append(f"  unavailable: {', '.join(covered.unavailable())}")
    return overridden, block
