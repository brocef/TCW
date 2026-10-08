"""The `tcw://` reference protocol — a portable way to point at a TCW object.

Grammar: ``tcw://[<namespace>/]<axis>/<ref>``
  - ``<axis>``      is ``T`` (Taxonomy), ``C`` (Capabilities), or ``W`` (Work).
  - ``<namespace>`` (optional) locates the object in another project: an
    ``extends`` alias for T/C, a project ID for W. Absent = local.
  - ``<ref>``       is the identifier within that axis.

`parse_tcw_uri` is a pure, total function (never raises) — the abstract grammar.
`resolve_tcw_ref` is thin CLI/serve adapter glue: it imports the FS stores for
T and C and reads a work item through its project's backend for W, and never
propagates a store exception to a caller scanning many links. A work item is
found at any stage, because TCW never deletes an item folder (TCW-70 Design
12.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore

_SCHEME = "tcw://"
_AXES = {"T", "C", "W"}


@dataclass(frozen=True)
class TcwRef:
    namespace: str  # "" = local
    axis: str       # normalized upper: "T" | "C" | "W"
    ref: str


@dataclass(frozen=True)
class ResolveResult:
    ok: bool
    axis: str | None
    key: str | None
    reason: str
    project: str = ""      # owning project id for a foreign work ref; "" = local
    # A work ref that resolved to a *record* of a resolved item rather than to a
    # live one. Still `ok` — the reference is sound and names real, finished work
    # — but there is nothing to navigate to, so a viewer shows it inert rather
    # than as a link, and `tcw validate` says nothing at all.
    archived: bool = False
    resolution: str = ""   # the archived item's resolution; "" when unrecorded


def _segment_ok(seg: str) -> bool:
    """A decoded path segment is safe iff it is not a traversal token and holds
    no control/NUL/backslash chars (mirrors the guard style of `_safe_store_id`)."""
    if seg in (".", ".."):
        return False
    return not any(ord(c) < 0x20 or c == "\x7f" or c == "\\" for c in seg)


def parse_tcw_uri(uri: str) -> TcwRef | None:
    """Parse a ``tcw://`` uri into its (namespace, axis, ref). Total: returns
    None on any malformed input, never raises.

    Split the remainder on ``/`` FIRST, then percent-decode each segment (so a
    ``%2F`` inside a segment can't inject a spurious separator/axis — matches
    the React client's ``parsePath``). The axis is the first segment whose ``.upper()``
    is one of T/C/W; the first-bare-axis-wins collision (``tcw://T/C/ref``) is a
    documented limitation. Empty segments (multiple slashes) are dropped.
    """
    if not isinstance(uri, str) or not uri.startswith(_SCHEME):
        return None
    raw_segs = [s for s in uri[len(_SCHEME):].split("/") if s]  # drop empties
    segs = [unquote(s) for s in raw_segs]
    if not all(_segment_ok(s) for s in segs):
        return None
    axis_idx = next((i for i, s in enumerate(segs) if s.upper() in _AXES), -1)
    if axis_idx == -1:
        return None
    ref = "/".join(segs[axis_idx + 1:])
    if not ref:
        return None
    return TcwRef("/".join(segs[:axis_idx]), segs[axis_idx].upper(), ref)


def resolve_tcw_ref(node_root: Path | None, uri: str) -> ResolveResult:
    """Resolve a ``tcw://`` uri against the node at ``node_root``, returning the
    SPA object key (namespace-qualified where present). Never propagates a store
    exception — a store failure becomes ``ok=False`` with a reason.

    ``ok`` answers one question only: **does this reference resolve in the
    registered graph?** That is what `tcw validate` asks. Whether a *viewer* can
    open it is a different question with a different answer per server, so it is
    not decided here — a foreign work ref reports its owning project in
    ``project`` and the viewer gates on that (see `tcw serve`'s ``/api/resolve``).
    Conflating the two is what made a valid cross-node link report ``ok`` and then
    dead-end in the SPA: the two spellings of a namespaced work ref took different
    paths, and the one people actually write never reached the gate at all.

    Both spellings produce the same qualified key. ``parse_tcw_uri`` treats the
    first T/C/W segment as the axis, so ``tcw://<id>/W/<folder>`` arrives with a
    parsed namespace while ``tcw://W/<id>/<folder>`` arrives as a bare ref with
    the project in front; `_resolve_work` reads both the same way.
    """
    parsed = parse_tcw_uri(uri)
    if parsed is None:
        return ResolveResult(False, None, None, "malformed tcw:// uri")
    if node_root is None:
        return ResolveResult(False, parsed.axis, None, "no tcw node")
    ns_ref = f"{parsed.namespace}/{parsed.ref}" if parsed.namespace else parsed.ref
    try:
        if parsed.axis == "T":
            term = FsTaxonomyStore.open(node_root).get(ns_ref)
            if term is None:
                return ResolveResult(False, "T", None, f"no taxonomy term: {ns_ref}")
            return ResolveResult(True, "T", term.qualified, "")
        if parsed.axis == "C":
            cap = FsCapabilitiesStore.open(node_root).get(ns_ref)
            if cap is None:
                return ResolveResult(False, "C", None, f"no capability: {ns_ref}")
            return ResolveResult(True, "C", cap.qualified, "")
        # axis == "W"
        return _resolve_work(node_root, parsed.namespace, parsed.ref)
    except Exception as e:  # store errors (AmbiguousRef, MultipleMatch, IO) -> ok=False
        return ResolveResult(False, parsed.axis, None, str(e))


def _resolve_work(node_root: Path, namespace: str | None, ref: str) -> ResolveResult:
    """A 3.0 work reference: the item read through its project's backend. Found
    at any stage is OK; `NotFound` is missing; a project declared but not on
    this machine is unresolved (TCW-70 Design 12.1)."""
    from tcw.errors import BackendError, NotFound, Unreachable
    from tcw.work.open import open_backend, open_project

    namespace = namespace or None              # the parser gives "" for no namespace
    if namespace is None and "/" in ref:
        namespace, ref = ref.split("/", 1)
    try:
        if namespace is None:
            backend = open_backend(node_root)
        else:
            backend = open_project(namespace, node_root)
            if backend.project == _current_project(node_root):
                namespace = None
        item = backend.read(ref)
    except Unreachable as error:
        return ResolveResult(False, "W", None, f"unresolved: {error}")
    except NotFound as error:
        return ResolveResult(False, "W", None, str(error))
    except BackendError as error:
        return ResolveResult(False, "W", None, str(error))
    if namespace is None:
        return ResolveResult(True, "W", item.slug.folder, "")
    return ResolveResult(True, "W", str(item.slug), "", namespace)


def _current_project(node_root: Path) -> str | None:
    from tcw.store.fs import FsProjectRegistry
    try:
        return FsProjectRegistry.open(node_root).current.id
    except ValueError:
        return None
