"""Taxonomy and capability routes, and `tcw://` link resolution.

Reading, creating and editing go through the same stores the CLI uses, with
their revisions; a successful save is followed by the one-object validation
check, whose findings come back as `warnings` and never undo the save.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from typing import Any

from tcw.findings import Finding
from tcw.ids import identity
from tcw.locate import find_tree
from tcw.refs import resolve_tcw_ref
from tcw.serve.server import Request, not_found, read_only, route, usage
from tcw.store.base import AmbiguousRef, Capability, Term
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tcw.validate import ValidationTarget, validate

# tcw:// axis letter -> the client's axis word (the client parses no TCW references).
AXIS_WORD = {"T": "taxonomy", "C": "capabilities", "W": "work"}
# At most this many links per /api/resolve request (a rendered page's links).
RESOLVE_MAX_URIS = 256


def jsonable(value: Any) -> Any:
    if isinstance(value, (Term, Capability)):
        # Named by its full identifier and owner (TCW-110 Design 4.5); the
        # path, the store's own `origin` and the owner field it came from
        # are not sent.
        data = {**identity(value.full_id), **asdict(value)}
        for attr in ("slug", "path", "origin"):
            data.pop(attr, None)
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


def _route_target(store: FsTaxonomyStore | FsCapabilitiesStore, key: str):
    """The entry a route key names, read as command input is (TCW-110 Design
    3.1): this project's id-path, or a full identifier. An entry of a project
    this one does not inherit from is not served here."""
    found = find_tree(store, key)          # a usage error is 400, not found 404
    if found.origin == "local" and found.owner != store.project_id:
        raise not_found(f"{found.full_id} belongs to project '{found.owner}', "
                        f"which this project does not inherit from")
    return found


# -- taxonomy ---------------------------------------------------------------------


def list_terms(request: Request):
    return HTTPStatus.OK, jsonable(_taxonomy(request).list_all())


def get_term(request: Request):
    store = _taxonomy(request)
    detail = store.get_term_detail(_route_target(store, request.param(1)).full_id)
    if detail is None:
        raise not_found(f"no such term: {request.param(1)}")
    return HTTPStatus.OK, {"term": jsonable(detail.term),
                           "coreRevision": detail.core_revision}


def create_term(request: Request):
    store = _taxonomy(request)
    name = request.field("name", required=False, default="")
    if not name:
        raise usage("name is required")
    with request.lock:
        term = store.add(name=name, slug=request.field("slug", required=False),
                         parent=request.field("parent", required=False),
                         description=request.field("description", required=False,
                                                   default=""),
                         kind=request.field("kind", required=False, default="Vocabulary"),
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
    if found.origin != "local":
        raise read_only(f"{found.full_id} is inherited from '{found.owner}'; "
                        f"change it there")
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
            term = taxonomy.get(ref)
        except AmbiguousRef:
            continue                    # the store's own message names it
        if term is not None and term.kind != "Vocabulary":
            raise usage(f"Subject: {ref} is a {term.kind}, not a vocabulary entry")


def list_capabilities(request: Request):
    return HTTPStatus.OK, jsonable(_capabilities(request).list_all())


def get_capability(request: Request):
    store = _capabilities(request)
    detail = store.get_capability_detail(_route_target(store, request.param(1)).full_id)
    if detail is None:
        raise not_found(f"no such capability: {request.param(1)}")
    return HTTPStatus.OK, {"capability": jsonable(detail.capability),
                           "coreRevision": detail.core_revision}


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
    response = {"capability": jsonable(detail.capability),
                "coreRevision": detail.core_revision}
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
    if found.origin != "local":
        raise read_only(f"{found.full_id} is inherited from '{found.owner}'; "
                        f"change it there, or override it in this project with "
                        f"`tcw capabilities set {found.full_id} --field <name>=<value>`")
    if fields:
        _subjects_are_vocabulary(request, fields)
    with request.lock:
        detail = store.update_capability(found.full_id, **changes)
    response = {"capability": jsonable(detail.capability),
                "coreRevision": detail.core_revision}
    return HTTPStatus.OK, checked(response, request,
                                  ValidationTarget("capabilities", detail.capability.path))


# -- links ----------------------------------------------------------------------------


def resolve(request: Request):
    """Each `tcw://` link's target, or why it has none. `reason` is one of
    `unresolved` (with `detail`), `archived` (with `detail` and
    `resolution`) and `other-project` (with `project`): a sound reference to
    another project's item, drawn as a labelled link that does not
    navigate, since this server shows one project."""
    uris = request.body.get("uris")
    if not isinstance(uris, list):
        raise usage("uris must be a list")
    result: dict[str, Any] = {}
    for uri in uris[:RESOLVE_MAX_URIS]:
        if not isinstance(uri, str):
            continue
        found = resolve_tcw_ref(request.root, uri)
        if not found.ok:
            result[uri] = {"ok": False, "reason": "unresolved", "detail": found.reason}
        elif found.archived:
            detail = f"{found.key} is resolved work; its documents are no longer " \
                     f"in the tree"
            if found.resolution:
                detail = f"{found.key} was resolved as {found.resolution}; its " \
                         f"documents are no longer in the tree"
            result[uri] = {"ok": False, "reason": "archived", "detail": detail,
                           "resolution": found.resolution}
        elif found.project:
            result[uri] = {"ok": False, "reason": "other-project",
                           "project": found.project}
        else:
            result[uri] = {"ok": True, "axis": AXIS_WORD.get(found.axis),
                           "key": found.key}
    return HTTPStatus.OK, result


ONE = r"/([^/]+)"
ROUTES = [
    route("GET", r"/api/taxonomy", list_terms),
    route("GET", r"/api/taxonomy" + ONE, get_term),
    route("POST", r"/api/taxonomy", create_term),
    route("PATCH", r"/api/taxonomy" + ONE, update_term),
    route("GET", r"/api/capabilities", list_capabilities),
    route("GET", r"/api/capabilities" + ONE, get_capability),
    route("POST", r"/api/capabilities", create_capability),
    route("PATCH", r"/api/capabilities" + ONE, update_capability),
    route("POST", r"/api/resolve", resolve),
]
