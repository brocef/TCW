"""The `tcw://` reference protocol — a portable way to point at a TCW object.

Grammar: ``tcw://[<namespace>/]<axis>/<ref>``
  - ``<axis>``      is ``T`` (Taxonomy), ``C`` (Capabilities), or ``W`` (Work).
  - ``<namespace>`` (optional) locates the object in another project: an
    ``extends`` alias for T/C, a descendant node path for W. Absent = local.
  - ``<ref>``       is the identifier within that axis.

`parse_tcw_uri` is a pure, total function (never raises) — the abstract grammar.
`resolve_tcw_ref` is thin CLI/serve adapter glue: it imports the FS stores and
dispatches through their existing ``get()`` / ``resolve_qualified_work_ref`` (no
new store-interface method — litmus-clean), and never propagates a store
exception to a caller scanning many links.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from tcw.store.fs import (
    FsCapabilitiesStore,
    FsTaxonomyStore,
    qualified_work_ref_problem,
    resolve_qualified_work_ref,
)

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

    Both spellings now produce the same qualified key. ``parse_tcw_uri`` treats the
    first T/C/W segment as the axis, so ``tcw://<id>/W/<slug>`` arrives with a
    parsed namespace while ``tcw://W/<id>/<slug>`` arrives as a bare ref whose
    qualifier is resolved by ``resolve_qualified_work_ref``; keying off where the
    ref actually landed, rather than off the spelling, covers both.
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
        resolved = resolve_qualified_work_ref(node_root, ns_ref)
        if resolved is None:
            return ResolveResult(
                False, "W", None, qualified_work_ref_problem(node_root, ns_ref))
        store, bare = resolved
        if store.node_root == node_root.resolve():        # landed locally
            return ResolveResult(True, "W", bare, "")
        # Foreign: the qualifier is a project id (a status-path locator is always
        # local), and the SPA keys foreign items the way the board prints them.
        project = ns_ref.partition("/")[0]
        return ResolveResult(True, "W", f"{project}/{bare}", "", project)
    except Exception as e:  # store errors (AmbiguousRef, MultipleMatch, IO) -> ok=False
        return ResolveResult(False, parsed.axis, None, str(e))
