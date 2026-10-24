"""Taxonomy and capability routes, and `tcw://` link resolution.

Reading, creating and editing go through the same stores the CLI uses, with
their revisions; a successful save is followed by the one-object validation
check, whose findings come back as `warnings` and never undo the save.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from typing import Any, Callable

from tcw.errors import NotFound, TcwError, UsageError
from tcw.findings import Finding
from tcw.ids import MalformedId, identity, inherited_keys, parent_text, sort_input
from tcw.ids import parse_address
from tcw.locate import UNRESOLVED, find_tree
from tcw.refs import resolve_address
from tcw.serve.server import (Request, Written, creates, not_found, route, usage)
from tcw.store.base import Capability, Term
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tcw.tree_scope import (active_store, capability_detail, list_document, listing,
                            scope_keys, show_row, term_detail)
from tcw.validate import ValidationTarget, validate

# At most this many links per /api/resolve request (a rendered page's links).
RESOLVE_MAX_URIS = 256


def jsonable(value: Any) -> Any:
    if isinstance(value, (Term, Capability)):
        # Named by its full identifier and owner (TCW-110 Design 4.5); the
        # path, the store's own `origin` and the owner field it came from
        # are not sent.
        # `parent` as text, never its parts; then `overrides` or `partial`,
        # as the CLI's records carry them (TCW-112 Design 3.3, 3.4).
        rest = {k: v for k, v in asdict(value).items()
                if k not in ("slug", "path", "origin", "parent", "overrides", "partial")}
        data = {**identity(value.full_id), "parent": parent_text(value.parent),
                **inherited_keys(value), **rest}
        if isinstance(value, Capability):
            data["status"] = value.status
        return jsonable(data)
    if is_dataclass(value):
        data = asdict(value)
        for attr in ("ref", "status"):
            if attr not in data and hasattr(value, attr):
                data[attr] = getattr(value, attr)
        return data
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return value


def scope_of(request: Request):
    """The projects a read route covers (TCW-113 Design 6.1): its `scope`
    query parameter, `own` when absent, and its `project`, each read as
    `--scope` and `--project` are. `cover` is called once, so the request
    has one `Locator` and one registry (plan choice 4). A value the CLI
    refuses answers 400 `usage` with the CLI's message."""
    from tcw.scope import cover
    scope = (request.query.get("scope") or ["own"])[-1] or "own"
    project = (request.query.get("project") or [""])[-1] or None
    try:
        return cover(request.root, scope, project)
    except UsageError as error:
        raise usage(str(error)) from None


def _quiet(line: str) -> None:
    """A warning the CLI prints on standard error: the server's answer
    carries what the page shows, `projects` among it, and prints nothing."""


def _listed(request: Request, axis: str, **filters):
    """A list answer (Design 6.2): the records `tcw <axis> list --json`
    prints for the same scope, in the same order, each beside the server's
    other fields of that object (plan choice 9), and `projects` when the
    scope is not `own`."""
    covered = scope_of(request)
    read = listing(covered, axis, say=_quiet, **filters)
    return HTTPStatus.OK, list_document(covered, axis, read, extra=jsonable)


def _shown(request: Request, axis: str):
    """The row a detail route's key names under its scope (Design 4.8), the
    detail read from the owner's store, and `projects` for the answer. The
    served store reads another project's object through the request's
    `Locator` (`_owner_store`), so `coreRevision` and `declaredDescription`
    are the owner's (TCW-112 AC 44)."""
    from tcw.errors import UnknownProject
    covered = scope_of(request)
    try:
        row = show_row(covered, axis, request.param(1))
    except UnknownProject as error:
        # A mistyped project in a URL is not found, not a server fault
        # (Design 6.4).
        raise not_found(str(error)) from None
    store = active_store(covered, axis)
    read = store.get_term_detail if axis == "taxonomy" else store.get_capability_detail
    detail = read(row.obj.full_id)
    if detail is None:
        noun = "term" if axis == "taxonomy" else "capability"
        raise not_found(f"no such {noun}: {request.param(1)}")
    projects = covered.projects_json()
    return row, detail, {} if projects is None else {"projects": projects}


def finding_record(finding: Finding) -> dict[str, str]:
    return {"severity": finding.severity, "where": finding.where,
            "message": finding.message}


def checked(response: dict, request: Request, target: ValidationTarget) -> dict:
    """`response` with the saved object's validation findings as `warnings`.
    A check that cannot finish is itself one warning: the save stands."""
    try:
        found = [finding_record(f) for f in validate(request.root, target=target)]
    except Exception as error:
        found = [{"severity": "warning", "where": target.ref or "",
                  "message": f"validation could not complete: {error}"}]
    if found:
        response["warnings"] = found
    return response


def _taxonomy(request: Request) -> FsTaxonomyStore:
    return FsTaxonomyStore.open(request.root)


def _capabilities(request: Request) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(request.root)


def OVERRIDE_HINT(id_path: str) -> str:
    """The end of the refusal of an inherited capability's edit: the page
    edits only this project's own objects, and the CLI makes an override."""
    return (f"; or override it in this project with `tcw capabilities set "
            f"{id_path} --field <name>=<value>`")


def _route_target(store: FsTaxonomyStore | FsCapabilitiesStore, key: str):
    """The entry a route key names, read as command input is (TCW-112 Design
    3.1): this project's id-path, or a full identifier, which names its
    owner's own object. An entry of a project this one does not inherit
    from is not served here."""
    found = find_tree(store, key)          # a usage error is 400, not found 404
    if found.owner != store.project_id and found.owner not in {
            entry.id for entry in store.locator.registry.source_entries(store.COMPONENT)}:
        raise not_found(f"{found.full_id} belongs to project '{found.owner}', "
                        f"which this project does not inherit from")
    return found


def _written(open_store: Callable[[Request], Any], namespace: str,
             hint: Callable[[str], str] | None = None):
    """The `writes` of a route that edits the object its key names
    (TCW-114 Design 1.4). A full identifier is answered as written, before
    any store is read, so another project's object is refused whether or
    not that project can be read (Design 1.1); an id-path is found in the
    served project's view, where it may name an inherited object. `hint`
    gives the refusal's end from the object's id-path, for an object of a
    project the served one inherits from, which is the only kind it can
    override."""
    def writes(request: Request) -> list[Written]:
        key = request.param(1)
        try:
            found = sort_input(key, namespace)
        except MalformedId:
            return []                   # the handler's own lookup answers it
        store = open_store(request)
        if found.form in ("a", "c"):
            full_id = found.full_id
        else:
            full_id = find_tree(store, key).full_id
        sources = {entry.id for entry in store.locator.registry.source_entries(namespace)}
        end = hint(full_id.id_path) if hint and full_id.project in sources else None
        return [Written(full_id, end)]
    return writes


# -- taxonomy ---------------------------------------------------------------------


def list_terms(request: Request):
    return _listed(request, "taxonomy")


def get_term(request: Request):
    row, detail, projects = _shown(request, "taxonomy")
    return HTTPStatus.OK, {"term": {**jsonable(detail.term), **term_detail(row.obj),
                                    **scope_keys(row)},
                           "coreRevision": detail.core_revision, **projects}


def create_term(request: Request):
    store = _taxonomy(request)
    name = request.field("name", required=False, default="")
    if not name:
        raise usage("name is required")
    parent = request.field("parent", required=False)
    with request.lock:
        if parent:
            # A parent naming nothing is a bad field in the request, not a
            # missing resource: 400, as every other refused value is.
            try:
                store.find_parent(parent)
            except NotFound as missing:
                raise usage(f"parent: {missing}") from None
        term = store.add(name=name, slug=request.field("slug", required=False),
                         parent=parent,
                         description=request.field("description", required=False,
                                                   default=""),
                         kind=request.field("kind", required=False),
                         vocabulary=request.field("vocabulary", list, required=False))
        detail = store.get_term_detail(term.slug)
    response = {"term": jsonable(term),
                "coreRevision": detail.core_revision if detail else ""}
    return HTTPStatus.CREATED, checked(response, request,
                                       ValidationTarget("taxonomy", term.slug))


TERM_FIELDS = {"name": "name", "description": "description", "kind": "kind",
               "relates_to": "relates_to", "relatesTo": "relates_to",
               "vocabulary": "vocabulary"}


def update_term(request: Request):
    fields = request.field("fields", dict, required=False, default={})
    changes: dict[str, Any] = {TERM_FIELDS[k]: v for k, v in fields.items()
                               if k in TERM_FIELDS}
    if "body" in request.body:
        changes["description"] = request.body["body"]
    # Required, so no save skips the check that the record is unchanged since
    # it was read; the client always sends the `coreRevision` it last read.
    changes["core_revision"] = request.field("revision")
    store = _taxonomy(request)
    found = _route_target(store, request.param(1))
    with request.lock:
        detail = store.update_term(found.full_id, **changes)
    response = {"term": jsonable(detail.term), "coreRevision": detail.core_revision}
    return HTTPStatus.OK, checked(response, request,
                                  ValidationTarget("taxonomy", detail.term.slug))


# -- capabilities ----------------------------------------------------------------------


def _subjects_are_vocabulary(request: Request, fields: dict) -> None:
    """A capability's `Subject` names vocabulary entries, inherited ones
    included. The store refuses a Subject that names nothing, and every other
    reference field that does not resolve; it accepts a Subject naming a
    Feature, which the viewer refuses as it offers only vocabulary."""
    subjects = fields.get("Subject")
    if not subjects:
        return
    taxonomy = _taxonomy(request)
    for ref in subjects if isinstance(subjects, list) else str(subjects).split(","):
        ref = str(ref).strip()
        try:
            # Read as the store reads it before storing its full identifier.
            term = find_tree(taxonomy, ref)
        except TcwError:
            continue                    # the store's own message names it
        if term.kind != "Vocabulary":
            raise usage(f"Subject: {ref} is a {term.kind}, not a vocabulary entry")


def list_capabilities(request: Request):
    return _listed(request, "capabilities")


def get_capability(request: Request):
    row, detail, projects = _shown(request, "capabilities")
    answer = _capability_answer(detail)
    answer["capability"] = {**answer["capability"], **capability_detail(row.obj),
                            **scope_keys(row)}
    return HTTPStatus.OK, {**answer, **projects}


def _capability_answer(detail) -> dict:
    """A capability detail as the web app reads it: the record, its
    revision, and the owner's declared description, which the editor edits
    instead of the combined body (TCW-112 Design 4.5)."""
    return {"capability": jsonable(detail.capability),
            "coreRevision": detail.core_revision,
            "declaredDescription": detail.declared_description}


def create_capability(request: Request):
    store = _capabilities(request)
    path = request.field("path", required=False, default="")
    if not path:
        raise usage("path is required")
    fields = request.field("fields", dict, required=False)
    if fields:
        _subjects_are_vocabulary(request, fields)
    with request.lock:
        store.add(path, name=request.field("name", required=False) or None,
                  status=request.field("status", required=False, default="Missing"),
                  body=request.field("body", required=False, default=""),
                  fields=fields)
        detail = store.get_capability_detail(path)
    response = _capability_answer(detail)
    return HTTPStatus.CREATED, checked(response, request,
                                       ValidationTarget("capabilities", path))


def update_capability(request: Request):
    changes: dict[str, Any] = {}
    fields = request.field("fields", dict, required=False)
    if fields is not None:
        changes["fields"] = fields
    if "body" in request.body:
        changes["body"] = request.body["body"]
    # Required, so no save skips the check that the record is unchanged since
    # it was read; the client always sends the `coreRevision` it last read.
    changes["core_revision"] = request.field("revision")
    store = _capabilities(request)
    found = _route_target(store, request.param(1))
    if fields:
        _subjects_are_vocabulary(request, fields)
    with request.lock:
        detail = store.update_capability(found.full_id, **changes)
    response = _capability_answer(detail)
    return HTTPStatus.OK, checked(response, request,
                                  ValidationTarget("capabilities", detail.capability.path))


# -- links ----------------------------------------------------------------------------


def resolve(request: Request):
    """Each `tcw://` link's target, or why it has none. `reason` is one of
    `unresolved` (with `detail`), `archived` (with `detail` and
    `resolution`) and `other-project` (with `project`): a link to a project
    that is not on this machine, drawn as a labelled link that does not
    navigate. A link to another project's object that is there answers `ok`
    with its full identifier as `key`, the route key that reads it from its
    owner (TCW-113 Design 6.4)."""
    uris = request.body.get("uris")
    if not isinstance(uris, list):
        raise usage("uris must be a list")
    result: dict[str, Any] = {}
    for uri in uris[:RESOLVE_MAX_URIS]:
        if not isinstance(uri, str):
            continue
        found = resolve_address(request.root, uri)
        if not found.ok and found.outcome == UNRESOLVED:
            result[uri] = {"ok": False, "reason": "other-project",
                           "project": parse_address(uri).project}
        elif not found.ok:
            result[uri] = {"ok": False, "reason": "unresolved", "detail": found.reason}
        elif found.folder:
            # A sound folder address, drawn inert: the app shows objects.
            result[uri] = {"ok": False, "reason": "unresolved",
                           "detail": f"{uri} names a folder, not an object"}
        elif found.archived:
            detail = f"{found.key} is resolved work; its documents are no longer " \
                     f"in the tree"
            if found.resolution:
                detail = f"{found.key} was resolved as {found.resolution}; its " \
                         f"documents are no longer in the tree"
            result[uri] = {"ok": False, "reason": "archived", "detail": detail,
                           "resolution": found.resolution}
        else:
            result[uri] = {"ok": True, "axis": found.namespace, "key": found.key}
    return HTTPStatus.OK, result


ONE = r"/([^/]+)"
ROUTES = [
    route("GET", r"/api/taxonomy", list_terms),
    route("GET", r"/api/taxonomy" + ONE, get_term),
    route("POST", r"/api/taxonomy", create_term, writes=creates),
    route("PATCH", r"/api/taxonomy" + ONE, update_term,
          writes=_written(_taxonomy, "taxonomy")),
    route("GET", r"/api/capabilities", list_capabilities),
    route("GET", r"/api/capabilities" + ONE, get_capability),
    route("POST", r"/api/capabilities", create_capability, writes=creates),
    route("PATCH", r"/api/capabilities" + ONE, update_capability,
          writes=_written(_capabilities, "capabilities", OVERRIDE_HINT)),
    route("POST", r"/api/resolve", resolve),
]
